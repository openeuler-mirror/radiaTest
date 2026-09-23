# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.tasks.service import record_task_event
from app.modules.test_management.execution import process_test_job
from app.modules.test_management.frameworks.dangerous_cases import (
    collect_dangerous_scan_reasons,
)
from app.modules.test_management.models import TEST_JOB_TIMEOUT
from app.modules.test_management.schemas import MugenCaseSyncRequest
from app.modules.test_management.service import (
    SUBJECT_ID_MUGEN_SYNC,
    SUBJECT_TYPE_MUGEN_SYNC,
    TASK_TYPE_MUGEN_SYNC,
    release_mugen_sync_lock,
    sync_mugen_cases,
)
from app.worker import celery_app

logger = logging.getLogger(__name__)

# Celery 异步任务入口：Mugen 用例同步与测试任务执行。任务事件写入 task_events
# 供页面详情与中断恢复；Mugen 同步锁在 finally 释放，确保异常也不泄漏锁。


def run_git_command(args: list[str], *, cwd: str | None = None, timeout_seconds: int = 300) -> str:
    """运行 git 子进程，失败时把末尾 2000 字符 stderr 当错误抛 RuntimeError。"""
    completed = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        detail = (
            completed.stderr or completed.stdout or f"exit code {completed.returncode}"
        )[-2000:]
        raise RuntimeError(detail)
    return completed.stdout.strip()


def read_suite_documents(repo_dir: Path) -> dict[str, object]:
    """读取 mugen 仓库 suite2cases/*.json，返回 {suite名: 文档} 供解析。"""
    suite_dir = repo_dir / "suite2cases"
    suites: dict[str, object] = {}
    for path in sorted(suite_dir.glob("*.json")):
        suites[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return suites


def record_sync_event(
    *,
    phase: str,
    message: str,
    celery_task_id: str | None,
    level: str = "info",
    error_code: str | None = None,
) -> None:
    """在独立 DB session 里写一条 Mugen 同步事件并提交，供任务线程外也能记录。"""
    with SessionLocal() as db:
        record_task_event(
            db,
            task_type=TASK_TYPE_MUGEN_SYNC,
            subject_type=SUBJECT_TYPE_MUGEN_SYNC,
            subject_id=SUBJECT_ID_MUGEN_SYNC,
            celery_task_id=celery_task_id,
            phase=phase,
            message=message,
            level=level,
            error_code=error_code,
        )
        db.commit()


@celery_app.task(bind=True, name="app.modules.test_management.tasks.sync_mugen_cases")
def sync_mugen_cases_task(self: object, actor_user_id: str, lock_token: str) -> None:
    """异步同步 Mugen 用例索引：浅克隆 mugen 仓库→读 suite2cases→全量替换索引。

    异常也写 failed 事件再 re-raise；finally 释放同步锁(无论成功失败)，
    避免锁 TTL 未到时阻塞下一次同步。
    """
    task_id = getattr(getattr(self, "request", None), "id", None)
    settings = get_settings()
    try:
        record_sync_event(
            phase="started",
            message="开始同步 Mugen 用例索引",
            celery_task_id=task_id,
        )
        with tempfile.TemporaryDirectory(prefix="kronos-mugen-") as temp_dir:
            repo_dir = Path(temp_dir) / "mugen"
            run_git_command(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    "--branch",
                    settings.mugen_repo_branch,
                    settings.mugen_repo_url,
                    str(repo_dir),
                ],
                timeout_seconds=600,
            )
            commit_sha = run_git_command(["git", "rev-parse", "HEAD"], cwd=str(repo_dir))
            suites = read_suite_documents(repo_dir)
            dangerous_reasons = collect_dangerous_scan_reasons(repo_dir, suites)
            with SessionLocal() as db:
                result = sync_mugen_cases(
                    db,
                    MugenCaseSyncRequest(commit_sha=commit_sha, suites=suites),
                    dangerous_reasons=dangerous_reasons,
                )
                record_task_event(
                    db,
                    task_type=TASK_TYPE_MUGEN_SYNC,
                    subject_type=SUBJECT_TYPE_MUGEN_SYNC,
                    subject_id=SUBJECT_ID_MUGEN_SYNC,
                    celery_task_id=task_id,
                    phase="succeeded",
                    message=(
                        f"Mugen 用例同步完成，{result.case_count} 条 case，"
                        f"脚本扫描标记危险 {len(dangerous_reasons)} 条"
                    ),
                )
                db.commit()
    except Exception as exc:  # noqa: BLE001
        record_sync_event(
            phase="failed",
            message=f"Mugen 用例同步失败：{exc}",
            celery_task_id=task_id,
            level="error",
            error_code="mugen_sync_failed",
        )
        raise
    finally:
        release_mugen_sync_lock(lock_token)


@celery_app.task(
    bind=True,
    name="app.modules.test_management.tasks.run_test_job",
    soft_time_limit=int(TEST_JOB_TIMEOUT.total_seconds()),
)
def run_test_job_task(self: object, job_id: int | str) -> None:
    """异步执行测试任务。soft_time_limit=15h，超时由 Celery 抛 SoftTimeLimitExceeded，
    execution 层捕获后判 task_timeout。job_id 为历史字符串 ID 时忽略。
    """
    try:
        resolved_job_id = int(job_id)
    except (TypeError, ValueError):
        logger.warning("Ignoring test job task with legacy ID: %s", job_id)
        return
    process_test_job(resolved_job_id)

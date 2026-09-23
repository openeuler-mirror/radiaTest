# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Pipeline RunJob Celery task（通用循环）。

每个 RunJob 一个任务：按 test_framework 调 executor.prepare_and_execute → 更新 RunJob 状态 →
finally 自汇集日志。fail-safe：异常自己 catch 标 error，绝不 raise，保证 finally 自汇集可靠。
执行/解析的 mugen/非 mugen 差异封在 framework_executor 里，这里类型/框架无关。
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.pipelines.registry import get_framework_executor
from app.modules.tasks.models import TaskEvent
from app.modules.test_management.log_collector import LogCollector
from app.modules.test_management.models import TestJob, TestLogArtifact
from app.modules.test_management.remote import run_ssh_command, scp_directory, scp_file
from app.worker import celery_app

logger = logging.getLogger(__name__)

_LOG_TIMEOUT_SECONDS = 120
_DIR_TIMEOUT_SECONDS = 600
_TERMINAL_RUN_JOB_STATUSES = frozenset({"succeeded", "failed", "error", "cancelled"})


def _run_job_is_terminal(db: Session, run_job: PipelineRunJob) -> bool:
    """刷新 RunJob，防止存活 Worker 覆盖恢复服务已提交的终态。"""
    db.refresh(run_job, with_for_update=True)
    return run_job.status in _TERMINAL_RUN_JOB_STATUSES


def _control_node_ssh_targets(db: Session, job: TestJob) -> list[dict[str, object]]:
    """返回每个 env_set 控制节点的 SSH 连接信息(best-effort)。"""
    from app.modules.test_management.envs.vm import node_runtime

    targets: list[dict[str, object]] = []
    for env_set in job.env_sets:
        control_node = next(
            (n for n in env_set.nodes if n.role == "control"), None
        )
        if control_node is None or not control_node.resource_id:
            continue
        try:
            runtime = node_runtime(db, control_node)
        except Exception:  # noqa: BLE001
            # 控制节点 SSH 信息解析失败时跳过该 env_set,留 debug 便于排查为何缺目标。
            logger.debug(
                "failed to resolve control node runtime", exc_info=True
            )
            continue
        targets.append(
            {
                "ip": runtime.ip,
                "username": runtime.username,
                "password": runtime.password,
                "env_set_index": env_set.set_index,
            }
        )
    return targets


def _self_collect_logs(
    db: Session,
    *,
    run_job: PipelineRunJob,
    job: TestJob | None,
    run: PipelineRun | None,
    template: TestModuleTemplate | None,
) -> None:
    """SSH 到控制节点拉 /opt/{template.name}-logs/* → store_artifact。best-effort，失败不抛。"""
    if job is None or run is None or template is None:
        return
    log_dir = f"/opt/{template.name}-logs"
    collector = LogCollector(base_dir=get_settings().pipeline_log_dir)
    multi_env = len(job.env_sets) > 1
    for target in _control_node_ssh_targets(db, job):
        ip = str(target["ip"])
        if not ip:
            continue
        env_set_index = target.get("env_set_index")
        try:
            listing = run_ssh_command(
                host=ip,
                username=str(target["username"]),
                password=str(target["password"]),
                command=f"ls -1F {log_dir}/ 2>/dev/null",
                timeout_seconds=_LOG_TIMEOUT_SECONDS,
                verify_host_key=False,
            )
            if listing.returncode != 0:
                continue
            entries = [
                line.strip()
                for line in (listing.stdout or "").splitlines()
                if line.strip()
            ]
        except Exception:  # noqa: BLE001
            # 列目录失败(SSH/超时)按跳过该目标处理,留 debug 留痕。
            logger.debug("failed to list log dir", exc_info=True)
            continue
        for entry in entries:
            is_dir = entry.endswith("/")
            filename = entry.rstrip("/*@|")
            if not filename:
                continue
            # 目录和文件都带 env 前缀(multi_env)，避免命名冲突
            # (否则 env 2 的 logs/results 会被既有检查跳过)。
            artifact_name = (
                f"env{env_set_index}-{filename}"
                if multi_env and env_set_index is not None
                else filename
            )
            existing = db.execute(
                select(TestLogArtifact).where(
                    TestLogArtifact.pipeline_run_id == run.id,
                    TestLogArtifact.job_id == job.id,
                    TestLogArtifact.artifact_name == artifact_name,
                )
            ).scalars().first()
            if existing is not None and not is_dir:
                # 文件已登记：跳过（module_log 不做增量合并）。
                continue
            local_parent = (
                Path(get_settings().pipeline_log_dir)
                / run.id
                / template.name
                / run_job.arch
                / run_job.id
            )
            if multi_env and env_set_index is not None:
                local_parent /= f"env-{env_set_index}"
            local_parent.mkdir(parents=True, exist_ok=True)
            if is_dir:
                if existing is not None:
                    # 补漏式重拉（ADR 0048）：目录 artifact 已存在（逐 case 上传
                    # 登记过）仍重拉全量并与既有内容合并——逐 case 上传失败的
                    # case 由这里兜底；同名文件幂等覆盖（mugen 日志文件名含时间
                    # 戳，重跑产生新文件名，不膨胀）。不新增 artifact 记录。
                    with tempfile.TemporaryDirectory(prefix="kronos-log-merge-") as tmp:
                        ok = scp_directory(
                            host=ip,
                            username=str(target["username"]),
                            password=str(target["password"]),
                            remote_path=f"{log_dir}/{filename}",
                            local_dir=tmp,
                            timeout_seconds=_DIR_TIMEOUT_SECONDS,
                            verify_host_key=False,
                        )
                        merged = Path(tmp) / filename
                        if ok and merged.is_dir():
                            shutil.copytree(
                                merged, Path(existing.storage_path), dirs_exist_ok=True
                            )
                    continue
                ok = scp_directory(
                    host=ip,
                    username=str(target["username"]),
                    password=str(target["password"]),
                    remote_path=f"{log_dir}/{filename}",
                    local_dir=str(local_parent),
                    timeout_seconds=_DIR_TIMEOUT_SECONDS,
                    verify_host_key=False,
                )
                if not ok:
                    continue
                collector.store_dir_artifact(
                    db=db,
                    pipeline_run_id=run.id,
                    job_id=job.id,
                    module=template.name,
                    arch=run_job.arch,
                    artifact_type="pkg_folder",
                    artifact_name=artifact_name,
                    local_dir=str(local_parent / filename),
                )
            else:
                # File: scp the full file to disk (no truncation). The old
                # cat-into-stdout was capped at SUMMARY_LIMIT (16KB), truncating
                # large logs (ltp.txt 825k lines → ~400 lines).
                local_file = local_parent / filename
                ok = scp_file(
                    host=ip,
                    username=str(target["username"]),
                    password=str(target["password"]),
                    remote_path=f"{log_dir}/{filename}",
                    local_path=str(local_file),
                    timeout_seconds=_DIR_TIMEOUT_SECONDS,
                    verify_host_key=False,
                )
                if not ok:
                    continue
                collector.store_file_artifact(
                    db=db,
                    job_id=job.id,
                    module=template.name,
                    arch=run_job.arch,
                    artifact_type="module_log",
                    artifact_name=artifact_name,
                    pipeline_run_id=run.id,
                    local_file=str(local_file),
                )
    db.commit()


@celery_app.task(
    bind=True,
    name="app.modules.pipelines.tasks.run_pipeline_run_job",
    soft_time_limit=15 * 3600 + 600,
)
def run_pipeline_run_job_task(
    self: object, run_job_id: str, actor_user_id: str
) -> None:
    with SessionLocal() as db:
        run_job = db.get(PipelineRunJob, run_job_id)
        if run_job is None:
            return
        if run_job.cancel_requested:
            run_job.status = "cancelled"
            db.commit()
            return
        if run_job.status != "pending":
            return
        run_job.status = "preparing"
        db.add(
            TaskEvent(
                task_type="pipeline_runjob",
                subject_type="runjob",
                subject_id=run_job.id,
                celery_task_id=run_job.task_id,
                phase="started",
                message="worker 已领取 Pipeline RunJob",
            )
        )
        db.commit()

        run: PipelineRun | None = None
        config: PipelineConfig | None = None
        template: TestModuleTemplate | None = None
        job: TestJob | None = None
        try:
            run = db.get(PipelineRun, run_job.pipeline_run_id)
            if run is None:
                if not _run_job_is_terminal(db, run_job):
                    run_job.status = "error"
                    db.commit()
                return
            config = db.get(PipelineConfig, run.config_id)
            template = db.get(TestModuleTemplate, run_job.module_template_id)
            if config is None or template is None:
                if not _run_job_is_terminal(db, run_job):
                    run_job.status = "error"
                    db.commit()
                return

            if _run_job_is_terminal(db, run_job):
                return
            if run_job.cancel_requested:
                run_job.status = "cancelled"
                db.commit()
                return
            run_job.status = "running"
            db.commit()

            # Seam 2: 执行按 test_framework 分派（mugen = build_test_job + process_test_job）
            executor = get_framework_executor(config.test_framework)
            terminal = executor.prepare_and_execute(
                db,
                run_job=run_job,
                config=config,
                actor_user_id=actor_user_id,
            )
            if not _run_job_is_terminal(db, run_job):
                run_job.status = "cancelled" if run_job.cancel_requested else terminal
                db.commit()
        except Exception as exc:  # noqa: BLE001
            # PostgreSQL 语句失败后事务不可继续使用；先回滚，再用当前数据库事实
            # 重新读取 RunJob，确保 error 状态和事件可以可靠提交。
            db.rollback()
            run_job = db.get(PipelineRunJob, run_job_id)
            if run_job is not None and not _run_job_is_terminal(db, run_job):
                run_job.status = "error"
                db.add(
                    TaskEvent(
                        task_type="pipeline_runjob",
                        subject_type="runjob",
                        subject_id=run_job.id,
                        celery_task_id=run_job.task_id,
                        phase="runjob_error",
                        message=str(exc),
                        level="error",
                    )
                )
                db.commit()
        finally:
            # fail-safe 自汇集日志（无论成败/异常都跑）
            if run_job is not None:
                if run_job.test_job_id:
                    job = db.get(TestJob, run_job.test_job_id)
                try:
                    _self_collect_logs(
                        db, run_job=run_job, job=job, run=run, template=template
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("pipeline self log collection failed: run_job=%s", run_job.id)


@celery_app.task(
    name="app.modules.pipelines.tasks.collect_pipeline_logs",
    autoretry_for=(Exception,),
    retry_backoff=60,
    max_retries=3,
)
def collect_pipeline_logs_task(run_job_id: str) -> None:
    """独立的日志汇集 task——可跨 worker 重启存活。

    幂等：跳过已存在的 artifact。可由 API 手动触发或在任务完成后调度。
    """
    with SessionLocal() as db:
        run_job = db.get(PipelineRunJob, run_job_id)
        if run_job is None or not run_job.test_job_id:
            return
        run = db.get(PipelineRun, run_job.pipeline_run_id)
        template = db.get(TestModuleTemplate, run_job.module_template_id)
        job = db.get(TestJob, run_job.test_job_id)
        _self_collect_logs(
            db, run_job=run_job, job=job, run=run, template=template
        )


@celery_app.task(name="app.modules.pipelines.tasks.destroy_execution_envs")
def destroy_execution_envs_task(execution_id: str, actor_user_id: str) -> None:
    """异步销毁环境——避免销毁大量 VM 时 API 超时。"""
    from app.modules.pipelines.service import destroy_execution_envs, get_pipeline_execution
    from app.modules.users.service import get_user_by_id

    with SessionLocal() as db:
        execution = get_pipeline_execution(db, execution_id)
        if execution is None:
            return
        actor = get_user_by_id(db, user_id=actor_user_id)
        if actor is None:
            return
        destroy_execution_envs(db, execution=execution, actor=actor)

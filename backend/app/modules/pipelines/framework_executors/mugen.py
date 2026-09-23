# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Mugen 测试框架 executor（Seam 2：test_framework）。

决定 mugen 的"执行 + 解析"：建 mugen TestJob（从模板复制脚本/mugen_exec_command/
result_parser）+ 复用 process_test_job（run_case 跑 mugen.sh + HangDetector +
result_parser 写 TestCaseRunDetail）。非 mugen 框架（未来）实现自己的 executor，
写同样的结果表（TestCaseRun/Detail/logs）。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.pipelines.builder import build_test_job_for_run_job
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.test_management.case_log_context import CaseLogContext
from app.modules.test_management.execution import cancel_unstarted_test_job, process_test_job
from app.modules.test_management.models import TestJobStatus


class MugenFrameworkExecutor:
    test_framework = "mugen"
    display_name = "Mugen"

    @staticmethod
    def prepare_and_execute(
        db: Session,
        *,
        run_job: PipelineRunJob,
        config: PipelineConfig,
        actor_user_id: str,
    ) -> str:
        """建 mugen TestJob + 跑 process_test_job，返回 RunJob 终态（succeeded/failed/error）。"""
        run = db.get(PipelineRun, run_job.pipeline_run_id)
        template = db.get(TestModuleTemplate, run_job.module_template_id)
        if run is None or template is None:
            return "error"
        job = build_test_job_for_run_job(
            db,
            run_job=run_job,
            config=config,
            template=template,
            version=run.version,
            actor_user_id=actor_user_id,
        )
        # Commit so process_test_job (which opens its own session) can see
        # the newly created TestJob/EnvSets/CaseRuns. Without this, the
        # flushed-but-uncommitted rows are invisible to a new PostgreSQL
        # transaction, causing process_test_job to silently return None.
        db.commit()
        db.refresh(run_job)
        if run_job.cancel_requested:
            # 取消可能在 builder 写入 TestJob 后才提交；此时不允许启动任何环境。
            job.cancel_requested = True
            cancel_unstarted_test_job(db, job=job)
            return "cancelled"
        # 逐 case 日志上传上下文（ADR 0048）：runner 侧据此把 case 日志落到
        # pipeline 存储分组路径；DTO 由本侧（拥有 pipeline 上下文）注入。
        process_test_job(
            job.id,
            case_log_context=CaseLogContext(
                run_id=run.id,
                module_name=template.name,
                arch=run_job.arch,
                run_job_id=run_job.id,
            ),
        )
        db.refresh(job)
        return _map_job_status(job.status)


def _map_job_status(job_status: str) -> str:
    if job_status == TestJobStatus.SUCCEEDED.value:
        return "succeeded"
    if job_status == TestJobStatus.FAILED.value:
        return "failed"
    if job_status == TestJobStatus.CANCELLED.value:
        return "cancelled"
    return "error"

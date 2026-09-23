# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""任务列表对 Pipeline 来源与引用状态的只读实现。

被 test_management.pipeline_reads 的注入缝消费（注册发生在应用装配层），
依赖方向符合 ADR 0036：pipelines 允许读取 test_management 的模型和 Schema。
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.test_management.models import TestJob
from app.modules.test_management.schemas import PipelineOriginRead


def attach_pipeline_origins(
    db: Session, job_ids: Sequence[int]
) -> dict[int, tuple[PipelineOriginRead | None, bool]]:
    """批量反查任务来源流水线，返回 job_id -> (来源信息, 来源执行已删除标记)。

    关联仍在的 RunJob 给出完整来源；`keep_env=True` 且 RunJob 已删的是流水线
    孤儿任务（keep_env 仅流水线 builder 置位，普通创建接口不暴露），标记来源
    执行已删除；普通任务两者皆无。批量查询避免逐行 join。
    """
    if not job_ids:
        return {}
    rows = db.execute(
        select(
            PipelineRunJob.test_job_id,
            PipelineRunJob.id.label("run_job_id"),
            PipelineRunJob.arch.label("arch"),
            TestModuleTemplate.name.label("module_name"),
            PipelineRun.version.label("version"),
            PipelineConfig.name.label("config_name"),
        )
        .join(TestModuleTemplate, PipelineRunJob.module_template_id == TestModuleTemplate.id)
        .join(PipelineRun, PipelineRunJob.pipeline_run_id == PipelineRun.id)
        .join(PipelineExecution, PipelineRun.execution_id == PipelineExecution.id)
        .join(PipelineConfig, PipelineExecution.config_id == PipelineConfig.id)
        .where(PipelineRunJob.test_job_id.in_(job_ids))
    ).all()
    linked = {
        row.test_job_id: PipelineOriginRead(
            run_job_id=row.run_job_id,
            config_name=row.config_name,
            version=row.version,
            module_name=row.module_name,
            arch=row.arch,
        )
        for row in rows
    }
    unlinked_job_ids = [job_id for job_id in job_ids if job_id not in linked]
    orphan_flags: dict[int, bool] = {}
    if unlinked_job_ids:
        keep_env_rows = db.execute(
            select(TestJob.id, TestJob.keep_env).where(TestJob.id.in_(unlinked_job_ids))
        ).all()
        orphan_flags = {row.id: bool(row.keep_env) for row in keep_env_rows}
    return {
        job_id: (linked[job_id], False)
        if job_id in linked
        else (None, orphan_flags.get(job_id, False))
        for job_id in job_ids
    }


def is_test_job_referenced_by_pipeline(db: Session, job_id: int) -> bool:
    """任务是否仍被现存 PipelineRunJob 引用（无外键约束，需显式查询）。"""
    exists = (
        db.execute(
            select(PipelineRunJob.id).where(PipelineRunJob.test_job_id == job_id).limit(1)
        )
        .scalar_one_or_none()
    )
    return exists is not None

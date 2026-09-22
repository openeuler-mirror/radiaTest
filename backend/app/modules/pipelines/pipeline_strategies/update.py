# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Update 流水线类型 strategy（Seam 1：pipeline_type）。

决定 update 的"形状"：多版本 × 多架构 × 模块模板矩阵，env_type=both 的模块拆 vm/physical。
读 config_data["module_template_ids"]（类型专属配置）。execution 编排/执行/自汇集/看板是通用层。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)


class UpdatePipelineStrategy:
    pipeline_type = "update"

    @staticmethod
    def plan_run_jobs(
        db: Session,
        *,
        config: PipelineConfig,
        execution: PipelineExecution,
        versions: list[str],
        archs: list[str],
        triggered_by: str = "manual",
    ) -> list[PipelineRunJob]:
        template_ids = list(config.config_data.get("module_template_ids") or [])
        templates = [
            t for t in (db.get(TestModuleTemplate, tid) for tid in template_ids) if t is not None
        ]
        run_jobs: list[PipelineRunJob] = []
        for version in versions:
            run = PipelineRun(
                config_id=config.id,
                execution_id=execution.id,
                version=version,
                status="pending",
                triggered_by=triggered_by,
            )
            db.add(run)
            db.flush()
            for template in templates:
                for arch in archs:
                    # 64k kernel is aarch64-only; skip x86_64 for -64k versions.
                    if version.endswith("-64k") and arch == "x86_64":
                        continue
                    if template.env_type == "both":
                        job = PipelineRunJob(
                            pipeline_run_id=run.id,
                            module_template_id=template.id,
                            arch=arch,
                            env_type=None,
                            status="pending",
                        )
                        db.add(job)
                        run_jobs.append(job)
                    else:
                        # physical -> single physical RunJob; vm -> single vm RunJob
                        # (env_type=None, builder resolves to VM)
                        job = PipelineRunJob(
                            pipeline_run_id=run.id,
                            module_template_id=template.id,
                            arch=arch,
                            env_type="physical" if template.env_type == "physical" else None,
                            status="pending",
                        )
                        db.add(job)
                        run_jobs.append(job)
        db.flush()
        return run_jobs

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Direct-run pipeline strategy（B-class，数据驱动）。

所有 B 类（`strategy_kind=direct_run`）类型共享此 strategy。RunJob 形状：
`version × arch`（单版本时即每架构一个 RunJob）。每个 RunJob 用单个 release 模板，
其 TestJob/env_set 跑**全部选中 suite 的 case**（跨 suite 共一套环境），
env_type 固定 None（不拆 vm/physical）。`node_num`=max(全部选中 case 的 node_num)。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)


def _release_default_post_env(log_dir_name: str) -> str:
    """direct_run 模板默认 post_env：拷贝 mugen 原生 logs/results 到自汇集约定路径。

    通用 §4.8 自汇集 SSH 拉 `/opt/{template.name}-logs/*`；direct_run 模板无模块专属
    脚本，故给一个默认脚本把 `${OET_PATH}/logs`+`results` 拷过去，使日志落盘无需改
    共享自汇集代码（update 不受影响）。`${OET_PATH}` 由 build_env_file 注入。
    """
    return (
        f"mkdir -p /opt/{log_dir_name}-logs\n"
        f'cp -r "${{OET_PATH}}/logs" /opt/{log_dir_name}-logs/ 2>/dev/null || true\n'
        f'cp -r "${{OET_PATH}}/results" /opt/{log_dir_name}-logs/ 2>/dev/null || true\n'
    )


def _find_or_create_release_template(
    db: Session, pipeline_type: str
) -> TestModuleTemplate:
    """查找或创建 direct_run 的单个 TestModuleTemplate。

    release 一个 RunJob 跑全部选中 suite 的 case（跨 suite 共一套环境），故只需一个
    模板承载 pre/post_env/result_parser（case 选择由 builder 从 config_data.case_selections
    汇总，不依赖 template.suite_name）。模板名 `{pipeline_type}`，带默认 post_env
    （日志拷贝）。复用 TestModuleTemplate 模型让 builder 路径（每个 RunJob 需带
    module_template_id）不变。
    """
    name = pipeline_type
    existing = db.execute(
        select(TestModuleTemplate).where(TestModuleTemplate.name == name)
    ).scalars().first()
    if existing is not None:
        # 既有 release 模板升级为 both：物理机用例开关（release_physical_enabled）
        # 依赖 both 分支按 env_type 拆分环境集。
        if existing.env_type != "both":
            existing.env_type = "both"
            db.flush()
        return existing
    template = TestModuleTemplate(
        name=name,
        display_name=pipeline_type,
        suite_name=pipeline_type,
        pipeline_type=pipeline_type,
        env_set_num=1,
        node_num=1,
        case_filter="none",
        env_type="both",
        pre_env_script="",
        rerun_env_script="",
        post_env_script=_release_default_post_env(name),
        result_parser="mugen_results",
        test_framework="mugen",
        mugen_exec_command=None,
    )
    db.add(template)
    db.flush()
    return template


class DirectRunPipelineStrategy:
    """B-class pipeline strategy。经 `strategy_kind=direct_run` 分派。"""

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
        # release 为单版本配置；config 校验已约束 len(versions)==1，此为触发级覆盖的兜底。
        if config.pipeline_type == "release" and len(versions) > 1:
            raise ValueError("release 配置只支持单版本")
        # case_selections 必须存在（release 校验保证）；兼容旧 direct_run 的 config_data.suites。
        case_selections = list(config.config_data.get("case_selections") or [])
        if not case_selections:
            legacy_suites = config.config_data.get("suites") or []
            case_selections = [
                {"suite_name": s, "case_names": []} for s in legacy_suites
            ]
        # 单个 release 模板：每个 RunJob 跑全部选中 suite 的 case（每架构一套环境）。
        template = _find_or_create_release_template(db, config.pipeline_type)

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
            # 每架构一个 RunJob（跨 suite 的全部 case 在这一套环境里跑）。
            for arch in archs:
                job = PipelineRunJob(
                    pipeline_run_id=run.id,
                    module_template_id=template.id,
                    arch=arch,
                    env_type=None,
                    status="pending",
                )
                db.add(job)
                run_jobs.append(job)
        db.flush()
        return run_jobs

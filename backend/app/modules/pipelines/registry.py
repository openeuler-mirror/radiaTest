# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Pipeline seam 注册表。

PIPELINE_STRATEGIES: strategy_kind -> strategy(RunJob 形状 + 类型专属 config)。
FRAMEWORK_EXECUTORS: test_framework -> executor(构建执行单元 + run + parse)。

framework.py 的通用循环（trigger / run_pipeline_run_job）按这俩注册表分派。
新增 A 类 pipeline 类型 = 加一个 strategy 文件 + 注册；新增 B 类（direct_run）
类型 = 前端 CRUD `pipeline_types` 表，无需代码。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pipelines.framework_executors.mugen import MugenFrameworkExecutor
from app.modules.pipelines.models import PipelineType
from app.modules.pipelines.pipeline_strategies.direct_run import (
    DirectRunPipelineStrategy,
)
from app.modules.pipelines.pipeline_strategies.update import UpdatePipelineStrategy

# 按 `strategy_kind`(代码注册)分派。pipeline_type name → strategy_kind 的
# 查询经 pipeline_types 表(数据驱动)。
_STRATEGY_KIND_DISPATCH: dict[str, object] = {
    "update_strategy": UpdatePipelineStrategy(),
    "direct_run": DirectRunPipelineStrategy(),
}

FRAMEWORK_EXECUTORS: dict[str, object] = {
    "mugen": MugenFrameworkExecutor(),
}


def get_pipeline_strategy(db: Session, pipeline_type: str) -> object:
    """查 pipeline_type 行，按 strategy_kind 分派。

    pipeline_type 未注册或 strategy_kind 未知时抛 ValueError。
    """
    pt = db.execute(
        select(PipelineType).where(PipelineType.name == pipeline_type)
    ).scalar_one_or_none()
    if pt is None:
        raise ValueError(f"unknown pipeline_type: {pipeline_type}")
    strategy = _STRATEGY_KIND_DISPATCH.get(pt.strategy_kind)
    if strategy is None:
        raise ValueError(f"unknown strategy_kind: {pt.strategy_kind}")
    return strategy


def get_framework_executor(test_framework: str) -> object:
    executor = FRAMEWORK_EXECUTORS.get(test_framework)
    if executor is None:
        raise ValueError(f"unknown test_framework: {test_framework}")
    return executor

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Test Job 侧对 Pipeline 只读能力的注入缝。

依赖方向约束（ADR 0036）：固定为 Pipeline → Test Job，本模块不得导入
pipelines 包。任务列表来源展示和删除引用校验需要读取 Pipeline 拥有的
RunJob 关联状态，因此在此声明 provider 接口，由应用装配层注册
pipelines 模块的实现；未注册时按"无来源、无引用"处理，Test Job 保持
可独立执行。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sqlalchemy.orm import Session

from app.modules.test_management.schemas import PipelineOriginRead

# 返回 job_id -> (来源信息, 来源执行已删除标记)。origin 为 None 且
# deleted 为 True 表示流水线孤儿任务（RunJob 已删）。
PipelineOriginProvider = Callable[
    [Session, Sequence[int]], dict[int, tuple[PipelineOriginRead | None, bool]]
]
# 任务是否仍被现存 RunJob 引用；引用中的任务禁止从任务列表删除。
PipelineReferenceChecker = Callable[[Session, int], bool]


def _default_origin_provider(
    db: Session, job_ids: Sequence[int]
) -> dict[int, tuple[PipelineOriginRead | None, bool]]:
    return {job_id: (None, False) for job_id in job_ids}


def _default_reference_checker(db: Session, job_id: int) -> bool:
    return False


_origin_provider: PipelineOriginProvider = _default_origin_provider
_reference_checker: PipelineReferenceChecker = _default_reference_checker


def register_pipeline_reads(
    *,
    origin_provider: PipelineOriginProvider,
    reference_checker: PipelineReferenceChecker,
) -> None:
    """装配层注入 pipelines 模块实现；应用启动时调用一次。"""
    global _origin_provider, _reference_checker
    _origin_provider = origin_provider
    _reference_checker = reference_checker


def resolve_pipeline_origins(
    db: Session, job_ids: Sequence[int]
) -> dict[int, tuple[PipelineOriginRead | None, bool]]:
    return _origin_provider(db, job_ids)


def is_test_job_referenced_by_pipeline(db: Session, job_id: int) -> bool:
    return _reference_checker(db, job_id)

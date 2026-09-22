# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Pipeline type strategy(Seam 1: strategy_kind)。每个 strategy 定义某个
strategy_kind 的 RunJob 形状 + 类型专属 config。框架循环
(trigger / run_pipeline_run_job)与类型无关，经 registry 分派。

A-class(`update_strategy`)type 的代码级 strategy 在此。
B-class(`direct_run`)type 共用 `DirectRunPipelineStrategy`，由
`pipeline_types` 表驱动(无 per-type 代码)。
"""

from __future__ import annotations

from .direct_run import DirectRunPipelineStrategy
from .update import UpdatePipelineStrategy

__all__ = ["DirectRunPipelineStrategy", "UpdatePipelineStrategy"]

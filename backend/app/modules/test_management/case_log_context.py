# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""逐 case 日志上传的 pipeline 上下文（ADR 0048）。

run_case（test_management）需要 run_id/模块名/arch/run_job_id 才能把日志落到
pipeline 存储分组路径，但这些状态归 pipelines 模块所有。由 executor 构造纯
DTO 经 process_test_job 注入，进程内注册表按 job_id 存取（env_set 并行线程链
不穿参）。test_management 不 import pipelines（模块边界守卫测试约束）。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class CaseLogContext:
    """逐 case 日志上传所需的 pipeline 存储上下文（纯值对象）。"""

    run_id: str
    module_name: str
    arch: str
    run_job_id: str


_lock = threading.Lock()
_contexts: dict[int, CaseLogContext] = {}


def set_case_log_context(job_id: int, context: CaseLogContext) -> None:
    """注册 job 的上下文；process_test_job 启动时调用一次。"""
    with _lock:
        _contexts[job_id] = context


def get_case_log_context(job_id: int) -> CaseLogContext | None:
    """读取 job 的上下文；run_case 收尾时调用，无上下文返回 None（跳过上传）。"""
    with _lock:
        return _contexts.get(job_id)


def pop_case_log_context(job_id: int) -> CaseLogContext | None:
    """取出并注销 job 的上下文；process_test_job 终止路径统一调用，防泄漏。"""
    with _lock:
        return _contexts.pop(job_id, None)

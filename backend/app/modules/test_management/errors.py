# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations


class TestJobExecutionError(Exception):
    """测试执行链路错误。code 是稳定的 error_code(写 task_events、决定终态)。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class EnvSetHangError(Exception):
    """VM/物理机挂死，本 env_set 剩余 case 跳过，其他 env_set 继续。"""


class TestJobDeleteError(Exception):
    """测试任务删除被拒绝。

    reason 是稳定的原因码（forbidden/not_terminal/retained_env/pipeline_referenced），
    路由据此映射状态码；message 面向用户展示。
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason

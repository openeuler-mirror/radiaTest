# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.


class TicketError(Exception):
    """工单模块所有领域异常的基类，供路由层统一捕获映射。"""


class TicketNotFoundError(TicketError):
    """按 ID 未找到工单，映射 404。"""


class TicketPermissionError(TicketError):
    """鉴权策略被拒(非提出人编辑、非管理员受理等)，映射 403。"""


class TicketValidationError(TicketError):
    """请求参数语义非法(完成时间早于当前等)，映射 400。"""


class TicketConflictError(TicketError):
    """工单状态冲突(如非待处理状态不可编辑)，映射 409。"""


class TicketVersionConflictError(TicketConflictError):
    """乐观并发冲突：更新时状态已不是期望状态(rowcount != 1)，映射 409。"""


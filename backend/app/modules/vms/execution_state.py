# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.resources.models import Resource

# VM 销毁执行状态存放在 resource.extra(JSON)中，作为跨模块的幂等防重账本：
# 租约懒释放入队后写 task_id+enqueued_at，worker 领取后写 started_at，
# 销毁完成或失败后清除。避免同一 VM 被重复入队销毁。
VM_DESTROY_ENQUEUED_AT_KEY = "vm_destroy_enqueued_at"
VM_DESTROY_STARTED_AT_KEY = "vm_destroy_started_at"
VM_DESTROY_TASK_ID_KEY = "vm_destroy_task_id"


@dataclass(frozen=True)
class VMDestroyExecution:
    """已入队的 VM 销毁执行快照，从 resource.extra 解析得到。"""

    task_id: str
    enqueued_at: datetime | None
    started_at: datetime | None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_vm_destroy_execution(resource: Resource) -> VMDestroyExecution | None:
    """读取已入队的销毁执行；无则返回 None。租约懒释放据此判断是否已入队。"""
    task_id = resource.extra.get(VM_DESTROY_TASK_ID_KEY)
    if not isinstance(task_id, str) or not task_id:
        return None
    return VMDestroyExecution(
        task_id=task_id,
        enqueued_at=_parse_datetime(resource.extra.get(VM_DESTROY_ENQUEUED_AT_KEY)),
        started_at=_parse_datetime(resource.extra.get(VM_DESTROY_STARTED_AT_KEY)),
    )


def mark_vm_destroy_queued(
    resource: Resource,
    *,
    task_id: str,
    enqueued_at: datetime,
) -> None:
    """租约懒释放入队成功后写入 task_id 与 enqueued_at。"""
    resource.extra = {
        **resource.extra,
        VM_DESTROY_ENQUEUED_AT_KEY: enqueued_at.isoformat(),
        VM_DESTROY_TASK_ID_KEY: task_id,
    }


def mark_vm_destroy_started(
    resource: Resource,
    *,
    task_id: str,
    started_at: datetime,
) -> None:
    """worker 领取销毁任务后写 started_at，区分"已入队"与"正在销毁"。"""
    resource.extra = {
        **resource.extra,
        VM_DESTROY_STARTED_AT_KEY: started_at.isoformat(),
        VM_DESTROY_TASK_ID_KEY: task_id,
    }


def clear_vm_destroy_execution(resource: Resource, *, error: object | None = None) -> None:
    """
    销毁完成或失败后清除执行状态键。error 非 None 时把错误记到 last_destroy_error
    供下次读取定位，但不保留 task_id(允许重新入队)。
    """
    removed_keys = {
        VM_DESTROY_ENQUEUED_AT_KEY,
        VM_DESTROY_STARTED_AT_KEY,
        VM_DESTROY_TASK_ID_KEY,
    }
    extra = {
        key: value for key, value in resource.extra.items() if key not in removed_keys
    }
    if error is not None:
        extra["last_destroy_error"] = error
    resource.extra = extra

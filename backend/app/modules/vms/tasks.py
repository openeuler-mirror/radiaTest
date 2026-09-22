# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from app.modules.vms.service import VMDestroyOptions, process_vm_destroy, process_vm_request
from app.worker import celery_app

# VM Celery 任务入口。实际逻辑在 service.process_* 中，此处只做 task 装饰
# 与参数透传，便于在 service 层单独测试编排逻辑。


@celery_app.task(bind=True, name="app.modules.vms.tasks.create_vm_request")
def create_vm_request_task(self: object, vm_request_id: str) -> None:
    """异步创建 VM 的 Celery 入口，由 submit_vm_request 经 send_task 投递。"""
    process_vm_request(vm_request_id)


@celery_app.task(bind=True, name="app.modules.vms.tasks.destroy_vm")
def destroy_vm_task(
    self: object,
    resource_id: str,
    lease_id: str,
    options: dict[str, object],
) -> None:
    """异步销毁 VM 的 Celery 入口，由租约懒释放或用户释放投递。

    从 self.request.id 取真实 task_id 传给 service，用于把 started_at 记到
    execution_state，区分"已入队"与"正在销毁"。
    """
    task_id = getattr(getattr(self, "request", None), "id", None)
    process_vm_destroy(
        resource_id,
        lease_id,
        options=VMDestroyOptions(
            actor_user_id=options.get("actor_user_id"),
            reason=options.get("reason"),
            force=bool(options.get("force", False)),
            task_id=task_id,
        ),
    )

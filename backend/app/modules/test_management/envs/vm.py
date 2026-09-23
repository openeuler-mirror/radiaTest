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
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.modules.leases.service import get_resource_active_lease
from app.modules.resources.models import Resource
from app.modules.test_management.errors import TestJobExecutionError
from app.modules.test_management.models import (
    TEST_JOB_TIMEOUT,
    TestEnvNode,
    TestEnvNodeStatus,
    TestEnvSet,
    TestEnvSetStatus,
    TestJob,
    test_job_deadline,
)
from app.modules.test_management.service import record_test_job_event
from app.modules.users.models import User
from app.modules.vms.models import VMRequest, VMRequestStatus
from app.modules.vms.schemas import VMRequestCreate
from app.modules.vms.service import create_vm_request, process_vm_destroy, process_vm_request

VM_VCPU_COUNT = 4
VM_MEMORY_MB = 8192

# VM 环境节点：为测试任务的每个环境节点申请/创建 VM、回收销毁 VM。
# keep_env(全保留)时 VM 租约按 5 天设期，留出人工排查窗口；否则按 15h 总超时。
# 销毁走 vms 模块的 process_vm_destroy，保证 VM 与租约状态一致清理。


@dataclass(frozen=True)
class VMNodeRuntime:
    """环境节点运行态：解密后的 SSH 连接信息，供 mugen_runner 直接用。"""

    resource: Resource
    ip: str
    username: str
    password: str


def node_resource(db: Session, node: TestEnvNode) -> Resource:
    if not node.resource_id:
        raise TestJobExecutionError("vm_missing", "Test env node has no VM resource")
    resource = db.get(Resource, node.resource_id)
    if resource is None or resource.deleted_at is not None or not resource.primary_ip:
        raise TestJobExecutionError("vm_missing", "Test env node VM is unavailable")
    return resource


def node_runtime(db: Session, node: TestEnvNode) -> VMNodeRuntime:
    resource = node_resource(db, node)
    return VMNodeRuntime(
        resource=resource,
        ip=resource.primary_ip or "",
        username=resource.ssh_username,
        password=decrypt_secret(resource.ssh_password_ciphertext),
    )


def create_env_node_vm(
    db: Session,
    *,
    job: TestJob,
    env_set: TestEnvSet,
    node: TestEnvNode,
    actor: User,
) -> bool:
    """为环境节点申请并创建 VM，成功后置 ready。

    os_version 含 -64k 时由 vms 模块在创建时装 64k 内核并重启(见内联注释)。
    expected_ends_at 按 keep_env 选 5 天或 15h。创建结果经 process_vm_request
    同步等待；失败按 error_code 映射 vm_create_failed/task_timeout。
    """
    node.status = TestEnvNodeStatus.CREATING.value
    if job.keep_env:
        expected_ends_at = job.created_at + timedelta(days=5)
    else:
        expected_ends_at = job.created_at + TEST_JOB_TIMEOUT
    data_disk_count = max(1, env_set.add_disk_num)
    # -64k 信号传给 process_vm_request → apply_kernel_64k 在 VM 创建时装 64k + 重启。
    # find_image 内部对 -64k 做 strip（用 4k base 镜像），request.os_version 保留 -64k。
    # release 的内核变体快照在 job.pipeline_extras（update 为 None → 不换内核）。
    extras = job.pipeline_extras or {}
    request = create_vm_request(
        db,
        actor=actor,
        payload=VMRequestCreate(
            dist=job.dist,
            os_version=job.os_version,
            image_round=job.image_round,
            arch=job.arch,
            vcpu_count=VM_VCPU_COUNT,
            memory_mb=VM_MEMORY_MB,
            data_disk_count=data_disk_count,
            extra_nic_num=env_set.add_nic_num,
            purpose=f"测试任务 {job.name} / env {env_set.set_index} / {node.role}",
            expected_ends_at=expected_ends_at,
            kernel_variant=extras.get("kernel_variant"),
            kernel_rpm_url=extras.get("kernel_rpm_url"),
        ),
    )
    request.task_id = job.task_id
    request_id = request.id
    node.vm_request_id = request_id
    record_test_job_event(
        db,
        job=job,
        phase="vm_create_started",
        message=f"开始创建 env {env_set.set_index} {node.role} VM",
    )
    db.commit()

    kernel_64k_transferred = process_vm_request(
        request_id,
        deadline=test_job_deadline(job),
        serialize_per_host=True,
        allow_kernel_64k_round_fallback=False,
    )
    db.expire_all()
    request = db.get(VMRequest, request_id)
    if (
        request is None
        or request.status != VMRequestStatus.SUCCEEDED.value
        or not request.resource_id
    ):
        node.status = TestEnvNodeStatus.ERROR.value
        message = request.error_message if request else "VM request is missing"
        error_code = (
            "task_timeout"
            if request and request.error_code == "task_timeout"
            else "vm_create_failed"
        )
        raise TestJobExecutionError(error_code, message or "VM create failed")

    node.resource_id = request.resource_id
    resource = db.get(Resource, request.resource_id)
    node.primary_ip = resource.primary_ip if resource else None
    if kernel_64k_transferred is False:
        node.status = TestEnvNodeStatus.NOT_EXECUTED.value
        record_test_job_event(
            db,
            job=job,
            phase="kernel_64k_not_transferred",
            message="最新 update repo 未转测 kernel-64k，本环境不执行测试",
            level="warning",
        )
        db.commit()
        return False
    node.status = TestEnvNodeStatus.READY.value
    record_test_job_event(
        db,
        job=job,
        phase="vm_create_succeeded",
        message=f"env {env_set.set_index} {node.role} VM 创建完成",
    )
    db.commit()
    return True


def destroy_env_node_vm(db: Session, *, job: TestJob, node: TestEnvNode, actor: User) -> None:
    if not node.resource_id or node.status == TestEnvNodeStatus.DESTROYED.value:
        return
    resource = db.get(Resource, node.resource_id)
    if resource is None:
        raise TestJobExecutionError("vm_destroy_failed", "VM resource is missing")
    lease = get_resource_active_lease(db, resource)
    if lease is None:
        raise TestJobExecutionError("vm_destroy_failed", "VM active lease is missing")
    record_test_job_event(
        db,
        job=job,
        phase="vm_destroy_started",
        message=f"开始销毁 env node {node.node_index} VM",
    )
    db.commit()
    destroyed = process_vm_destroy(
        resource.id,
        lease.id,
        actor.id,
        "test job finished",
        False,
        task_id=job.task_id,
    )
    db.expire_all()
    if not destroyed:
        record_test_job_event(
            db,
            job=job,
            phase="vm_destroy_failed",
            message=f"env node {node.node_index} VM destroy failed",
            level="error",
            error_code="vm_destroy_failed",
        )
        db.commit()
        raise TestJobExecutionError("vm_destroy_failed", "VM destroy failed")
    node.status = TestEnvNodeStatus.DESTROYED.value
    record_test_job_event(
        db,
        job=job,
        phase="vm_destroy_succeeded",
        message=f"env node {node.node_index} VM 销毁流程已执行",
    )
    db.commit()


def cleanup_env_vms(
    db: Session,
    *,
    job: TestJob,
    env_set: TestEnvSet,
    actor: User,
    preserve: bool,
) -> None:
    """清理环境集全部 VM。preserve=True 保留失败环境不动；否则逐节点销毁，
    任一节点失败汇总成 error 并抛出，状态收敛到 destroyed/error。
    """
    if preserve:
        record_test_job_event(
            db,
            job=job,
            phase="env_preserved",
            message=f"env {env_set.set_index} 因测试失败被保留",
        )
        return
    env_set.status = TestEnvSetStatus.DESTROYING.value
    db.commit()
    errors: list[str] = []
    for node in env_set.nodes:
        try:
            destroy_env_node_vm(db, job=job, node=node, actor=actor)
        except TestJobExecutionError as exc:
            errors.append(f"node {node.node_index}: {exc}")
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            errors.append(f"node {node.node_index}: {exc}")
    if errors:
        env_set.status = TestEnvSetStatus.ERROR.value
        db.commit()
        raise TestJobExecutionError("vm_destroy_failed", "; ".join(errors))
    env_set.status = TestEnvSetStatus.DESTROYED.value
    db.commit()

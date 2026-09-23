# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from time import sleep as _sleep

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.resources.models import ManagementStatus
from app.modules.resources.physical_install_models import PhysicalInstallImage
from app.modules.tasks.service import make_event_recorder
from app.modules.test_management.errors import TestJobExecutionError
from app.modules.test_management.models import (
    TestEnvNode,
    TestEnvNodeStatus,
    TestEnvSet,
    TestJob,
    remaining_test_job_seconds,
)
from app.modules.test_management.physical_resources import (
    claim_available_owned_physical_resource,
    has_matching_owned_physical_resource,
)
from app.modules.test_management.service import record_test_job_event
from app.modules.users.models import User

# 物理机环境节点：复用触发人已占用的物理机(usage_scenario=<module>-update)，
# PXE 重装到目标 OS 后供 mugen 使用。物理机不归 radiaTest 销毁，故 cleanup 为空操作。


def _find_install_image(db: Session, *, os_version: str, arch: str) -> PhysicalInstallImage | None:
    """查找与 pipeline 版本 + arch 匹配的安装镜像。

    job.os_version 是短形(如 ``24.03-LTS-SP3``)；镜像的 os_version 是全形
    (``openEuler-24.03-LTS-SP3``)。-64k 变体没有独立的 PXE 镜像——
    用基础版本装 OS，64k 内核由 install_kernel_64k_via_ssh 单独安装。
    """
    target = os_version if os_version.startswith("openEuler-") else f"openEuler-{os_version}"
    if target.endswith("-64k"):
        target = target[: -len("-64k")]
    stmt = select(PhysicalInstallImage).where(
        PhysicalInstallImage.os_version == target,
        PhysicalInstallImage.arch == arch,
    )
    return db.execute(stmt).scalars().first()


def create_env_node_physical(
    db: Session,
    *,
    job: TestJob,
    env_set: TestEnvSet,
    node: TestEnvNode,
    actor: User,
) -> bool:
    """为物理机 RunJob 获取 env node。

    使用触发者已占用的物理机(arch 匹配)，PXE 重装到 pipeline 指定 OS，等待
    SSH 上线后把 node 标记为 ready 供 mugen 使用。(所有物理机 RunJob 都先重装再测试。)
    """
    node.status = TestEnvNodeStatus.CREATING.value
    db.commit()

    # Pipeline snapshots this value onto the Test Job at creation time, so
    # execution does not need to resolve Pipeline-owned state.
    usage_scenario = job.physical_usage_scenario or ""
    module_name = usage_scenario.removesuffix("-update")

    while True:
        resource = claim_available_owned_physical_resource(
            db,
            node=node,
            arch=job.arch,
            actor_id=actor.id,
            usage_scenario=usage_scenario,
        )
        if resource is not None:
            break
        if not has_matching_owned_physical_resource(
            db,
            arch=job.arch,
            actor_id=actor.id,
            usage_scenario=usage_scenario,
        ):
            node.status = TestEnvNodeStatus.ERROR.value
            raise TestJobExecutionError(
                "physical_resource_unavailable",
                f"No occupied physical resource with usage_scenario="
                f"{usage_scenario or '<module>-update'} for arch {job.arch} "
                f"(user {actor.username}); occupy a "
                f"{usage_scenario or 'matching'} machine before triggering the pipeline",
            )
        wait_seconds = remaining_test_job_seconds(job, maximum=60)
        if wait_seconds <= 0:
            node.status = TestEnvNodeStatus.ERROR.value
            raise TestJobExecutionError(
                "task_timeout",
                "等待测试空闲物理机超过测试任务 15 小时总截止时间",
            )
        _sleep(wait_seconds)
        db.expire_all()

    image = _find_install_image(db, os_version=job.os_version, arch=job.arch)
    if image is None:
        node.status = TestEnvNodeStatus.ERROR.value
        raise TestJobExecutionError(
            "install_image_unavailable",
            f"No physical_install_image for os_version={job.os_version} arch={job.arch}",
        )

    # PXE reinstall the occupied machine; blocks until SSH is up.
    # Opens its own DB session (the install is a self-contained operation).
    from app.modules.vms.pxe_install import run_pxe_install

    record_test_job_event(
        db,
        job=job,
        phase="pxe_reinstall_start",
        message=(f"开始 PXE 重装 {resource.resource_code} → {image.os_version} (最长 30 分钟)"),
    )
    db.commit()
    from app.modules.vms.service import Kernel64kNotTransferredError

    try:
        installed = run_pxe_install(
            resource_id=resource.id,
            image_id=image.id,
            actor_user_id=actor.id,
            target_os_version=job.os_version,
        )
    except Kernel64kNotTransferredError:
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
    if not installed:
        node.status = TestEnvNodeStatus.ERROR.value
        raise TestJobExecutionError(
            "pxe_reinstall_failed",
            f"PXE reinstall failed for {resource.primary_ip}; "
            "see task_events (pxe_failed) for details",
        )

    record_test_job_event(
        db,
        job=job,
        phase="pxe_reinstall_done",
        message=f"PXE 重装完成，SSH 已通 ({resource.primary_ip})",
    )
    db.commit()

    # kernel 模块 + 非 -64k：PXE 重装成功后、标 READY 前装最新 update 内核 + 重启
    # （[ADR 0026]）。-64k 变体由 run_pxe_install Step 6 的 64k 路径处理，不重复触发。
    if module_name == "kernel" and job.os_version and not job.os_version.endswith("-64k"):
        from app.modules.vms.service import (
            LatestKernelInstallError,
            install_latest_kernel_via_ssh,
        )

        record_event = make_event_recorder(record_test_job_event, db=db, job=job)

        record_event(
            "kernel_swap_start",
            f"开始装最新 update 内核 + reboot ({resource.primary_ip})",
        )
        db.commit()
        try:
            install_latest_kernel_via_ssh(
                os_version=job.os_version,
                resource=resource,
                record_event=record_event,
            )
        except LatestKernelInstallError as exc:
            resource.management_status = ManagementStatus.DISABLED.value
            db.commit()
            node.status = TestEnvNodeStatus.ERROR.value
            raise TestJobExecutionError(
                "kernel_install_failed",
                f"latest kernel install failed for {resource.primary_ip}; "
                "see task_events (kernel_latest_install_failed) for details",
            ) from exc


    node.status = TestEnvNodeStatus.READY.value
    record_test_job_event(
        db,
        job=job,
        phase="physical_node_ready",
        message=(
            f"env {env_set.set_index} {node.role} physical resource "
            f"{resource.resource_code} reinstalled to {image.os_version}"
        ),
    )
    db.commit()
    return True


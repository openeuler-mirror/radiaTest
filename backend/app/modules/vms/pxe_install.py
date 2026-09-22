# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""物理机 PXE 安装编排。

5 步流程(单个 Celery 任务)：
1. run_host_script 在 PXE server 上同步启动文件 + 绑定 dhcp
2. ipmitool 在 worker 上设置 PXE 启动 + power reset
3. SSH 循环探测目标 IP，等待安装完成
4. 更新资源凭据 + os_version
5. 恢复 management_status 为 active
"""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.db.session import SessionLocal
from app.modules.resources.models import ManagementStatus, Resource, ResourceType
from app.modules.resources.physical_install_models import PhysicalInstallImage
from app.modules.tasks.models import TaskEvent
from app.modules.test_management.remote import (
    RemoteCommandError,
    RemoteRunOptions,
    RemoteTarget,
    run_ssh_command,
)
from app.modules.vms.host_contract import PXEInstallPayload, PXEInstallResult
from app.modules.vms.host_runner import HostEventSink, HostScriptError, run_host_script
from app.modules.vms.service import (
    Kernel64kInstallError,
    Kernel64kNotFoundError,
    Kernel64kNotTransferredError,
    UnsupportedKernel64kVersionError,
    install_kernel_64k_via_ssh,
)
from app.worker import celery_app

logger = logging.getLogger(__name__)

DEFAULT_ROOT_PASSWORD = "openEuler12#$"
SSH_CHECK_INTERVAL = 10
SSH_CHECK_MAX_ATTEMPTS = 360  # 60 minutes
IPMITOOL_TIMEOUT = 60
TASK_TYPE_PXE_INSTALL = "pxe_install"
SUBJECT_TYPE_RESOURCE = "resource"


def _find_pxe_server(db: Session) -> Resource:
    """查找 PXE server 资源(usage_scenario='pxe-host'，PHYSICAL 类型)。

    按 usage_scenario 而非 JSON tag 包含查询，因为 PostgreSQL 的 ``tags``
    列是普通 ``JSON``(非 ``JSONB``)，``@>`` 操作符仅对 ``jsonb`` 定义。
    资源创建时同时打 ``pxe-host`` tag 和 ``usage_scenario='pxe-host'``。
    """
    from app.modules.resources.models import Resource as Res

    return (
        db.execute(
            select(Res).where(
                Res.resource_type == ResourceType.PHYSICAL.value,
                Res.usage_scenario == "pxe-host",
            )
        )
        .scalars()
        .first()
    )


@dataclass(frozen=True)
class PXEEventDraft:
    """PXE 装机任务事件草稿。"""

    subject_id: str
    phase: str
    message: str
    level: str = "info"
    error_code: str | None = None


def _record_event(
    db: Session,
    *,
    event: PXEEventDraft,
) -> None:
    subject_id = event.subject_id
    phase = event.phase
    message = event.message
    level = event.level
    error_code = event.error_code
    db.add(
        TaskEvent(
            task_type=TASK_TYPE_PXE_INSTALL,
            subject_type=SUBJECT_TYPE_RESOURCE,
            subject_id=subject_id,
            phase=phase,
            level=level,
            message=message,
            error_code=error_code,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()


def _build_event_sink(db: Session, subject_id: str) -> HostEventSink:
    def sink(phase: str, message: str) -> None:
        _record_event(
            db,
            event=PXEEventDraft(
            subject_id=subject_id,
            phase=phase,
            message=message,
            ),
        )

    return sink


def _ipmitool_pxe_boot(bmc_ip: str, bmc_username: str, bmc_password: str) -> tuple[int, str]:
    """运行 ipmitool 设置 PXE 启动并 power reset。返回 (exit_code, output)。"""
    ipmi_base = [
        "ipmitool",
        "-I",
        "lanplus",
        "-H",
        bmc_ip,
        "-U",
        bmc_username,
        "-P",
        bmc_password,
    ]
    commands = [
        ipmi_base + ["chassis", "bootdev", "disk", "options=persistent"],
        ipmi_base + ["chassis", "bootdev", "pxe", "options=efiboot"],
        ipmi_base + ["power", "reset"],
    ]
    output_parts: list[str] = []
    try:
        for command_args in commands:
            completed = subprocess.run(
                command_args,
                capture_output=True,
                text=True,
                timeout=IPMITOOL_TIMEOUT,
            )
            output_parts.append(completed.stdout + completed.stderr)
            if completed.returncode != 0:
                return completed.returncode, "".join(output_parts)
        return 0, "".join(output_parts)
    except subprocess.TimeoutExpired:
        return 1, "ipmitool timed out"
    except FileNotFoundError:
        return 1, "ipmitool not found in worker container"


def _wait_for_ssh(ip: str, password: str) -> bool:
    """循环 SSH 探测直到目标可达。成功返回 True。"""
    for _ in range(SSH_CHECK_MAX_ATTEMPTS):
        try:
            result = run_ssh_command(
                target=RemoteTarget(host=ip, username="root", password=password),
                command="echo ok",
                timeout_seconds=10,
                options=RemoteRunOptions(verify_host_key=False),
            )
            if result.returncode == 0 and "ok" in result.stdout:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(SSH_CHECK_INTERVAL)
    return False


def _collect_nic_macs(host: str, username: str, password: str) -> list[str]:
    """采集目标机全部网卡 MAC（pxe DHCP 全绑，避免绑错启动网卡）。失败返回空。"""
    try:
        result = run_ssh_command(
            target=RemoteTarget(host=host, username=username, password=password),
            command="cat /sys/class/net/*/address",
            timeout_seconds=20,
            options=RemoteRunOptions(verify_host_key=False),
        )
    except RemoteCommandError:
        return []
    if result.returncode != 0:
        return []
    return sorted(
        {
            m.strip().lower()
            for m in result.stdout.splitlines()
            if m.strip() and m.strip() != "00:00:00:00:00:00"
        }
    )


def apply_kernel_64k_to_physical(
    db: Session,
    *,
    resource: Resource,
    os_version: str,
    subject_id: str,
) -> None:
    """物理机 64k 后处理入口（resource 事件）：委托 install_kernel_64k_via_ssh。

    与 VM 的 apply_kernel_64k 共享 install_kernel_64k_via_ssh，仅事件记录器不同
    （_record_event：subject_type=resource, task_type=pxe_install）。物理机只查询最新
    update round；未转测由调用方保留基础系统，其余安装故障禁用资源。
    """

    def record_event(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        _record_event(
            db,
            event=PXEEventDraft(
            subject_id=subject_id,
            phase=phase,
            message=message,
            level=level,
            error_code=error_code,
            ),
        )

    install_kernel_64k_via_ssh(
        db,
        os_version=os_version,
        resource=resource,
        record_event=record_event,
        allow_round_fallback=False,
    )


def _ssh_cat(ip: str, path: str) -> str:
    """SSH 读取文件内容，失败返回空串。"""
    try:
        result = run_ssh_command(
            target=RemoteTarget(host=ip, username="root", password=DEFAULT_ROOT_PASSWORD),
            command=f"cat {shlex.quote(path)}",
            timeout_seconds=15,
            options=RemoteRunOptions(verify_host_key=False),
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def _verify_install_os(resource: Resource, image: PhysicalInstallImage) -> None:
    """装机后校验：os-release 匹配目标版本 + 安装标记(round)一致，不符则失败。

    防"老系统被误判为装机完成"：`_wait_for_ssh` 只保证 SSH 通（默认密码），
    无法区分新装/旧系统；此处在回写凭据与 os_version 之前校验。
    """
    ip = resource.primary_ip or ""
    os_release = _ssh_cat(ip, "/etc/os-release")
    version_token = image.os_version.split("-")[1] if "-" in image.os_version else image.os_version
    # 边界匹配（含中文/相邻版本也命中），避免 "24" 命中 24.09。
    if not re.search(
        rf"(?<![0-9A-Za-z]){re.escape(version_token)}(?![0-9A-Za-z])",
        os_release,
    ):
        raise RuntimeError(
            f"装机校验失败：os-release 不含目标版本 {version_token}（安装未完成或仍是旧系统）"
        )
    # official/RC 都校验轮次标记（ks %post 统一写入）。
    marker = _ssh_cat(ip, "/root/.kronos-install-marker").strip()
    expected = f"{image.os_version} {image.round or 'official'}"
    if marker != expected:
        raise RuntimeError(
            f"装机校验失败：安装轮次标记不符（期望 {expected!r}，实际 {marker!r}）"
        )


def apply_custom_kernel_to_physical(
    db: Session,
    *,
    resource: Resource,
    image: PhysicalInstallImage,
    subject_id: str,
) -> None:
    """物理机装后换内核（base+swap 变体），复用 VM 的 install_custom_kernel_via_ssh。

    失败 raise CustomKernelError；上层按宽容策略处理（保留基础系统可用）。
    """

    def record_event(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        _record_event(
            db,
            event=PXEEventDraft(
            subject_id=subject_id,
            phase=phase,
            message=message,
            level=level,
            error_code=error_code,
            ),
        )

    from dataclasses import dataclass

    from app.modules.vms.service import CustomKernelSwapRequest, install_custom_kernel_via_ssh

    @dataclass
    class _PhysicalKernelSwapRequest(CustomKernelSwapRequest):
        os_version: str
        image_round: str | None
        kernel_variant: str | None
        kernel_rpm_url: str | None = None
        arch: str = ""

    request = _PhysicalKernelSwapRequest(
        os_version=image.os_version,
        image_round=image.round,
        kernel_variant=image.swap_kernel_variant,
        arch=image.arch,
    )
    install_custom_kernel_via_ssh(
        db, request=request, resource=resource, record_event=record_event
    )


def run_pxe_install(
    *,
    resource_id: str,
    image_id: str,
    actor_user_id: str = "",
    target_os_version: str | None = None,
) -> bool:
    """PXE 安装编排(同步)。自带独立 DB 会话。

    由 Celery 任务 ``run_pxe_install_task`` 与 pipeline physical-env 准备
    调用(mugen 之前须先完成安装)。流水线传入带 ``-64k`` 的目标版本时，
    PXE 基础系统安装后同步完成 64k 内核后处理才返回成功。
    """
    from app.core.credentials import encrypt_secret

    with SessionLocal() as db:
        resource = db.get(Resource, resource_id)
        if resource is None:
            return False
        if resource.resource_type != ResourceType.PHYSICAL.value:
            return False

        image = db.get(PhysicalInstallImage, image_id)
        if image is None:
            return False

        spec = resource.physical_spec
        if spec is None or not spec.bmc_ip:
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=resource_id,
                phase="pxe_failed",
                message="物理机缺少 BMC 信息（physical_spec 未配置或无 bmc_ip）",
                level="error",
                ),
            )
            resource.management_status = ManagementStatus.ACTIVE.value
            db.commit()
            return False

        pxe_server = _find_pxe_server(db)
        if pxe_server is None or not pxe_server.primary_ip:
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=resource_id,
                phase="pxe_failed",
                message="PXE 服务器未找到或无 IP",
                level="error",
                ),
            )
            resource.management_status = ManagementStatus.ACTIVE.value
            db.commit()
            return False

        # Set maintenance
        resource.management_status = ManagementStatus.MAINTENANCE.value
        db.commit()

        subject_id = resource_id
        event_sink = _build_event_sink(db, subject_id)

        # Decrypt BMC password
        bmc_password = decrypt_secret(spec.bmc_password_ciphertext or "")

        try:
            # Step 1+2: sync boot files + bind dhcp (on PXE server)
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_sync_files",
                message="开始同步引导文件",
                ),
            )
            nics = [resource.mac_address or ""] + _collect_nic_macs(
                resource.primary_ip or "", resource.ssh_username or "root", decrypt_secret(
                    resource.ssh_password_ciphertext
                )
            )
            payload = PXEInstallPayload(
                target_mac=resource.mac_address or "",
                target_ip=resource.primary_ip or "",
                efi_url=image.efi_url,
                repo_url=image.repo_url,
                iso_url=image.iso_url,
                round=image.round,
                kernel_variant=image.kernel_variant,
                arch=image.arch,
                os_name=image.os_version,
                nics=sorted(set(n for n in nics if n)),
            )
            result = run_host_script(
                host_ip=pxe_server.primary_ip,
                script_name="pxe-install.sh",
                payload=payload,
                result_model=PXEInstallResult,
                event_sink=event_sink,
                timeout_seconds=600 if image.iso_url else 120,
            )
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_bind_dhcp",
                message=f"DHCP 绑定完成: EFI={result.efi_relative_path}",
                ),
            )

            # Step 3: ipmitool set PXE boot + power reset
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_ipmi_boot",
                message="开始 IPMI PXE 启动",
                ),
            )
            exit_code, output = _ipmitool_pxe_boot(
                bmc_ip=spec.bmc_ip or "",
                bmc_username=spec.bmc_username or "",
                bmc_password=bmc_password,
            )
            if exit_code != 0:
                raise RuntimeError(f"ipmitool 失败: {output}")
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_ipmi_boot",
                message="IPMI PXE 启动完成，物理机正在重启",
                ),
            )

            # Step 4: wait for SSH
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_installing",
                message="等待装机完成（最长 30 分钟）",
                ),
            )
            if not _wait_for_ssh(resource.primary_ip or "", DEFAULT_ROOT_PASSWORD):
                raise RuntimeError("装机超时：30 分钟内 SSH 不可达")

            # Step 5: 装机校验（防假成功）。校验通过前不回写凭据/os_version。
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_verifying",
                message="校验装机结果（os-release + 轮次标记）",
                ),
            )
            _verify_install_os(resource, image)

            # Step 6: update credentials + os_version。
            resource.ssh_password_ciphertext = encrypt_secret(DEFAULT_ROOT_PASSWORD)
            resource.os_version = image.os_version
            db.commit()

            # Step 7: 换内核（base+swap 变体）。失败宽容：保留基础系统，继续恢复 active。
            if image.swap_kernel_variant:
                _record_event(
                    db,
                    event=PXEEventDraft(
                    subject_id=subject_id,
                    phase="kernel_swap_started",
                    message=f"开始换内核到 {image.swap_kernel_variant}",
                    ),
                )
                try:
                    apply_custom_kernel_to_physical(
                        db,
                        resource=resource,
                        image=image,
                        subject_id=subject_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    # 宽容策略：任何换内核失败（含 SSH/传输异常）都保留基础系统、
                    # 资源恢复 active，事件明确标注"换内核未完成 + 来源"。
                    _record_event(
                        db,
                        event=PXEEventDraft(
                        subject_id=subject_id,
                        phase="kernel_swap_failed",
                        level="warning",
                        message=f"换内核未完成，当前保留基础内核，来源见任务日志: {exc}",
                        ),
                    )

            # Step 8: 硬件探测（尽力而为）。
            try:
                from app.modules.resources.hardware_probe import (
                    probe_physical_hardware,
                )
                from app.modules.resources.service import apply_hardware_probe

                probe = probe_physical_hardware(
                    host=resource.primary_ip or "",
                    username="root",
                    password=DEFAULT_ROOT_PASSWORD,
                )
                apply_hardware_probe(db, resource, probe)
            except Exception:
                # 安装成功后的硬件探测属尽力而为,失败不影响安装结果;留 debug 便于排查。
                logger.debug("post-install hardware probe failed", exc_info=True)
            db.commit()

            # Step 9: 64k kernel post-processing (only when os_version ends with -64k).
            # Shared core with VM 64k. Missing latest-round content leaves the base OS
            # usable; an operational failure disables the physical resource.
            try:
                apply_kernel_64k_to_physical(
                    db,
                    resource=resource,
                    os_version=target_os_version or image.os_version,
                    subject_id=subject_id,
                )
            except Kernel64kNotTransferredError:
                resource.management_status = ManagementStatus.ACTIVE.value
                db.commit()
                raise
            except (Kernel64kInstallError, Kernel64kNotFoundError):
                resource.management_status = ManagementStatus.DISABLED.value
                db.commit()
                return False
            except UnsupportedKernel64kVersionError:
                resource.management_status = ManagementStatus.ACTIVE.value
                db.commit()
                return False
            except Exception as exc:  # noqa: BLE001
                # Remote transport/write failures during 64k provisioning are
                # operational failures too; keep the machine out of scheduling.
                _record_event(
                    db,
                    event=PXEEventDraft(
                    subject_id=subject_id,
                    phase="kernel_64k_install_failed",
                    message=f"64k 内核后处理异常: {exc}",
                    level="error",
                    error_code="kernel_64k_install_failed",
                    ),
                )
                resource.management_status = ManagementStatus.DISABLED.value
                db.commit()
                return False

            resource.management_status = ManagementStatus.ACTIVE.value
            db.commit()

            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_finished",
                message=f"物理机 {resource.primary_ip} 安装 "
                    f"{target_os_version or image.os_version} 完成",
                ),
            )
            return True

        except Kernel64kNotTransferredError:
            raise
        except HostScriptError as exc:
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_failed",
                message=f"PXE 脚本失败: {exc}",
                level="error",
                ),
            )
            resource.management_status = ManagementStatus.ACTIVE.value
            db.commit()
            return False
        except Exception as exc:  # noqa: BLE001
            _record_event(
                db,
                event=PXEEventDraft(
                subject_id=subject_id,
                phase="pxe_failed",
                message=f"装机异常: {exc}",
                level="error",
                ),
            )
            resource.management_status = ManagementStatus.ACTIVE.value
            db.commit()
            return False


@celery_app.task(
    bind=True,
    name="app.modules.vms.pxe_install.run_pxe_install_task",
    soft_time_limit=90 * 60,
)
def run_pxe_install_task(
    self: object,
    resource_id: str,
    image_id: str,
    actor_user_id: str,
) -> None:
    """PXE 安装编排任务(异步入口)。同步逻辑在 run_pxe_install。"""
    run_pxe_install(
        resource_id=resource_id,
        image_id=image_id,
        actor_user_id=actor_user_id,
    )

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import secrets
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol
from urllib.request import urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.pagination import PAGE_SIZE, PageParams
from app.db.session import SessionLocal
from app.modules.audit.service import record_audit_log
from app.modules.leases.models import LeaseEventType, ResourceLease
from app.modules.leases.schemas import LeaseCreate, LeaseReleaseNormalized
from app.modules.leases.service import (
    LEASE_DEADLINE_TOLERANCE,
    MAX_NON_ADMIN_LEASE,
    create_lease,
    get_active_lease,
    get_active_leases_by_resource_id,
    get_resource_active_lease,
    record_lease_event,
    release_lease,
)
from app.modules.resources.models import (
    ManagementStatus,
    OccupancyStatus,
    Resource,
    ResourceType,
)
from app.modules.resources.schemas import ResourceCreate, ResourceListParams, ResourceRead
from app.modules.resources.service import (
    create_resource,
    list_resources,
    serialize_resource,
    serialize_resources,
)
from app.modules.tasks.models import TaskEvent
from app.modules.tasks.service import list_task_events, record_task_event
from app.modules.users.models import User, UserRole
from app.modules.vms.execution_state import (
    clear_vm_destroy_execution,
    get_vm_destroy_execution,
    mark_vm_destroy_queued,
    mark_vm_destroy_started,
)
from app.modules.vms.host_contract import (
    VMHostCreatePayload,
    VMHostCreateResult,
    VMHostDestroyPayload,
    VMHostDestroyResult,
    VMHostInspectPayload,
    VMHostInspectResult,
    VMHostPowerPayload,
    VMHostPowerResult,
)
from app.modules.vms.host_runner import HostScriptError, run_host_script
from app.modules.vms.image_discovery import (
    OFFICIAL_IMAGE_ROUND,
    VMImage,
    find_image,
    precheck_custom_kernel,
)
from app.modules.vms.models import VMInstallType, VMRequest, VMRequestStatus
from app.modules.vms.schemas import VMConsoleRead, VMPowerRead, VMRequestCreate, VMRequestRead
from app.worker import celery_app

# VM 领域服务：VM 申请、异步创建、释放、电源、控制台、IP 刷新与 64k 内核后处理。
# 权限与生命周期状态转换集中在此处；宿主脚本调用走 host_runner，并发控制走
# host_lock，销毁执行状态(execution_state)用于跨模块的幂等防重入队。路由只做
# 请求解析与状态码映射。

DATA_DISK_SIZE_GB = 50
MANUAL_SYSTEM_DISK_SIZE_GB = 50
VM_HOST_TAG = "vm-host"
TASK_TYPE_VM_CREATE = "vm_create"
TASK_TYPE_VM_DESTROY = "vm_destroy"
SUBJECT_TYPE_VM_REQUEST = "vm_request"
SUBJECT_TYPE_RESOURCE = "resource"
# 命中这些 error_code 时在同一宿主上重试(镜像下载/DHCP/创建/超时属瞬时性故障)。
RETRY_ON_SAME_HOST = {"image_download_failed", "dhcp_ip_not_found", "vm_create_failed", "timeout"}
# 命中这些 error_code 时立即失败不重试(配置错误或依赖缺失，重试无意义)。
NON_RETRYABLE = {"cleanup_failed", "invalid_payload", "worker_dependency_missing"}
# VM 销毁对瞬时连接失败的重试策略：批量释放会同时对同一宿主发起多条 SSH，
# 超出 sshd MaxStartups(默认 10:30:100)的连接在 kex 阶段被重置
# (host_connection_failed)，属瞬时故障；指数退避+抖动的有限重试可自愈。
# 语义性失败(如 vm_destroy_failed)不重试。不可破坏约束：重试事件追加记录，
# 保留原始失败事实，不覆盖历史结果。
VM_DESTROY_CONNECT_RETRY_CODES = {"host_connection_failed"}
VM_DESTROY_RETRY_ATTEMPTS = 3
VM_DESTROY_RETRY_BACKOFF_SECONDS = 2.0
# 创建登记前回读未确认 VM 存在时的错误码：本宿主记 attempt 失败并尝试下一宿主
# (不在 NON_RETRYABLE/RETRY_ON_SAME_HOST 中，走默认的"换宿主"分支)。
VM_NOT_CONFIRMED_AFTER_CREATE = "vm_not_confirmed_after_create"
_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_DHCP_LEASE_PATTERN = re.compile(r"lease\s+([0-9.]+)\s+\{(.*?)\}", re.S | re.I)


class VMPolicyError(Exception):
    """VM 业务规则或权限被违反(如非申请人/ADMIN 取消、超 14 天)。"""


class VMConflictError(Exception):
    """VM 状态冲突(如重复释放、缺少宿主配置、销毁已入队)。"""


class VMQueueUnavailableError(Exception):
    """Celery broker 未配置或投递失败，VM 任务无法入队。"""


class VMImageNotFoundError(Exception):
    """镜像仓库中找不到匹配 (dist, os_version, round, arch) 的镜像。"""


class VMDhcpLeaseNotFoundError(Exception):
    """DHCP 租约文件中找不到该 MAC 的租约(VM 还未拿到 IP 或已过期)。"""


class VMDhcpLeaseFetchError(Exception):
    """拉取 DHCP 租约文件失败(网络不可达或解码错误)。"""


class Kernel64kNotFoundError(Exception):
    """所有 update repo 轮次均无 kernel-64k，普通申请 64k 后处理回滚 VM。"""


class Kernel64kNotTransferredError(Exception):
    """update 流水线最新轮尚未提供 kernel-64k，本轮测试不执行。"""


class Kernel64kInstallError(Exception):
    """kernel-64k 安装、启动或页大小验证失败。"""


class UnsupportedKernel64kVersionError(Exception):
    """请求了平台未明确支持的 64k OS 版本或架构。"""


class LatestKernelInstallError(Exception):
    """kernel 模块物理机装最新 update kernel 失败（dnf install / reboot-SSH 不回 / 无轮次）。"""


# Event sink for install_kernel_64k_via_ssh: (phase, message, *, level, error_code).
InstallKernel64kEventSink = Callable[..., None]
# Generic event sink for kernel install functions: (phase, message, *, level, error_code).
KernelInstallEventSink = Callable[..., None]

SUPPORTED_KERNEL_64K_OS_VERSION = "openEuler-24.03-LTS-SP4-64k"


def canonical_kernel_64k_os_version(os_version: str) -> str:
    """把 Test Job 的短版本规范化为资源与 VM 使用的完整版本。"""
    return os_version if os_version.startswith("openEuler-") else f"openEuler-{os_version}"


def validate_kernel_64k_target(*, os_version: str, arch: str) -> None:
    """后端统一约束当前唯一支持的 64k 版本与架构。"""
    if not os_version.endswith("-64k"):
        return
    if (
        canonical_kernel_64k_os_version(os_version) != SUPPORTED_KERNEL_64K_OS_VERSION
        or arch != "aarch64"
    ):
        raise UnsupportedKernel64kVersionError(
            f"不支持的 64k 目标版本或架构：{os_version}/{arch}；"
            f"当前仅支持 {SUPPORTED_KERNEL_64K_OS_VERSION}/aarch64"
        )


def now_utc() -> datetime:
    return datetime.now(UTC)


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def safe_name(value: str) -> str:
    return _SAFE_NAME_PATTERN.sub("-", value).strip("-")


def image_name_parts(*, os_version: str, image_round: str, arch: str) -> list[str]:
    parts: list[str] = []
    for part in (safe_name(os_version), safe_name(image_round), safe_name(arch)):
        if part:
            parts.append(part)
    return parts


def short_url_hash(url: str) -> str:
    return sha256(url.encode()).hexdigest()[:8]


def vm_name_timestamp() -> str:
    timezone = ZoneInfo(get_settings().display_timezone)
    return now_utc().astimezone(timezone).strftime("%Y%m%dT%H%M%S")


def parse_latest_dhcp_lease_ip(leases_text: str, mac_address: str) -> str | None:
    normalized_mac = mac_address.lower()
    matching_ips: list[str] = []
    hardware_pattern = re.compile(
        rf"hardware\s+ethernet\s+{re.escape(normalized_mac)}\s*;",
        re.I,
    )
    for match in _DHCP_LEASE_PATTERN.finditer(leases_text):
        ip, body = match.group(1), match.group(2)
        if hardware_pattern.search(body):
            matching_ips.append(ip)
    return matching_ips[-1] if matching_ips else None


def fetch_dhcp_leases(url: str) -> str:
    try:
        with urlopen(url, timeout=10) as response:  # noqa: S310
            return response.read().decode()
    except (OSError, UnicodeDecodeError) as exc:
        raise VMDhcpLeaseFetchError(f"Failed to fetch DHCP leases: {exc}") from exc


def request_install_type(request: VMRequest) -> VMInstallType:
    return VMInstallType(request.install_type or VMInstallType.AUTO.value)


def serialize_vm_request(db: Session, request: VMRequest) -> VMRequestRead:
    requester = db.get(User, request.requester_user_id)
    return VMRequestRead(
        id=request.id,
        requester_user_id=request.requester_user_id,
        requester_username=requester.username if requester else None,
        status=VMRequestStatus(request.status),
        purpose=request.purpose,
        expected_ends_at=request.expected_ends_at,
        dist=request.dist,
        os_version=request.os_version,
        image_round=request.image_round,
        arch=request.arch,
        kernel_version=request.kernel_version,
        kernel_variant=request.kernel_variant,
        kernel_rpm_url=request.kernel_rpm_url,
        install_type=request_install_type(request).value,
        image_url=request.image_url,
        vcpu_count=request.vcpu_count,
        memory_mb=request.memory_mb,
        data_disk_count=request.data_disk_count,
        data_disk_size_gb=request.data_disk_size_gb,
        extra_nic_num=request.extra_nic_num or 0,
        resource_id=request.resource_id,
        host_resource_id=request.host_resource_id,
        error_code=request.error_code,
        error_message=request.error_message,
        host_attempts=request.host_attempts,
        created_at=request.created_at,
        updated_at=request.updated_at,
        completed_at=request.completed_at,
        cancelled_at=request.cancelled_at,
    )


@dataclass(frozen=True)
class VMRequestEventDraft:
    """VM 申请任务事件草稿。"""

    request: VMRequest
    phase: str
    message: str
    level: str = "info"
    host: Resource | None = None
    error_code: str | None = None


def record_vm_request_event(
    db: Session,
    *,
    draft: VMRequestEventDraft,
) -> TaskEvent:
    request = draft.request
    phase = draft.phase
    message = draft.message
    level = draft.level
    host = draft.host
    error_code = draft.error_code
    return record_task_event(
        db,
        task_type=TASK_TYPE_VM_CREATE,
        subject_type=SUBJECT_TYPE_VM_REQUEST,
        subject_id=request.id,
        celery_task_id=request.task_id,
        level=level,
        phase=phase,
        message=message,
        host_resource_id=host.id if host else None,
        host_ip=host.primary_ip if host else None,
        error_code=error_code,
    )


@dataclass(frozen=True)
class VMDestroyEventDraft:
    """VM 销毁任务事件草稿。"""

    resource: Resource
    phase: str
    message: str
    celery_task_id: str | None = None
    level: str = "info"
    host: Resource | None = None
    error_code: str | None = None


def record_vm_destroy_event(
    db: Session,
    *,
    draft: VMDestroyEventDraft,
) -> TaskEvent:
    resource = draft.resource
    phase = draft.phase
    message = draft.message
    celery_task_id = draft.celery_task_id
    level = draft.level
    host = draft.host
    error_code = draft.error_code
    return record_task_event(
        db,
        task_type=TASK_TYPE_VM_DESTROY,
        subject_type=SUBJECT_TYPE_RESOURCE,
        subject_id=resource.id,
        celery_task_id=celery_task_id,
        level=level,
        phase=phase,
        message=message,
        host_resource_id=host.id if host else None,
        host_ip=host.primary_ip if host else None,
        error_code=error_code,
    )


def list_vm_request_events(db: Session, request: VMRequest) -> list[TaskEvent]:
    return list_task_events(db, subject_type=SUBJECT_TYPE_VM_REQUEST, subject_id=request.id)


def list_vm_resource_events(db: Session, resource: Resource) -> list[TaskEvent]:
    return list_task_events(db, subject_type=SUBJECT_TYPE_RESOURCE, subject_id=resource.id)


def ensure_vm_lease_window(actor: User, expected_ends_at: datetime | None) -> datetime | None:
    """VM 申请的租期校验(权限边界)。

    ADMIN 可给 None 表示永久租约；TE/TSE 必须提供未来时间且不超过 14 天
    (复用租约模块的 MAX_NON_ADMIN_LEASE + 容差)。与 leases.ensure_occupy_allowed
    保持同一套上限，避免 VM 申请绕过普通租约限制。
    """
    normalized = normalize_datetime(expected_ends_at)
    if actor.role == UserRole.ADMIN.value:
        if normalized is not None and normalized <= now_utc():
            raise VMPolicyError("expected_ends_at must be in the future")
        return normalized

    if normalized is None:
        raise VMPolicyError("TE and TSE VM requests require expected_ends_at")
    if normalized <= now_utc():
        raise VMPolicyError("expected_ends_at must be in the future")

    if normalized > now_utc() + MAX_NON_ADMIN_LEASE + LEASE_DEADLINE_TOLERANCE:
        raise VMPolicyError("TE and TSE VM requests cannot exceed 14 days")
    return normalized


def enqueue_vm_create(request: VMRequest) -> str:
    """
    把 VM 创建任务投递到 Celery。broker 未配置或投递失败时抛
    VMQueueUnavailableError，由调用方把请求标记失败。
    """
    if not get_settings().celery_broker_url:
        raise VMQueueUnavailableError("Celery broker is not configured")
    try:
        task = celery_app.send_task("app.modules.vms.tasks.create_vm_request", args=[request.id])
    except Exception as exc:  # noqa: BLE001
        raise VMQueueUnavailableError(str(exc)) from exc
    return str(task.id)


def enqueue_vm_destroy(
    *,
    resource_id: str,
    lease_id: str,
    actor_user_id: str | None,
    reason: str | None,
    force: bool,
) -> str:
    """
    把 VM 销毁任务投递到 Celery(异步入口)。由租约懒释放或用户主动释放触发，
    broker 不可用时抛 VMQueueUnavailableError。返回 task_id 供 execution_state 记账。
    """
    if not get_settings().celery_broker_url:
        raise VMQueueUnavailableError("Celery broker is not configured")
    try:
        task = celery_app.send_task(
            "app.modules.vms.tasks.destroy_vm",
            kwargs={
                "resource_id": resource_id,
                "lease_id": lease_id,
                "options": {
                    "actor_user_id": actor_user_id,
                    "reason": reason,
                    "force": force,
                },
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise VMQueueUnavailableError(str(exc)) from exc
    return str(task.id)


def create_vm_request(
    db: Session,
    *,
    actor: User,
    payload: VMRequestCreate,
) -> VMRequest:
    expected_ends_at = ensure_vm_lease_window(actor, payload.expected_ends_at)
    validate_kernel_64k_target(os_version=payload.os_version, arch=payload.arch)
    if payload.install_type == VMInstallType.MANUAL:
        image = VMImage(
            dist=payload.dist,
            os_version=payload.os_version,
            image_round=payload.image_round,
            arch=payload.arch,
            url=str(payload.image_url),
        )
    else:
        effective_round = payload.image_round or OFFICIAL_IMAGE_ROUND
        # os_version 带 -64k 后缀时（普通申请 64k），用 base 版查镜像（无 64k 镜像），
        # -64k 信号保留在 request.os_version 上供 apply_kernel_64k 触发后处理。
        lookup_os_version = payload.os_version.removesuffix("-64k")
        image = find_image(
            dist=payload.dist,
            os_version=lookup_os_version,
            image_round=effective_round,
            arch=payload.arch,
        )
        if image is None:
            raise VMImageNotFoundError("VM image does not exist")

    request = VMRequest(
        requester_user_id=actor.id,
        status=VMRequestStatus.PENDING.value,
        purpose=payload.purpose,
        expected_ends_at=expected_ends_at,
        dist=image.dist,
        os_version=image.os_version + ("-64k" if payload.os_version.endswith("-64k") else ""),
        image_round=image.image_round,
        arch=image.arch,
        kernel_version=payload.kernel_version,
        kernel_variant=payload.kernel_variant,
        kernel_rpm_url=payload.kernel_rpm_url,
        install_type=payload.install_type.value,
        image_url=image.url,
        vcpu_count=payload.vcpu_count,
        memory_mb=payload.memory_mb,
        disk_gb=0,
        data_disk_count=payload.data_disk_count,
        data_disk_size_gb=DATA_DISK_SIZE_GB,
        extra_nic_num=payload.extra_nic_num,
        host_attempts=[],
    )
    db.add(request)
    db.flush()
    return request


def queue_vm_request(db: Session, request: VMRequest) -> VMRequest:
    request.task_id = enqueue_vm_create(request)
    record_vm_request_event(
        db,
        draft=VMRequestEventDraft(
        request=request,
        phase="queued",
        message="VM 申请已进入异步队列",
        ),
    )
    db.flush()
    return request


def submit_vm_request(db: Session, *, actor: User, payload: VMRequestCreate) -> VMRequest:
    precheck_custom_kernel(payload)
    request = create_vm_request(db, actor=actor, payload=payload)
    db.commit()
    db.refresh(request)
    try:
        queue_vm_request(db, request)
    except VMQueueUnavailableError as exc:
        fail_request(request, code="queue_unavailable", message=str(exc))
        db.commit()
        raise
    db.commit()
    return request


def paginate_vm_requests(
    db: Session,
    *,
    actor: User,
    show_all: bool,
    pagination: PageParams,
) -> tuple[list[VMRequest], int]:
    statement = select(VMRequest)
    count_statement = select(func.count(VMRequest.id))
    if not show_all:
        statement = statement.where(VMRequest.requester_user_id == actor.id)
        count_statement = count_statement.where(VMRequest.requester_user_id == actor.id)
    statement = (
        statement.order_by(VMRequest.created_at.desc(), VMRequest.id)
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    items = list(db.execute(statement).scalars().all())
    total = db.scalar(count_statement) or 0
    return items, total


def _list_vm_resources(
    db: Session,
    *,
    actor: User,
    show_all: bool,
    search: str | None = None,
) -> list[Resource]:
    params = ResourceListParams(resource_type=ResourceType.VIRTUAL.value)
    resources = list_resources(db, params=params, offset=0, limit=None)
    if search:
        q = search.lower()
        matched: list[Resource] = []
        for r in resources:
            haystack = (
                r.name or "",
                r.primary_ip or "",
                r.os_version or "",
                r.arch or "",
                r.resource_code or "",
                r.management_status or "",
            )
            if any(q in field.lower() for field in haystack):
                matched.append(r)
        resources = matched
    if show_all:
        return resources
    active_leases = get_active_leases_by_resource_id(db, resources)
    return [
        resource
        for resource in resources
        if active_leases.get(resource.id) and active_leases[resource.id].user_id == actor.id
    ]


def list_vms(db: Session, *, actor: User, show_all: bool) -> list[ResourceRead]:
    resources = _list_vm_resources(db, actor=actor, show_all=show_all)
    return serialize_resources(db, resources)


def paginate_vms(
    db: Session,
    *,
    actor: User,
    show_all: bool,
    pagination: PageParams,
    search: str | None = None,
) -> tuple[list[ResourceRead], int]:
    resources = _list_vm_resources(db, actor=actor, show_all=show_all, search=search)
    page_resources = resources[pagination.offset:pagination.offset + PAGE_SIZE]
    return serialize_resources(db, page_resources), len(resources)


def cancel_vm_request(db: Session, *, request: VMRequest, actor: User) -> VMRequest:
    if request.requester_user_id != actor.id and actor.role != UserRole.ADMIN.value:
        raise VMPolicyError("Only requester or ADMIN can cancel VM requests")
    if request.status != VMRequestStatus.PENDING.value:
        raise VMConflictError("Only pending VM requests can be cancelled")
    cancelled_at = now_utc()
    result = db.execute(
        update(VMRequest)
        .where(
            VMRequest.id == request.id,
            VMRequest.status == VMRequestStatus.PENDING.value,
        )
        .values(
            status=VMRequestStatus.CANCELLED.value,
            cancelled_at=cancelled_at,
            completed_at=cancelled_at,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise VMConflictError("Only pending VM requests can be cancelled")
    db.refresh(request)
    return request


def get_vm_request(db: Session, request_id: str) -> VMRequest | None:
    return db.get(VMRequest, request_id)


def find_vm_hosts(db: Session, *, arch: str) -> list[Resource]:
    statement = (
        select(Resource)
        .options(selectinload(Resource.physical_spec))
        .where(
            Resource.deleted_at.is_(None),
            Resource.resource_type == ResourceType.PHYSICAL.value,
            Resource.management_status == ManagementStatus.ACTIVE.value,
            Resource.arch == arch,
        )
    )
    candidates = db.execute(statement).scalars().all()
    return [resource for resource in candidates if VM_HOST_TAG in (resource.tags or [])]


def cache_filename(image: VMImage | VMRequest) -> str:
    parts = image_name_parts(
        os_version=image.os_version,
        image_round=image.image_round,
        arch=image.arch,
    )
    install_type = getattr(image, "install_type", VMInstallType.AUTO.value)
    if install_type == VMInstallType.MANUAL.value:
        return f"manual-iso-{short_url_hash(image.image_url)}.iso"
    return f"{'-'.join(parts)}.qcow2"


def make_vm_name(request: VMRequest, vm_uuid: str) -> str:
    timestamp = vm_name_timestamp()
    parts = image_name_parts(
        os_version=request.os_version,
        image_round=request.image_round,
        arch=request.arch,
    )
    return "-".join([*parts, timestamp, vm_uuid])


@dataclass(frozen=True)
class VMAttemptUpdate:
    """一次宿主尝试的状态更新。"""

    host: Resource
    attempt: int
    status: str
    error_code: str | None = None
    error_message: str | None = None


def append_attempt(
    request: VMRequest,
    *,
    draft: VMAttemptUpdate,
) -> None:
    host = draft.host
    attempt = draft.attempt
    status = draft.status
    error_code = draft.error_code
    error_message = draft.error_message
    request.host_attempts = [
        *request.host_attempts,
        {
            "host_resource_id": host.id,
            "host_ip": host.primary_ip,
            "attempt": attempt,
            "status": status,
            "error_code": error_code,
            "error_message": error_message,
        },
    ]


def build_create_payload(
    request: VMRequest,
    host: Resource,
    vm_uuid: str,
    vm_name: str,
) -> VMHostCreatePayload:
    settings = get_settings()
    return VMHostCreatePayload(
        vm_uuid=vm_uuid,
        vm_name=vm_name,
        install_type=request_install_type(request),
        image_url=request.image_url,
        cache_filename=cache_filename(request),
        arch=request.arch,
        system_disk_size_gb=MANUAL_SYSTEM_DISK_SIZE_GB,
        vcpu_count=request.vcpu_count,
        memory_mb=request.memory_mb,
        data_disk_count=request.data_disk_count,
        data_disk_size_gb=request.data_disk_size_gb,
        extra_nic_num=request.extra_nic_num or 0,
        dhcp_leases_url=settings.vm_dhcp_leases_url,
        network_bridge=settings.vm_network_bridge,
        host_resource_id=host.id,
    )


@dataclass(frozen=True)
class VMResourceCreateSpec:
    """VM 创建成功后的资源落库参数。"""

    request: VMRequest
    host: Resource
    vm_uuid: str
    vm_name: str
    result: VMHostCreateResult


def create_resource_from_vm_result(
    db: Session,
    *,
    draft: VMResourceCreateSpec,
) -> Resource:
    request = draft.request
    host = draft.host
    vm_uuid = draft.vm_uuid
    vm_name = draft.vm_name
    result = draft.result
    settings = get_settings()
    request.disk_gb = result.disk_gb
    payload = ResourceCreate(
        resource_code=vm_uuid,
        resource_type=ResourceType.VIRTUAL,
        name=vm_name,
        primary_ip=result.primary_ip,
        mac_address=result.mac_address,
        arch=request.arch,
        os_version=request.os_version,
        kernel_version=request.kernel_version,
        ssh_username=settings.vm_default_ssh_username,
        ssh_password=settings.vm_default_ssh_password,
        tags=["vm"],
        vm_name=result.vm_name or vm_name,
        vnc_port=result.vnc_port,
        vnc_websocket_port=result.vnc_websocket_port,
        vcpu_count=request.vcpu_count,
        memory_mb=request.memory_mb,
        disk_gb=result.disk_gb,
        host_resource_id=host.id,
        system_disk_path=result.system_disk_path,
        data_disk_count=request.data_disk_count,
        data_disk_size_gb=request.data_disk_size_gb,
        data_disk_paths=result.data_disk_paths,
    )
    return create_resource(db, payload)


def fail_request(request: VMRequest, *, code: str, message: str) -> None:
    request.status = VMRequestStatus.FAILED.value
    request.error_code = code
    request.error_message = message
    request.completed_at = now_utc()


def claim_pending_vm_request(db: Session, vm_request_id: str) -> VMRequest | None:
    """原子地把 VM 申请从 pending 置为 creating(状态转换)。

    用 UPDATE...WHERE status=pending 的 rowcount 判定领取权，保证多个
    worker 并发领取同一申请时只有一个成功；领取失败返回 None 让调用方静默退出。
    """
    result = db.execute(
        update(VMRequest)
        .where(
            VMRequest.id == vm_request_id,
            VMRequest.status == VMRequestStatus.PENDING.value,
        )
        .values(status=VMRequestStatus.CREATING.value)
    )
    if result.rowcount != 1:
        db.rollback()
        return None
    db.flush()
    return db.get(VMRequest, vm_request_id)


def _apply_post_create_kernel(
    db: Session,
    *,
    request: VMRequest,
    resource: Resource,
    actor: User,
    allow_round_fallback: bool = True,
) -> None:
    """VM 创建后内核处理调度：显式换内核(variant/url)优先，否则 -64k 后缀走 64k。

    两条路径互斥：用户选了变体或填了 URL → apply_custom_kernel；否则 os_version
    以 -64k 结尾 → apply_kernel_64k；都没有则不换。失败各自 raise，由调用方
    except 后 _rollback_just_created_vm；-64k 未转测（Kernel64kNotTransferredError）
    保留 VM 由调用方标成功后返回 False。
    """
    if request.kernel_variant or request.kernel_rpm_url:
        apply_custom_kernel(db, request=request, resource=resource, actor=actor)
    elif request.os_version.endswith("-64k"):
        apply_kernel_64k(
            db,
            request=request,
            resource=resource,
            actor=actor,
            allow_round_fallback=allow_round_fallback,
        )


def process_vm_request(
    vm_request_id: str,
    *,
    deadline: datetime | None = None,
    serialize_per_host: bool = False,
    allow_kernel_64k_round_fallback: bool = True,
) -> bool | None:
    """VM 创建的主编排(worker 调用，自带独立 DB 会话)。

    流程：原子领取申请 → 选宿主 → SSH 跑 create-vm.sh → 建资源+租约 →
    64k 后处理。失败按 error_code 决定同宿主重试、换宿主或立即失败
    (见 RETRY_ON_SAME_HOST / NON_RETRYABLE)。

    并发：serialize_per_host=True 时走两阶段锁——先非阻塞试所有宿主，全忙
    才阻塞等第一个宿主(host_create_lock)，避免多任务在同一宿主上争抢。
    超时：deadline 到期时按剩余时间收紧 host 脚本超时，到期即标 task_timeout。
    普通 VM 的 64k 后处理可回退近期 update round；测试流水线只查最新 round。
    最新 round 未转测时保留基础 VM 并返回 False；安装故障回滚刚建的 VM。
    """
    with SessionLocal() as db:
        request = claim_pending_vm_request(db, vm_request_id)
        if request is None:
            return None
        record_vm_request_event(
            db,
            draft=VMRequestEventDraft(
            request=request,
            phase="started",
            message="worker 已领取 VM 创建任务",
            ),
        )
        db.commit()

        actor = db.get(User, request.requester_user_id)
        if actor is None or not actor.is_active:
            fail_request(request, code="requester_unavailable", message="Requester is unavailable")
            record_vm_request_event(
                db,
                draft=VMRequestEventDraft(
                request=request,
                phase="failed",
                message="申请人不可用，VM 创建失败",
                level="error",
                error_code="requester_unavailable",
                ),
            )
            db.commit()
            return None

        hosts = find_vm_hosts(db, arch=request.arch)
        if not hosts:
            fail_request(request, code="capacity_insufficient", message="No VM host is available")
            record_vm_request_event(
                db,
                draft=VMRequestEventDraft(
                request=request,
                phase="failed",
                message="没有可用 VM 宿主",
                level="error",
                error_code="capacity_insufficient",
                ),
            )
            db.commit()
            return None

        def fail_for_task_timeout(host: Resource) -> None:
            fail_request(
                request,
                code="task_timeout",
                message="Test job exceeded its total timeout",
            )
            record_vm_request_event(
                db,
                draft=VMRequestEventDraft(
                request=request,
                phase="failed",
                message="测试任务总超时，停止创建 VM",
                level="error",
                host=host,
                error_code="task_timeout",
                ),
            )
            db.commit()

        # When serialize_per_host: try non-blocking lock on each host first.
        # Busy hosts are skipped; only when ALL are busy do we block on the first.
        all_hosts_busy = serialize_per_host

        for host in hosts:
            lock_fh = None
            if serialize_per_host:
                from app.modules.vms.host_lock import (
                    host_create_lock,
                    release_host_lock,
                    try_host_lock,
                )

                lock_fh = try_host_lock(host.primary_ip)
                if lock_fh is None:
                    continue
                all_hosts_busy = False

            try:
                record_vm_request_event(
                    db,
                    draft=VMRequestEventDraft(
                    request=request,
                    phase="host_selected",
                    message=f"选择宿主 {host.primary_ip}",
                    host=host,
                    ),
                )
                db.commit()
                vm_uuid = str(uuid4())
                vm_name = make_vm_name(request, vm_uuid)
                payload = build_create_payload(request, host, vm_uuid, vm_name)
                max_attempts = 2
                for attempt in range(1, max_attempts + 1):
                    record_vm_request_event(
                        db,
                        draft=VMRequestEventDraft(
                        request=request,
                        phase="host_connecting",
                        message=f"开始连接宿主 {host.primary_ip}，第 {attempt} 次尝试",
                        host=host,
                        ),
                    )
                    db.commit()

                    def record_host_phase(
                        phase: str,
                        message: str,
                        current_host: Resource = host,
                    ) -> None:
                        record_vm_request_event(
                            db,
                            draft=VMRequestEventDraft(
                            request=request,
                            phase=phase,
                            message=message,
                            host=current_host,
                            ),
                        )
                        db.commit()

                    try:
                        timeout_seconds = None
                        if deadline is not None:
                            nd = normalize_datetime(deadline)
                            if nd is None:
                                raise RuntimeError("无法解析租约截止时间") from exc
                            remaining = int((nd - now_utc()).total_seconds())
                            if remaining <= 0:
                                fail_for_task_timeout(host)
                                return None
                            timeout_seconds = remaining
                        result = run_host_script(
                                     options=HostRunOptions(
                                     host_ip=host.primary_ip,
                                     script_name="create-vm.sh",
                                     payload=payload,
                                     result_model=VMHostCreateResult,
                                     event_sink=record_host_phase,
                                     timeout_seconds=timeout_seconds,
                                     ),
                                 )
                        _confirm_created_vm_on_host(
                            host_ip=host.primary_ip, result=result
                        )
                    except HostScriptError as exc:
                        if deadline is not None:
                            nd = normalize_datetime(deadline)
                            if nd is None:
                                raise RuntimeError("无法解析租约截止时间") from exc
                            if nd <= now_utc():
                                fail_for_task_timeout(host)
                                return None
                        failure_phase = (
                            "host_connection_failed"
                            if exc.code
                            in {
                                "host_connection_failed",
                                "timeout",
                                "worker_dependency_missing",
                            }
                            else "host_script_failed"
                        )
                        record_vm_request_event(
                            db,
                            draft=VMRequestEventDraft(
                            request=request,
                            phase=failure_phase,
                            message=str(exc),
                            level="error",
                            host=host,
                            error_code=exc.code,
                            ),
                        )
                        append_attempt(
                            request,
                            draft=VMAttemptUpdate(
                            host=host,
                            attempt=attempt,
                            status="failed",
                            error_code=exc.code,
                            error_message=str(exc),
                            ),
                        )
                        db.commit()
                        if exc.code == "capacity_insufficient":
                            break
                        if exc.code in NON_RETRYABLE:
                            fail_request(request, code=exc.code, message=str(exc))
                            record_vm_request_event(
                                db,
                                draft=VMRequestEventDraft(
                                request=request,
                                phase="failed",
                                message=f"VM 创建失败：{exc}",
                                level="error",
                                error_code=exc.code,
                                ),
                            )
                            db.commit()
                            return None
                        if exc.code not in RETRY_ON_SAME_HOST or attempt >= max_attempts:
                            break
                        continue

                    resource = create_resource_from_vm_result(
                                   db,
                                   draft=VMResourceCreateSpec(
                                   request=request,
                                   host=host,
                                   vm_uuid=vm_uuid,
                                   vm_name=vm_name,
                                   result=result,
                                   ),
                               )
                    create_lease(
                        db,
                        resource=resource,
                        actor=actor,
                        payload=LeaseCreate(
                            purpose=request.purpose,
                            expected_ends_at=request.expected_ends_at,
                        ),
                    )
                    kernel_64k_transferred = True
                    try:
                        _apply_post_create_kernel(
                            db,
                            request=request,
                            resource=resource,
                            actor=actor,
                            allow_round_fallback=allow_kernel_64k_round_fallback,
                        )
                    except Kernel64kNotTransferredError:
                        kernel_64k_transferred = False
                    except Exception as exc:  # noqa: BLE001
                        _rollback_just_created_vm(
                            db,
                            draft=VMRollbackContext(
                            request=request,
                            resource=resource,
                            actor=actor,
                            host=host,
                            error=exc,
                            ),
                        )
                        return None
                    request.status = VMRequestStatus.SUCCEEDED.value
                    request.resource_id = resource.id
                    request.host_resource_id = host.id
                    request.completed_at = now_utc()
                    append_attempt(
                        request,
                        draft=VMAttemptUpdate(
                        host=host,
                        attempt=attempt,
                        status="succeeded",
                        ),
                    )
                    vnc_port = resource.virtual_spec.vnc_port if resource.virtual_spec else "-"
                    success_message = (
                        f"VM 创建成功，IP {resource.primary_ip}"
                        if resource.primary_ip
                        else f"VM 创建成功，VNC {vnc_port}"
                    )
                    record_vm_request_event(
                        db,
                        draft=VMRequestEventDraft(
                        request=request,
                        phase="succeeded",
                        message=success_message,
                        host=host,
                        ),
                    )
                    db.commit()
                    return kernel_64k_transferred
            finally:
                if lock_fh is not None:
                    release_host_lock(lock_fh)

        # All hosts either busy or script-failed.
        if all_hosts_busy:
            # Phase 2: every host was busy — block on the first one.
            first_host = hosts[0]

            def _on_wait(_h: Resource = first_host) -> None:
                request.status = VMRequestStatus.QUEUED.value
                record_vm_request_event(
                    db,
                    draft=VMRequestEventDraft(
                    request=request,
                    phase="queued",
                    message=f"等待宿主 {_h.primary_ip} 完成其他 VM 创建",
                    host=_h,
                    ),
                )
                db.commit()

            with host_create_lock(first_host.primary_ip, on_wait=_on_wait) as waited:
                if waited:
                    request.status = VMRequestStatus.CREATING.value
                    db.commit()
                # Run the same attempt loop on the first host.
                host = first_host
                lock_fh = None  # lock held by context manager, no manual release
                record_vm_request_event(
                    db,
                    draft=VMRequestEventDraft(
                    request=request,
                    phase="host_selected",
                    message=f"选择宿主 {host.primary_ip}",
                    host=host,
                    ),
                )
                db.commit()
                vm_uuid = str(uuid4())
                vm_name = make_vm_name(request, vm_uuid)
                payload = build_create_payload(request, host, vm_uuid, vm_name)
                max_attempts = 2
                for attempt in range(1, max_attempts + 1):
                    record_vm_request_event(
                        db,
                        draft=VMRequestEventDraft(
                        request=request,
                        phase="host_connecting",
                        message=f"开始连接宿主 {host.primary_ip}，第 {attempt} 次尝试",
                        host=host,
                        ),
                    )
                    db.commit()

                    def record_host_phase(  # noqa: B023
                        phase: str,
                        message: str,
                        current_host: Resource = host,
                    ) -> None:
                        record_vm_request_event(
                            db,
                            draft=VMRequestEventDraft(
                            request=request,
                            phase=phase,
                            message=message,
                            host=current_host,
                            ),
                        )
                        db.commit()

                    try:
                        timeout_seconds = None
                        if deadline is not None:
                            nd = normalize_datetime(deadline)
                            if nd is None:
                                raise RuntimeError("无法解析租约截止时间") from exc
                            remaining = int((nd - now_utc()).total_seconds())
                            if remaining <= 0:
                                fail_for_task_timeout(host)
                                return None
                            timeout_seconds = remaining
                        result = run_host_script(
                                     options=HostRunOptions(
                                     host_ip=host.primary_ip,
                                     script_name="create-vm.sh",
                                     payload=payload,
                                     result_model=VMHostCreateResult,
                                     event_sink=record_host_phase,
                                     timeout_seconds=timeout_seconds,
                                     ),
                                 )
                        _confirm_created_vm_on_host(
                            host_ip=host.primary_ip, result=result
                        )
                    except HostScriptError as exc:
                        if deadline is not None:
                            normalized_deadline = normalize_datetime(deadline)
                            if normalized_deadline is None:
                                raise RuntimeError("无法解析租约截止时间") from exc
                            if normalized_deadline <= now_utc():
                                fail_for_task_timeout(host)
                                return None
                        failure_phase = (
                            "host_connection_failed"
                            if exc.code
                            in {
                                "host_connection_failed",
                                "timeout",
                                "worker_dependency_missing",
                            }
                            else "host_script_failed"
                        )
                        record_vm_request_event(
                            db,
                            draft=VMRequestEventDraft(
                            request=request,
                            phase=failure_phase,
                            message=str(exc),
                            level="error",
                            host=host,
                            error_code=exc.code,
                            ),
                        )
                        append_attempt(
                            request,
                            draft=VMAttemptUpdate(
                            host=host,
                            attempt=attempt,
                            status="failed",
                            error_code=exc.code,
                            error_message=str(exc),
                            ),
                        )
                        db.commit()
                        if exc.code == "capacity_insufficient":
                            break
                        if exc.code in NON_RETRYABLE:
                            fail_request(request, code=exc.code, message=str(exc))
                            record_vm_request_event(
                                db,
                                draft=VMRequestEventDraft(
                                request=request,
                                phase="failed",
                                message=f"VM 创建失败：{exc}",
                                level="error",
                                error_code=exc.code,
                                ),
                            )
                            db.commit()
                            return None
                        if exc.code not in RETRY_ON_SAME_HOST or attempt >= max_attempts:
                            break
                        continue

                    resource = create_resource_from_vm_result(
                                   db,
                                   draft=VMResourceCreateSpec(
                                   request=request,
                                   host=host,
                                   vm_uuid=vm_uuid,
                                   vm_name=vm_name,
                                   result=result,
                                   ),
                               )
                    create_lease(
                        db,
                        resource=resource,
                        actor=actor,
                        payload=LeaseCreate(
                            purpose=request.purpose,
                            expected_ends_at=request.expected_ends_at,
                        ),
                    )
                    kernel_64k_transferred = True
                    try:
                        _apply_post_create_kernel(
                            db,
                            request=request,
                            resource=resource,
                            actor=actor,
                            allow_round_fallback=allow_kernel_64k_round_fallback,
                        )
                    except Kernel64kNotTransferredError:
                        kernel_64k_transferred = False
                    except Exception as exc:  # noqa: BLE001
                        _rollback_just_created_vm(
                            db,
                            draft=VMRollbackContext(
                            request=request,
                            resource=resource,
                            actor=actor,
                            host=host,
                            error=exc,
                            ),
                        )
                        return None
                    request.status = VMRequestStatus.SUCCEEDED.value
                    request.resource_id = resource.id
                    request.host_resource_id = host.id
                    request.completed_at = now_utc()
                    append_attempt(
                        request,
                        draft=VMAttemptUpdate(
                        host=host,
                        attempt=attempt,
                        status="succeeded",
                        ),
                    )
                    vnc_port = resource.virtual_spec.vnc_port if resource.virtual_spec else "-"
                    success_message = (
                        f"VM 创建成功，IP {resource.primary_ip}"
                        if resource.primary_ip
                        else f"VM 创建成功，VNC {vnc_port}"
                    )
                    record_vm_request_event(
                        db,
                        draft=VMRequestEventDraft(
                        request=request,
                        phase="succeeded",
                        message=success_message,
                        host=host,
                        ),
                    )
                    db.commit()
                    return kernel_64k_transferred

        fail_request(request, code="vm_create_failed", message="All VM hosts failed")
        record_vm_request_event(
            db,
            draft=VMRequestEventDraft(
            request=request,
            phase="failed",
            message="所有候选宿主创建失败",
            level="error",
            error_code="vm_create_failed",
            ),
        )
        db.commit()


def ensure_vm_release_allowed(db: Session, *, resource: Resource, actor: User) -> tuple[bool, str]:
    """VM 释放的鉴权边界。返回 (force, lease_id)。

    本人释放 force=False；ADMIN 可释放任意 VM force=True；TSE 可释放 TE 的
    VM force=True；其余拒绝。无有效租约则抛 VMConflictError。
    """
    lease = get_resource_active_lease(db, resource)
    if lease is None:
        raise VMConflictError("VM has no active lease")
    if lease.user_id == actor.id:
        return False, lease.id
    lease_user = db.get(User, lease.user_id)
    if actor.role == UserRole.ADMIN.value:
        return True, lease.id
    if actor.role == UserRole.TSE.value and lease_user and lease_user.role == UserRole.TE.value:
        return True, lease.id
    raise VMPolicyError("Actor cannot release this VM")


def ensure_vm_ip_refresh_allowed(db: Session, *, resource: Resource, actor: User) -> None:
    """IP 刷新鉴权：ADMIN 或当前占用者可刷新，否则拒绝。"""
    if actor.role == UserRole.ADMIN.value:
        return
    lease = get_resource_active_lease(db, resource)
    if lease is not None and lease.user_id == actor.id:
        return
    raise VMPolicyError("Actor cannot refresh this VM IP")


def ensure_vm_console_allowed(db: Session, *, resource: Resource, actor: User) -> None:
    """
    控制台鉴权(最终边界，前端可见性只用于体验)：ADMIN 或当前占用者可开
    控制台，否则拒绝。电源操作复用同一鉴权。
    """
    if actor.role == UserRole.ADMIN.value:
        return
    lease = get_resource_active_lease(db, resource)
    if lease is not None and lease.user_id == actor.id:
        return
    raise VMPolicyError("Actor cannot open this VM console")


def get_vm_host_and_name(db: Session, resource: Resource) -> tuple[Resource, str]:
    spec = resource.virtual_spec
    if spec is None or not spec.host_resource_id:
        raise VMConflictError("VM host is not configured")
    vm_name = spec.vm_name or resource.name or resource.resource_code
    if not vm_name:
        raise VMConflictError("VM name is not configured")

    host = db.get(Resource, spec.host_resource_id)
    if host is None or not host.primary_ip:
        raise VMConflictError("VM host IP is not configured")
    return host, vm_name


def get_vm_console_config(
    db: Session,
    *,
    resource: Resource,
    actor: User,
) -> VMConsoleRead:
    ensure_vm_console_allowed(db, resource=resource, actor=actor)
    spec = resource.virtual_spec
    if spec is None or not spec.host_resource_id:
        raise VMConflictError("VM host is not configured")
    if not spec.vnc_websocket_port:
        raise VMConflictError("VM web console is not configured")

    host = db.get(Resource, spec.host_resource_id)
    if host is None or not host.primary_ip:
        raise VMConflictError("VM host IP is not configured")

    return VMConsoleRead(
        resource_id=resource.id,
        vm_name=spec.vm_name,
        url=f"ws://{host.primary_ip}:{spec.vnc_websocket_port}/",
        port=spec.vnc_port,
        websocket_port=spec.vnc_websocket_port,
        password=None,
    )


def run_vm_power_host_script(
    db: Session,
    *,
    resource: Resource,
    actor: User,
    action: str,
) -> tuple[VMHostPowerResult, Resource, str]:
    ensure_vm_console_allowed(db, resource=resource, actor=actor)
    host, vm_name = get_vm_host_and_name(db, resource)

    try:
        result = run_host_script(
                     options=HostRunOptions(
                     host_ip=host.primary_ip,
                     script_name="power-vm.sh",
                     payload=VMHostPowerPayload(vm_name=vm_name, action=action),
                     result_model=VMHostPowerResult,
                     ),
                 )
    except HostScriptError as exc:
        raise VMConflictError(str(exc)) from exc
    return result, host, vm_name


def get_vm_power_state(db: Session, *, resource: Resource, actor: User) -> VMPowerRead:
    result, _host, vm_name = run_vm_power_host_script(
        db,
        resource=resource,
        actor=actor,
        action="state",
    )
    return VMPowerRead(resource_id=resource.id, vm_name=vm_name, power_state=result.power_state)


def operate_vm_power(
    db: Session,
    *,
    resource: Resource,
    actor: User,
    action: str,
) -> VMPowerRead:
    result, host, vm_name = run_vm_power_host_script(
        db,
        resource=resource,
        actor=actor,
        action=action,
    )
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action=f"vm.power.{action}",
        target_type="resource",
        target_id=resource.id,
        detail={
            "resource_code": resource.resource_code,
            "vm_name": vm_name,
            "host_resource_id": host.id,
            "host_ip": host.primary_ip,
            "power_state": result.power_state,
        },
    )
    db.flush()
    return VMPowerRead(resource_id=resource.id, vm_name=vm_name, power_state=result.power_state)


def refresh_vm_primary_ip(db: Session, *, resource: Resource, actor: User) -> ResourceRead:
    ensure_vm_ip_refresh_allowed(db, resource=resource, actor=actor)
    if not resource.mac_address:
        raise VMConflictError("VM has no MAC address")

    leases_text = fetch_dhcp_leases(get_settings().vm_dhcp_leases_url)
    new_ip = parse_latest_dhcp_lease_ip(leases_text, resource.mac_address)
    if not new_ip:
        raise VMDhcpLeaseNotFoundError("No DHCP lease found for VM MAC address")

    old_ip = resource.primary_ip
    if old_ip != new_ip:
        resource.primary_ip = new_ip
        record_audit_log(
            db,
            actor_user_id=actor.id,
            action="vm.refresh_ip",
            target_type="resource",
            target_id=resource.id,
            detail={
                "resource_code": resource.resource_code,
                "mac_address": resource.mac_address,
                "old_primary_ip": old_ip,
                "new_primary_ip": new_ip,
            },
        )
        db.flush()
    return serialize_resource(db, resource)


def request_vm_release(
    db: Session,
    *,
    resource: Resource,
    actor: User,
    reason: str | None,
) -> None:
    """入队 VM 销毁任务(异步)。

    幂等防重：先对资源行加锁，再查 execution_state——已有销毁任务在队则
    抛 VMConflictError，避免重复入队。鉴权通过后投递 Celery 任务并把
    task_id 记到 resource.extra(mark_vm_destroy_queued)。
    """
    locked_resource = db.execute(
        select(Resource).where(Resource.id == resource.id).with_for_update()
    ).scalar_one()
    if get_vm_destroy_execution(locked_resource) is not None:
        raise VMConflictError("VM destroy is already queued")

    force, lease_id = ensure_vm_release_allowed(
        db,
        resource=locked_resource,
        actor=actor,
    )
    task_id = enqueue_vm_destroy(
        resource_id=locked_resource.id,
        lease_id=lease_id,
        actor_user_id=actor.id,
        reason=reason,
        force=force,
    )
    mark_vm_destroy_queued(locked_resource, task_id=task_id, enqueued_at=now_utc())
    record_vm_destroy_event(
        db,
        draft=VMDestroyEventDraft(
        resource=locked_resource,
        phase="queued",
        message="VM 销毁任务已进入异步队列",
        celery_task_id=task_id,
        ),
    )


def batch_release_vms(
    db: Session,
    *,
    resource_ids: list[str],
    actor: User,
    reason: str | None,
) -> dict[str, list[str]]:
    """批量释放 VM：循环 request_vm_release，单个失败（无权/无 lease/不存在）归 failed 不阻塞。"""
    from app.modules.resources.service import get_resource

    destroyed: list[str] = []
    failed: list[str] = []
    seen: set[str] = set()
    for rid in resource_ids:
        if rid in seen:
            continue
        seen.add(rid)
        resource = get_resource(db, rid)
        if resource is None or resource.resource_type != ResourceType.VIRTUAL.value:
            failed.append(rid)
            continue
        try:
            request_vm_release(db, resource=resource, actor=actor, reason=reason)
            destroyed.append(rid)
        except (VMPolicyError, VMConflictError, VMQueueUnavailableError):
            failed.append(rid)
    return {"destroyed": destroyed, "failed": failed}


def install_kernel_64k_via_ssh(
    db: Session,
    *,
    os_version: str,
    resource: Resource,
    record_event: InstallKernel64kEventSink,
    allow_round_fallback: bool = True,
) -> None:
    """安装并验证 64k 内核；普通申请可回退，update 流水线只检查最新轮。

    record_event 签名：``(phase, message, *, level="info", error_code=None) -> None``，
    由调用方包成 VM/物理机各自的事件记录器（含 commit）。
    """
    if not os_version.endswith("-64k"):
        return
    validate_kernel_64k_target(
        os_version=os_version,
        arch=getattr(resource, "arch", None) or "aarch64",
    )

    record_event(
        "kernel_64k_install_start",
        f"开始安装 64k 内核 ({resource.primary_ip})",
    )

    from app.core.credentials import decrypt_secret
    from app.modules.pipelines.repodata import list_update_dirs
    from app.modules.test_management.remote import RemoteRunOptions, RemoteTarget, run_ssh_command, write_remote_file

    settings = get_settings()
    base_version = os_version[: -len("-64k")]
    rounds = list_update_dirs(
        repo_base_url=settings.vm_openeuler_update_repo_root,
        version=base_version,
    )[: 5 if allow_round_fallback else 1]

    password = (
        decrypt_secret(resource.ssh_password_ciphertext)
        if resource.ssh_password_ciphertext
        else settings.vm_default_ssh_password
    )
    username = resource.ssh_username or "root"
    ssh_target = RemoteTarget(host=resource.primary_ip or "", username=username, password=password)

    repo_base = settings.vm_openeuler_update_repo_root.rstrip("/")

    for round_label in rounds:
        repo_file = (
            f"[openEuler_update_{round_label}]\n"
            f"name=openEuler update {round_label}\n"
            f"baseurl={repo_base}/{base_version}/{round_label}/$basearch/\n"
            "enabled=1\ngpgcheck=0\n"
        )
        write_remote_file(
            path=f"/etc/yum.repos.d/openEuler-update-{round_label}.repo",
            content=repo_file,
            timeout_seconds=30,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        query = run_ssh_command(
            command=f"dnf repoquery --repo=openEuler_update_{round_label} kernel-64k",
            timeout_seconds=120,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        if query.returncode != 0:
            record_event(
                "kernel_64k_install_failed",
                f"查询 {round_label} 的 kernel-64k 失败：{(query.stderr or '').strip()[:200]}",
                level="error",
                error_code="kernel_64k_repo_query_failed",
            )
            raise Kernel64kInstallError(f"kernel-64k repoquery failed for {round_label}")
        found = bool((query.stdout or "").strip())
        # 最新轮（rounds[0]）记一条"本周转测检查"日志（找到/未找到都记），旧轮回退不记。
        if round_label == rounds[0]:
            from app.modules.pipelines.repodata import round_label_to_date

            record_event(
                "kernel_64k_repo_check",
                f"检查了 {round_label_to_date(round_label)} 的 repo，"
                f"{'找到' if found else '未找到'} 64k kernel",
            )
        if not found:
            continue

        install = run_ssh_command(
            command=(
                "echo 'skip_if_unavailable=True' >> /etc/dnf/dnf.conf && dnf install -y kernel-64k"
            ),
            timeout_seconds=300,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        if install.returncode != 0:
            record_event(
                "kernel_64k_install_failed",
                f"安装 kernel-64k 失败：{(install.stderr or '').strip()[:200]}",
                level="error",
                error_code="kernel_64k_dnf_install_failed",
            )
            raise Kernel64kInstallError(f"kernel-64k install failed for {round_label}")

        set_default = run_ssh_command(
            command=(
                "kernel=$(rpm -q --qf '%{VERSION}-%{RELEASE}.%{ARCH}\\n' kernel-64k "
                "| sort -V | tail -n1); "
                "entry=$(grep '^menuentry' /etc/grub2-efi.cfg | grep -F \"$kernel\" "
                "| sed -n \"s/^menuentry '\\([^']*\\)'.*/\\1/p\" | head -n1); "
                'test -n "$entry" && grub2-set-default "$entry"'
            ),
            timeout_seconds=30,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        if set_default.returncode != 0:
            record_event(
                "kernel_64k_install_failed",
                "无法把 kernel-64k 设置为默认启动内核",
                level="error",
                error_code="kernel_64k_set_default_failed",
            )
            raise Kernel64kInstallError(f"cannot set kernel-64k default for {round_label}")

        run_ssh_command(
            command="reboot",
            timeout_seconds=30,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        # Wait for SSH to go down (reboot started), then come back (reboot done).
        # Without this, the caller may try SSH before the VM has finished rebooting.
        down_deadline = time.monotonic() + 60
        ssh_went_down = False
        # Phase 1: wait for SSH to become unreachable.
        while time.monotonic() < down_deadline:
            try:
                r = run_ssh_command(
                    command="echo ok",
                    timeout_seconds=10,
                    options=RemoteRunOptions(verify_host_key=False),
                    target=ssh_target,
                )
                if r.returncode != 0:
                    ssh_went_down = True
                    break
            except Exception:  # noqa: BLE001
                ssh_went_down = True
                break
            time.sleep(2)
        if not ssh_went_down:
            record_event(
                "kernel_64k_install_failed",
                "重启后 SSH 未在 60 秒内下线",
                level="error",
                error_code="kernel_64k_ssh_not_down",
            )
            raise Kernel64kInstallError(
                f"SSH did not go down after kernel-64k reboot for {round_label}"
            )
        # Phase 2: wait for SSH to come back.
        up_deadline = time.monotonic() + 300
        ssh_back = False
        while time.monotonic() < up_deadline:
            try:
                r = run_ssh_command(
                    command="echo ok",
                    timeout_seconds=10,
                    options=RemoteRunOptions(verify_host_key=False),
                    target=ssh_target,
                )
                if r.returncode == 0:
                    ssh_back = True
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5)
        if not ssh_back:
            record_event(
                "kernel_64k_install_failed",
                "重启后 SSH 未恢复",
                level="error",
                error_code="kernel_64k_ssh_not_back",
            )
            raise Kernel64kInstallError(f"SSH not back after kernel-64k reboot for {round_label}")

        page_size = run_ssh_command(
            command="getconf PAGESIZE",
            timeout_seconds=10,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        if page_size.returncode != 0 or (page_size.stdout or "").strip() != "65536":
            record_event(
                "kernel_64k_install_failed",
                f"重启后页大小不是 65536：{(page_size.stdout or '').strip() or 'unknown'}",
                level="error",
                error_code="kernel_64k_page_size_mismatch",
            )
            raise Kernel64kInstallError(f"page size is not 65536 for {round_label}")

        uname = run_ssh_command(
            command="uname -r",
            timeout_seconds=10,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        if uname.returncode != 0 or not (uname.stdout or "").strip():
            record_event(
                "kernel_64k_install_failed",
                "读取 64k 内核版本失败",
                level="error",
                error_code="kernel_64k_uname_failed",
            )
            raise Kernel64kInstallError(f"uname failed after kernel-64k reboot for {round_label}")

        resource.os_version = canonical_kernel_64k_os_version(os_version)
        resource.kernel_version = (uname.stdout or "").strip()
        record_event(
            "kernel_64k_installed",
            f"kernel {resource.kernel_version} from {round_label}，页大小 65536",
        )
        return

    if not allow_round_fallback:
        record_event(
            "kernel_64k_not_transferred",
            "最新 update repo 未转测 kernel-64k",
            level="warning",
        )
        raise Kernel64kNotTransferredError(
            f"kernel-64k is not transferred in latest update round for {base_version}"
        )

    record_event(
        "kernel_64k_not_found",
        "所有 update repo 轮次均无 kernel-64k",
        level="error",
        error_code="kernel_64k_not_found",
    )
    raise Kernel64kNotFoundError(f"no kernel-64k in any update round for {base_version}")


def install_latest_kernel_via_ssh(
    *,
    os_version: str,
    resource: Resource,
    record_event: KernelInstallEventSink,
) -> None:
    """kernel 模块物理机：装 update 仓最新 4k kernel + reboot + 等 SSH 回来 + uname 写真实内核。

    os_version 不含 -64k（调用方 ``create_env_node_physical`` 已 gate）。失败 raise
    LatestKernelInstallError，由调用方标 ``management_status=DISABLED`` + node ERROR。

    record_event 签名：``(phase, message, *, level="info", error_code=None) -> None``。
    成功设 ``resource.kernel_version`` 为 ``uname -r`` 输出；记 ``kernel_latest_installed``。
    4k ``kernel`` 每轮都有，不像 64k 需枚举多轮 repoquery，直接取 ``rounds[0]`` 写 repo 即可。
    """
    from app.core.credentials import decrypt_secret
    from app.modules.pipelines.repodata import list_update_dirs, round_label_to_date
    from app.modules.test_management.remote import RemoteRunOptions, RemoteTarget, run_ssh_command, write_remote_file

    settings = get_settings()
    rounds = list_update_dirs(
        repo_base_url=settings.vm_openeuler_update_repo_root, version=os_version
    )
    if not rounds:
        record_event(
            "kernel_latest_install_failed",
            "无 update repo 轮次",
            level="error",
            error_code="kernel_latest_no_rounds",
        )
        raise LatestKernelInstallError(f"no update rounds for {os_version}")

    round_label = rounds[0]
    password = (
        decrypt_secret(resource.ssh_password_ciphertext)
        if resource.ssh_password_ciphertext
        else settings.vm_default_ssh_password
    )
    username = resource.ssh_username or "root"
    ssh_target = RemoteTarget(host=resource.primary_ip or "", username=username, password=password)

    repo_base = settings.vm_openeuler_update_repo_root.rstrip("/")
    repo_file = (
        f"[openEuler_update_{round_label}]\n"
        f"name=openEuler update {round_label}\n"
        f"baseurl={repo_base}/{os_version}/{round_label}/$basearch/\n"
        "enabled=1\ngpgcheck=0\n"
    )
    write_remote_file(
        path=f"/etc/yum.repos.d/openEuler-update-{round_label}.repo",
        content=repo_file,
        timeout_seconds=30,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )

    install = run_ssh_command(
        command="echo 'skip_if_unavailable=True' >> /etc/dnf/dnf.conf && dnf install -y kernel",
        timeout_seconds=300,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )
    if install.returncode != 0:
        record_event(
            "kernel_latest_install_failed",
            f"dnf install kernel 失败：{(install.stderr or '').strip()[:200]}",
            level="error",
            error_code="kernel_latest_dnf_install_failed",
        )
        raise LatestKernelInstallError(f"dnf install kernel failed for {os_version}")

    run_ssh_command(
        command="reboot",
        timeout_seconds=30,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )

    # 等 SSH：phase1 等下线（确认 reboot 生效，~60s），phase2 等回来（物理机 BIOS+
    # 内核+sshd，~300s）。两段独立 deadline——不共用一个 120s（太紧会把慢重启误判为
    # 失败 → 误 DISABLED），也避免 poll-for-UP 在 reboot 生效前读到旧内核。
    down_deadline = time.monotonic() + 60
    while time.monotonic() < down_deadline:
        try:
            r = run_ssh_command(
                command="echo ok",
                timeout_seconds=10,
                options=RemoteRunOptions(verify_host_key=False),
                target=ssh_target,
            )
            if r.returncode != 0:
                break
        except Exception:  # noqa: BLE001
            break
        time.sleep(2)
    up_deadline = time.monotonic() + 300
    ssh_back = False
    while time.monotonic() < up_deadline:
        try:
            r = run_ssh_command(
                command="echo ok",
                timeout_seconds=10,
                options=RemoteRunOptions(verify_host_key=False),
                target=ssh_target,
            )
            if r.returncode == 0:
                ssh_back = True
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(5)
    if not ssh_back:
        record_event(
            "kernel_latest_install_failed",
            "reboot 后 SSH 未恢复",
            level="error",
            error_code="kernel_latest_ssh_not_back",
        )
        raise LatestKernelInstallError(f"SSH not back after reboot for {os_version}")

    uname = run_ssh_command(
        command="uname -r",
        timeout_seconds=10,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )
    if uname.returncode != 0 or not (uname.stdout or "").strip():
        record_event(
            "kernel_latest_install_failed",
            "uname -r 失败",
            level="error",
            error_code="kernel_latest_uname_failed",
        )
        raise LatestKernelInstallError(f"uname -r failed for {os_version}")

    resource.kernel_version = (uname.stdout or "").strip()
    record_event(
        "kernel_latest_installed",
        f"kernel {resource.kernel_version} from {round_label}"
        f"（{round_label_to_date(round_label)}）",
    )


def apply_kernel_64k(
    db: Session,
    *,
    request: VMRequest,
    resource: Resource,
    actor: User,
    allow_round_fallback: bool = True,
) -> None:
    """VM 64k 后处理入口（VMRequest 事件）：委托 install_kernel_64k_via_ssh。

    是否回退近期 update round 由调用方决定。未转测抛出
    Kernel64kNotTransferredError；安装或查询故障由 process_vm_request 回滚。
    """

    def record_event(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        record_vm_request_event(
            db,
            draft=VMRequestEventDraft(
            request=request,
            phase=phase,
            message=message,
            level=level,
            error_code=error_code,
            ),
        )
        db.commit()

    install_kernel_64k_via_ssh(
        db,
        os_version=request.os_version,
        resource=resource,
        record_event=record_event,
        allow_round_fallback=allow_round_fallback,
    )


@dataclass(frozen=True)
class VMRollbackContext:
    """VM 创建失败回滚上下文。"""

    request: VMRequest
    resource: Resource
    actor: User
    host: Resource | None
    error: Exception


def _rollback_just_created_vm(
    db: Session,
    *,
    draft: VMRollbackContext,
) -> None:
    request = draft.request
    resource = draft.resource
    actor = draft.actor
    host = draft.host
    error = draft.error
    """换内核全失败回滚：跑 destroy-vm.sh + 释放租约 + 软删 resource + fail_request。

    按实际异常类型冒泡真实错误码/信息（custom-kernel repo 不可达不再被误报成
    kernel-64k not found）。复用 process_vm_destroy 的 destroy-vm.sh 调用与租约释放
    语义，但不记 destroy 事件流（回滚属 VM 请求失败，事件由 apply_* 记）。
    由 process_vm_request 在捕获 Kernel64kNotFoundError/CustomKernelError 后调用。
    """
    if isinstance(error, CustomKernelError):
        err_code, err_message = error.code, str(error)
    elif isinstance(error, Kernel64kNotFoundError):
        err_code, err_message = "kernel_64k_not_found", str(error)
    elif isinstance(error, UnsupportedKernel64kVersionError):
        err_code, err_message = "kernel_64k_unsupported", str(error)
    elif isinstance(error, Kernel64kInstallError):
        err_code, err_message = "kernel_64k_install_failed", str(error)
    else:
        err_code, err_message = "kernel_swap_failed", str(error)
    spec = resource.virtual_spec
    if host is not None and spec is not None:
        try:
            run_host_script(
                options=HostRunOptions(
                host_ip=host.primary_ip,
                script_name="destroy-vm.sh",
                payload=VMHostDestroyPayload(
                    vm_name=spec.vm_name or resource.name or resource.resource_code,
                    system_disk_path=spec.system_disk_path,
                    data_disk_paths=spec.data_disk_paths,
                ),
                result_model=VMHostDestroyResult,
                ),
            )
        except HostScriptError as exc:
            # destroy-vm.sh 失败不阻塞回滚：仍释放租约 + 软删 + fail_request，
            # 避免请求卡在 creating。leaked libvirt 域交由运维后续清理。
            record_vm_request_event(
                db,
                draft=VMRequestEventDraft(
                request=request,
                phase="kernel_64k_rollback_destroy_failed",
                message=f"回滚销毁 VM 失败（请求仍标失败）: {exc}",
                level="warning",
                error_code="rollback_destroy_failed",
                ),
            )
            db.commit()

    lease = get_resource_active_lease(db, resource)
    if lease is not None:
        release_lease(
            db,
            lease=lease,
            actor=actor,
            payload=LeaseReleaseNormalized(reason=f"kernel swap failed ({err_code}), rollback"),
            force=True,
            allow_virtual=True,
        )
    resource.deleted_at = now_utc()
    resource.current_lease_id = None
    resource.occupancy_status = OccupancyStatus.IDLE.value
    fail_request(
        request,
        code=err_code,
        message=err_message,
    )
    db.commit()



class CustomKernelError(Exception):
    """换内核失败：repo 不可达/包不存在/install 失败/uname 不匹配。

    回滚由 process_vm_request 在 except 中调 _rollback_just_created_vm。
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def apply_custom_kernel(
    db: Session,
    *,
    request: VMRequest,
    resource: Resource,
    actor: User,
) -> None:
    """VM 自定义内核后处理入口：委托 install_custom_kernel_via_ssh。

    失败 raise CustomKernelError；回滚（销毁 VM + fail_request）由
    process_vm_request 在 except 中调 _rollback_just_created_vm。
    """

    def record_event(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        record_vm_request_event(
            db,
            draft=VMRequestEventDraft(
            request=request,
            phase=phase,
            message=message,
            level=level,
            error_code=error_code,
            ),
        )
        db.commit()

    install_custom_kernel_via_ssh(
        db, request=request, resource=resource, record_event=record_event
    )


class CustomKernelSwapRequest(Protocol):
    """换内核所需的请求子集（VMRequest 与物理机 DTO 都满足）。"""

    os_version: str
    image_round: str | None
    kernel_variant: str | None
    kernel_rpm_url: str | None
    arch: str


def install_custom_kernel_via_ssh(
    db: Session,
    *,
    request: CustomKernelSwapRequest,
    resource: Resource,
    record_event: Callable[..., None],
) -> None:
    """换内核：推断 repo baseurl + 写 [local-kernel] repo + repoquery 找精确 NVR +
    dnf install kernel-<NVR> + reboot + 等 SSH + uname -r 比对新内核生效。

    变体路径：从 request.kernel_variant 解析版本前缀（with-kernel-6.18 → 6.18），
    拼 dailybuild repo baseurl，repoquery 找精确 NVR。URL 路径：从
    request.kernel_rpm_url 推断同目录 repo baseurl + 从文件名解析 NVR（跳过 repoquery）。

    成功：resource.kernel_version = uname -r 真实值；record_event kernel_custom_installed。
    失败：record_event 对应 phase + raise CustomKernelError。
    """
    from app.core.credentials import decrypt_secret
    from app.modules.test_management.remote import RemoteRunOptions, RemoteTarget, run_ssh_command, write_remote_file

    settings = get_settings()
    password = (
        decrypt_secret(resource.ssh_password_ciphertext)
        if resource.ssh_password_ciphertext
        else settings.vm_default_ssh_password
    )
    username = resource.ssh_username or "root"
    ssh_target = RemoteTarget(host=resource.primary_ip or "", username=username, password=password)

    # 推断 repo baseurl + NVR（变体路径 / URL 路径）
    if request.kernel_rpm_url:
        # URL 路径：从 RPM URL 推断同目录 repo baseurl + 从文件名解析 NVR
        repo_baseurl = request.kernel_rpm_url.rsplit("/Packages/", 1)[0] + "/"
        rpm_name = request.kernel_rpm_url.rsplit("/", 1)[-1].removesuffix(".rpm")
        nvr = rpm_name.rsplit(".", 1)[0]  # kernel-6.18.40-0.0.0.14.oe2609
    else:
        # 变体路径：从 kernel_variant 解析版本前缀，拼 dailybuild repo baseurl
        dailybuild_root = settings.vm_dailybuild_repo_root.rstrip("/")
        repo_baseurl = (
            f"{dailybuild_root}/EBS-{request.os_version}/{request.image_round}/"
            f"{request.kernel_variant}/everything/{request.arch}/"
        )
        kver_prefix = request.kernel_variant.split("with-kernel-")[-1]

    repo_file = (
        "[local-kernel]\n"
        "name=local kernel repo\n"
        f"baseurl={repo_baseurl}\n"
        "enabled=1\ngpgcheck=0\n"
    )
    write_remote_file(
        path="/etc/yum.repos.d/local-kernel.repo",
        content=repo_file,
        timeout_seconds=30,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )
    # 变体路径 repoquery 找精确 NVR（URL 路径 NVR 已从文件名解析，跳过）
    if not request.kernel_rpm_url:
        query = run_ssh_command(
            command=(
                "dnf repoquery --repo=local-kernel "
                f"'kernel-{kver_prefix}.*' "
                "--queryformat='%{name}-%{version}-%{release}.%{arch}'"
            ),
            timeout_seconds=120,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        if query.returncode != 0:
            record_event(
                "kernel_custom_repo_unreachable",
                f"repoquery 失败，repo {repo_baseurl} 不可达",
                level="error",
                error_code="kernel_custom_repo_unreachable",
            )
            raise CustomKernelError(
                "kernel_custom_repo_unreachable",
                f"repoquery failed for {repo_baseurl}",
            )
        query_lines = (query.stdout or "").strip().splitlines()
        if not query_lines:
            record_event(
                "kernel_custom_not_found",
                f"repo {repo_baseurl} 无 kernel-{kver_prefix}.* 包",
                level="error",
                error_code="kernel_custom_not_found",
            )
            raise CustomKernelError(
                "kernel_custom_not_found",
                f"no kernel-{kver_prefix}.* in {repo_baseurl}",
            )
        nvr = query_lines[0].rsplit(".", 1)[0]  # kernel-6.18.40-0.0.0.14.oe2609
    install = run_ssh_command(
        # 仅用 local-kernel 源解析，规避目标系统默认 OS 源损坏/不可达导致事务失败
        # （如 DevStation 26.09 默认 openEuler 镜像 404）。
        command=f"dnf install -y --disablerepo='*' --enablerepo=local-kernel {nvr}",
        timeout_seconds=300,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )
    if install.returncode != 0:
        record_event(
            "kernel_custom_install_failed",
            f"dnf install {nvr} 失败：{(install.stderr or '').strip()[:200]}",
            level="error",
            error_code="kernel_custom_install_failed",
        )
        raise CustomKernelError(
            "kernel_custom_install_failed",
            f"dnf install {nvr} failed",
        )
    # 部分机器换内核后（如 x86 的 6.18）网卡不会自动跑 DHCP → 开机一次性 dhclient
    # 兜底（仅对无 IPv4 的 e* 网卡执行，避免与正常网络管理冲突）；try/finally 摘除。
    write_remote_file(
        path="/usr/local/sbin/kronos-dhclient.sh",
        content=(
            "#!/usr/bin/env bash\n"
            "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
            "for i in /sys/class/net/e*; do\n"
            "  [ -d \"$i\" ] || continue\n"
            "  b=\"$(basename \"$i\")\"\n"
            "  [ -n \"$(ip -4 -o addr show \"$b\" 2>/dev/null)\" ] && continue\n"
            # dhclient -1: 拿到租约即退出，oneshot 正常完成不被 systemd timeout 杀掉
            "  dhclient -1 -v -pf \"/run/dhclient-$b.pid\" \"$b\" || true\n"
            "done\n"
        ),
        timeout_seconds=30,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )
    write_remote_file(
        path="/etc/systemd/system/kronos-manual-dhclient.service",
        content=(
            "[Unit]\n"
            "Description=radiaTest manual dhclient after kernel swap\n"
            "Wants=network-online.target\n"
            "After=network-online.target\n\n"
            "[Service]\n"
            "Type=oneshot\n"
            "ExecStart=/usr/local/sbin/kronos-dhclient.sh\n"
            "TimeoutStartSec=90\n\n"
            "[Install]\n"
            "WantedBy=multi-user.target\n"
        ),
        target=ssh_target,
    )
    run_ssh_command(
        command=(
            "chmod +x /usr/local/sbin/kronos-dhclient.sh && "
            "systemctl daemon-reload && "
            "systemctl enable kronos-manual-dhclient.service"
        ),
        timeout_seconds=30,
        options=RemoteRunOptions(verify_host_key=False),
        target=ssh_target,
    )
    try:
        run_ssh_command(
            command="reboot",
            timeout_seconds=30,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        # 等 SSH down（reboot 开始）再 up（reboot 完成），避免后续命令打在重启中

        reboot_deadline = time.monotonic() + 420
        while time.monotonic() < reboot_deadline:
            try:
                r = run_ssh_command(
                    command="echo ok",
                    timeout_seconds=10,
                    options=RemoteRunOptions(verify_host_key=False),
                    target=ssh_target,
                )
                if r.returncode != 0:
                    break
            except Exception:  # noqa: BLE001
                break
            time.sleep(2)
        while time.monotonic() < reboot_deadline:
            try:
                r = run_ssh_command(
                    command="echo ok",
                    timeout_seconds=10,
                    options=RemoteRunOptions(verify_host_key=False),
                    target=ssh_target,
                )
                if r.returncode == 0:
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5)
        # uname -r 判定新内核生效
        uname = run_ssh_command(
            command="uname -r",
            timeout_seconds=30,
            options=RemoteRunOptions(verify_host_key=False),
            target=ssh_target,
        )
        uname_version = (uname.stdout or "").strip()
        expected_version_rel = nvr.split("-", 1)[1]  # 6.18.40-0.0.0.14.oe2609
        if expected_version_rel not in uname_version:
            record_event(
                "kernel_custom_boot_mismatch",
                f"uname -r={uname_version} 期望含 {expected_version_rel}",
                level="error",
                error_code="kernel_custom_boot_mismatch",
            )
            raise CustomKernelError(
                "kernel_custom_boot_mismatch",
                f"uname -r {uname_version} != expected {expected_version_rel}",
            )
        resource.kernel_version = uname_version
        source = request.kernel_rpm_url or request.kernel_variant
        record_event(
            "kernel_custom_installed",
            f"{source} → {uname_version}",
        )
    finally:
        # 摘除开机 dhclient 兜底（成功或失败都清理，避免残留影响后续网络管理）
        try:
            run_ssh_command(
                command=(
                    "systemctl disable kronos-manual-dhclient.service 2>/dev/null; "
                    "rm -f /etc/systemd/system/kronos-manual-dhclient.service "
                    "/usr/local/sbin/kronos-dhclient.sh; systemctl daemon-reload"
                ),
                timeout_seconds=30,
                options=RemoteRunOptions(verify_host_key=False),
                target=ssh_target,
            )
        except Exception:  # noqa: BLE001
            pass


def _inspect_vm_host_state(
    *,
    host_ip: str,
    vm_name: str,
    system_disk_path: str | None,
    data_disk_paths: list[str],
) -> VMHostInspectResult | None:
    """回读宿主实际状态(只读探测)。探测失败返回 None，由调用方按"无法确认"处理。

    宿主脚本输出视为不可信输入：不符合 inspect 契约的响应一律按探测失败处理。
    """
    try:
        result = run_host_script(
                     options=HostRunOptions(
                     host_ip=host_ip,
                     script_name="inspect-vm.sh",
                     payload=VMHostInspectPayload(
                vm_name=vm_name,
                system_disk_path=system_disk_path,
                data_disk_paths=data_disk_paths,
            ),
                     result_model=VMHostInspectResult,
                     ),
                 )
    except HostScriptError:
        return None
    if isinstance(result, VMHostInspectResult):
        return result
    try:
        return VMHostInspectResult.model_validate(result)
    except ValidationError:
        return None


def host_confirms_vm_gone(result: VMHostInspectResult | None) -> bool:
    """回读结果是否确认 VM 及其磁盘已全部不存在。

    只有宿主事实确认消失才允许自动落账收敛；回读失败或仍有残留一律视为未确认。
    """
    return (
        result is not None
        and not result.domain_exists
        and not result.system_disk_exists
        and not result.data_disks_existing
    )


def inspect_vm_host_state(db: Session, resource: Resource) -> VMHostInspectResult | None:
    """按资源解析宿主并回读 VM 实际状态(只读)。

    供销毁对账与恢复路径跨模块使用；缺虚拟规格、宿主不存在或探测失败均返回
    None，由调用方按"无法确认"处理。
    """
    spec = resource.virtual_spec
    if spec is None or not spec.host_resource_id:
        return None
    host = db.get(Resource, spec.host_resource_id)
    if host is None or not host.primary_ip:
        return None
    return _inspect_vm_host_state(
        host_ip=host.primary_ip,
        vm_name=spec.vm_name or resource.name or resource.resource_code,
        system_disk_path=spec.system_disk_path,
        data_disk_paths=spec.data_disk_paths or [],
    )


def _host_state_facts(result: VMHostInspectResult | None) -> str:
    """把回读事实渲染为事件文案；None 表示回读失败(无法确认宿主实际状态)。"""
    if result is None:
        return "回读宿主失败，无法确认宿主实际状态"
    if result.domain_exists:
        return f"宿主上 domain 仍存在(电源态 {result.power_state or 'unknown'})"
    if result.system_disk_exists or result.data_disks_existing:
        remaining = ([result.system_disk_path] if result.system_disk_exists else []) + [
            path for path in result.data_disks_existing
        ]
        return f"宿主上 domain 已不存在，但磁盘仍残留: {', '.join(remaining)}"
    return "宿主上 domain 与磁盘均不存在"


def _run_destroy_host_script(
    *,
    host_ip: str,
    payload: VMHostDestroyPayload,
    event_sink: Callable[[str, str], None],
) -> None:
    """执行 destroy-vm.sh，对瞬时连接失败做有限次退避重试。

    批量销毁会对同一宿主并发建多条 SSH，超出 sshd MaxStartups 的连接在 kex
    阶段被重置(host_connection_failed)，属瞬时故障；指数退避+抖动可自愈，
    抖动用于避免多任务齐步重试再次撞限。语义性失败直接抛出，不重试。
    每次重试前追加事件，保留原始失败事实。
    """
    last_exc: HostScriptError | None = None
    for attempt in range(1, VM_DESTROY_RETRY_ATTEMPTS + 1):
        try:
            run_host_script(
                options=HostRunOptions(
                host_ip=host_ip,
                script_name="destroy-vm.sh",
                payload=payload,
                result_model=VMHostDestroyResult,
                event_sink=event_sink,
                ),
            )
            return
        except HostScriptError as exc:
            if exc.code not in VM_DESTROY_CONNECT_RETRY_CODES:
                raise
            last_exc = exc
            if attempt == VM_DESTROY_RETRY_ATTEMPTS:
                break
            delay = VM_DESTROY_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            delay += (delay / 2) * (secrets.randbelow(10_000) / 10_000)
            event_sink(
                "destroy_retrying",
                f"宿主连接失败(第 {attempt} 次尝试)，{delay:.1f}s 后重试: {exc}",
            )
            time.sleep(delay)
    if last_exc is None:
        raise RuntimeError("宿主脚本未执行即退出")
    raise last_exc


def _best_effort_destroy_created_vm(*, host_ip: str, result: VMHostCreateResult) -> None:
    """无法确认新建 VM 状态时尽力清理，避免宿主机孤儿 VM。

    destroy-vm.sh 幂等(domain 不存在则只清磁盘)，清理失败不阻塞后续的
    attempt 失败处理——失败事件已携带回读上下文，供人工排查宿主残留。
    """
    try:
        run_host_script(
            options=HostRunOptions(
            host_ip=host_ip,
            script_name="destroy-vm.sh",
            payload=VMHostDestroyPayload(
                vm_name=result.vm_name,
                system_disk_path=result.system_disk_path,
                data_disk_paths=result.data_disk_paths,
            ),
            result_model=VMHostDestroyResult,
            ),
        )
    except HostScriptError:
        pass


def _confirm_created_vm_on_host(*, host_ip: str, result: VMHostCreateResult) -> None:
    """登记前回读宿主，确认新建 VM 真实存在。

    create-vm.sh 回传成功不代表 domain 真实存在(如创建后秒挂)。未确认存在时
    抛 HostScriptError(VM_NOT_CONFIRMED_AFTER_CREATE)：走既有 attempt 失败
    分支(本宿主记失败、换下一宿主)。无法确认宿主状态时先尽力回滚，避免
    宿主机孤儿 VM(平台不知道的 VM)。
    """
    inspect_result = _inspect_vm_host_state(
        host_ip=host_ip,
        vm_name=result.vm_name,
        system_disk_path=result.system_disk_path,
        data_disk_paths=result.data_disk_paths,
    )
    if inspect_result is not None and inspect_result.domain_exists:
        return
    if inspect_result is None:
        _best_effort_destroy_created_vm(host_ip=host_ip, result=result)
        raise HostScriptError(
            VM_NOT_CONFIRMED_AFTER_CREATE,
            "创建后回读宿主失败，无法确认 VM 存在，已尽力清理",
        )
    raise HostScriptError(
        VM_NOT_CONFIRMED_AFTER_CREATE,
        "创建后回读宿主未发现 VM，不登记",
    )


@dataclass(frozen=True)
class VMDestroyOptions:
    """VM 销毁执行选项（celery 载荷经 dict 传入）。"""

    actor_user_id: str | None = None
    reason: str | None = None
    force: bool = False
    task_id: str | None = None


def process_vm_destroy(
    resource_id: str,
    lease_id: str,
    *,
    options: VMDestroyOptions,
) -> bool:
    actor_user_id = options.actor_user_id
    reason = options.reason
    force = options.force
    task_id = options.task_id
    """VM 销毁的主编排(worker 调用，自带独立 DB 会话)。

    状态机：标记 started → 校验宿主/租约匹配 → SSH 跑 destroy-vm.sh →
    释放租约(有 actor 走 release_lease，无 actor 走自动释放) → 软删资源 →
    清除 execution_state。任一步失败都清 execution_state 并记 destroy_failed，
    返回 False；资源不存在或非虚拟机返回 True(视为无需处理)。
    """
    with SessionLocal() as db:
        resource = (
            db.execute(
                select(Resource)
                .options(selectinload(Resource.virtual_spec))
                .where(Resource.id == resource_id, Resource.deleted_at.is_(None))
            )
            .scalars()
            .one_or_none()
        )
        if resource is None:
            return True
        if resource.resource_type != ResourceType.VIRTUAL.value:
            return False
        if task_id is not None:
            mark_vm_destroy_started(resource, task_id=task_id, started_at=now_utc())
        record_vm_destroy_event(
            db,
            draft=VMDestroyEventDraft(
            resource=resource,
            phase="destroy_started",
            message="worker 已领取 VM 销毁任务",
            celery_task_id=task_id,
            ),
        )
        db.commit()

        spec = resource.virtual_spec
        if spec is None or not spec.host_resource_id:
            clear_vm_destroy_execution(resource, error="VM host is missing")
            record_vm_destroy_event(
                db,
                draft=VMDestroyEventDraft(
                resource=resource,
                phase="destroy_failed",
                message="VM 缺少宿主信息",
                celery_task_id=task_id,
                level="error",
                error_code="vm_host_missing",
                ),
            )
            db.commit()
            return False
        host = db.get(Resource, spec.host_resource_id)
        if host is None:
            clear_vm_destroy_execution(resource, error="VM host resource is missing")
            record_vm_destroy_event(
                db,
                draft=VMDestroyEventDraft(
                resource=resource,
                phase="destroy_failed",
                message="VM 宿主资源不存在",
                celery_task_id=task_id,
                level="error",
                error_code="vm_host_resource_missing",
                ),
            )
            db.commit()
            return False

        lease = get_active_lease(db, lease_id, for_update=True)
        if lease is None or lease.resource_id != resource.id:
            clear_vm_destroy_execution(
                resource,
                error="VM active lease is missing or mismatched",
            )
            record_vm_destroy_event(
                db,
                draft=VMDestroyEventDraft(
                resource=resource,
                phase="destroy_failed",
                message="VM 有效租约不存在或不匹配",
                celery_task_id=task_id,
                level="error",
                error_code="lease_missing",
                ),
            )
            db.commit()
            return False

        actor = db.get(User, actor_user_id) if actor_user_id else None
        record_vm_destroy_event(
            db,
            draft=VMDestroyEventDraft(
            resource=resource,
            phase="host_connecting",
            message=f"开始连接宿主 {host.primary_ip}",
            celery_task_id=task_id,
            host=host,
            ),
        )
        db.commit()

        def record_host_phase(phase: str, message: str) -> None:
            record_vm_destroy_event(
                db,
                draft=VMDestroyEventDraft(
                resource=resource,
                phase=phase,
                message=message,
                celery_task_id=task_id,
                host=host,
                ),
            )

        converged_facts: str | None = None
        try:
            _run_destroy_host_script(
                host_ip=host.primary_ip,
                payload=VMHostDestroyPayload(
                    vm_name=spec.vm_name or resource.name or resource.resource_code,
                    system_disk_path=spec.system_disk_path,
                    data_disk_paths=spec.data_disk_paths or [],
                ),
                event_sink=record_host_phase,
            )
        except HostScriptError as exc:
            # 脚本失败后回读宿主实际状态：只有宿主事实确认 VM 与磁盘均已不存在
            # (半执行/外部清理后才可能出现)才按事实落账收敛；否则记失败并携带
            # 宿主实际状态，保持资源与租约可重试。恢复逻辑不重删 VM 本体。
            inspect_result = _inspect_vm_host_state(
                host_ip=host.primary_ip,
                vm_name=spec.vm_name or resource.name or resource.resource_code,
                system_disk_path=spec.system_disk_path,
                data_disk_paths=spec.data_disk_paths or [],
            )
            if host_confirms_vm_gone(inspect_result):
                converged_facts = _host_state_facts(inspect_result)
                record_host_phase(
                    "host_confirmed_missing",
                    f"销毁脚本失败({exc.code})，回读宿主: {converged_facts}；"
                    "按宿主事实完成销毁落账",
                )
            else:
                clear_vm_destroy_execution(
                    resource,
                    error={"code": exc.code, "message": str(exc)},
                )
                record_vm_destroy_event(
                    db,
                    draft=VMDestroyEventDraft(
                    resource=resource,
                    phase="host_script_failed",
                    message=f"{exc}\n宿主回读: {_host_state_facts(inspect_result)}",
                    celery_task_id=task_id,
                    level="error",
                    host=host,
                    error_code=exc.code,
                    ),
                )
                db.commit()
                return False

        if actor is not None:
            release_lease(
                db,
                lease=lease,
                actor=actor,
                payload=LeaseReleaseNormalized(reason=reason or "VM destroyed"),
                force=force,
                allow_virtual=True,
            )
        else:
            _auto_release_lease_for_destroy(db, lease=lease, reason=reason)
        record_vm_destroy_event(
            db,
            draft=VMDestroyEventDraft(
            resource=resource,
            phase="lease_released",
            message="VM 租约已释放",
            celery_task_id=task_id,
            host=host,
            ),
        )
        clear_vm_destroy_execution(resource)
        resource.deleted_at = now_utc()
        resource.current_lease_id = None
        resource.occupancy_status = OccupancyStatus.IDLE.value
        record_vm_destroy_event(
            db,
            draft=VMDestroyEventDraft(
            resource=resource,
            phase="resource_deleted",
            message="VM 资源已软删除",
            celery_task_id=task_id,
            host=host,
            ),
        )
        record_vm_destroy_event(
            db,
            draft=VMDestroyEventDraft(
            resource=resource,
            phase="destroy_succeeded",
            message=f"VM 销毁成功(按宿主事实收敛: {converged_facts})"
                if converged_facts
                else "VM 销毁成功",
            celery_task_id=task_id,
            host=host,
            ),
        )
        db.commit()
        return True


def _auto_release_lease_for_destroy(
    db: Session, *, lease: ResourceLease, reason: str | None
) -> None:
    """销毁流程中无操作者(过期懒释放/恢复收敛)的租约自动释放。"""
    lease.released_at = now_utc()
    lease.release_reason = reason or "VM destroyed"
    record_lease_event(
        db,
        lease=lease,
        actor_user_id=None,
        event_type=LeaseEventType.AUTO_RELEASE,
        detail={"reason": lease.release_reason},
    )


def finalize_destroy_by_host_fact(
    db: Session,
    *,
    resource: Resource,
    task_id: str | None,
    source: str,
) -> bool:
    """宿主回读确认 VM 已消失后的销毁落账收敛(恢复路径复用)。

    自动释放仍有效的租约(无 actor，AUTO_RELEASE，不覆盖已有释放事实)、
    清 execution_state、软删资源，并追加 destroy_succeeded 事件注明收敛来源。
    返回是否执行了收敛；调用方保证仅在 host_confirms_vm_gone 为真时调用。
    """
    host: Resource | None = None
    spec = resource.virtual_spec
    if spec is not None and spec.host_resource_id:
        host = db.get(Resource, spec.host_resource_id)
    lease = (
        get_active_lease(db, resource.current_lease_id, for_update=True)
        if resource.current_lease_id
        else None
    )
    if lease is not None and lease.resource_id == resource.id:
        _auto_release_lease_for_destroy(db, lease=lease, reason="VM destroyed")
        record_vm_destroy_event(
            db,
            draft=VMDestroyEventDraft(
            resource=resource,
            phase="lease_released",
            message="VM 租约已释放(宿主事实收敛)",
            celery_task_id=task_id,
            host=host,
            ),
        )
    clear_vm_destroy_execution(resource)
    resource.deleted_at = now_utc()
    resource.current_lease_id = None
    resource.occupancy_status = OccupancyStatus.IDLE.value
    record_vm_destroy_event(
        db,
        draft=VMDestroyEventDraft(
        resource=resource,
        phase="destroy_succeeded",
        message=f"回读宿主确认 VM 与磁盘已不存在({source})，按宿主事实完成销毁落账",
        celery_task_id=task_id,
        host=host,
        ),
    )
    db.commit()
    return True

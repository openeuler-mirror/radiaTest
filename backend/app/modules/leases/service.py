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
from datetime import UTC, datetime, timedelta

from cryptography.fernet import InvalidToken
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.core.pagination import PAGE_SIZE, PageParams
from app.modules.leases.models import (
    LeaseEvent,
    LeaseEventType,
    ResourceLease,
)
from app.modules.leases.schemas import (
    LeaseCreate,
    LeaseEventListParams,
    LeaseEventRead,
    LeaseExtend,
    LeaseRead,
    LeaseRelease,
    ResourceCredentialRead,
    ResourceSshCredentialRead,
)
from app.modules.resources.models import ManagementStatus, OccupancyStatus, Resource, ResourceType
from app.modules.test_management.physical_resources import active_physical_test_usage
from app.modules.users.models import User, UserRole
from app.modules.vms.execution_state import (
    get_vm_destroy_execution,
    mark_vm_destroy_queued,
)

# 租约领域服务：占用、续期、释放、懒释放过期租约与凭据查看的鉴权。
# 权限与状态规则集中在此处，路由只做请求解析与状态码映射。

# 普通用户(TE/TSE)租约最长 14 天；ADMIN 可创建永久租约，不受此限。
MAX_NON_ADMIN_LEASE = timedelta(days=14)
# 截止时间容差：放宽一分钟，避免边界时刻因时钟漂移被误判为超期。
LEASE_DEADLINE_TOLERANCE = timedelta(minutes=1)
# 续期上限：续期后的结束时间不得晚于当前时间起 7 天，防止用续期规避新建租约的限制。
MAX_LEASE_EXTENSION = timedelta(days=7)


class LeasePolicyError(Exception):
    """租约业务规则被违反（如非 active 资源占用、超过 14 天上限）。"""


class LeaseConflictError(Exception):
    """租约状态冲突（如重复占用、重复释放）。"""


class CredentialPolicyError(Exception):
    """凭据查看的鉴权策略被拒绝（非 ADMIN 查看关键资源凭据等）。"""


class CredentialReadError(Exception):
    """凭据密文无法解密，通常意味着 RESOURCE_SECRET_KEY 与加密时不一致。"""


def list_lease_events(
    db: Session,
    *,
    actor: User,
    params: LeaseEventListParams,
    pagination: PageParams,
) -> tuple[list[LeaseEventRead], int]:
    """分页查询租约事件。

    权限边界：TE 角色只能看到与自己相关的租约事件；TSE/ADMIN 可查全部。
    结果按创建时间倒序，返回 (条目列表, 总数) 供分页使用。
    """
    conditions = []
    if actor.role == UserRole.TE.value:
        conditions.append(ResourceLease.user_id == actor.id)
    if params.event_type:
        conditions.append(LeaseEvent.event_type.ilike(f"%{params.event_type}%"))
    if params.actor_username:
        conditions.append(User.username.ilike(f"%{params.actor_username}%"))
    if params.resource_code:
        conditions.append(Resource.resource_code.ilike(f"%{params.resource_code}%"))
    if params.resource_type:
        conditions.append(Resource.resource_type == params.resource_type)
    if params.primary_ip:
        conditions.append(Resource.primary_ip.ilike(f"%{params.primary_ip}%"))
    if params.started_at:
        conditions.append(LeaseEvent.created_at >= params.started_at)
    if params.ended_at:
        conditions.append(LeaseEvent.created_at <= params.ended_at)

    base_statement = (
        select(
            LeaseEvent,
            Resource.resource_code,
            Resource.primary_ip,
            Resource.resource_type,
            User.username,
        )
        .join(ResourceLease, LeaseEvent.lease_id == ResourceLease.id)
        .outerjoin(Resource, LeaseEvent.resource_id == Resource.id)
        .outerjoin(User, LeaseEvent.actor_user_id == User.id)
    )
    if conditions:
        base_statement = base_statement.where(and_(*conditions))
    statement = (
        base_statement.order_by(LeaseEvent.created_at.desc(), LeaseEvent.id)
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    count_statement = (
        select(func.count(LeaseEvent.id))
        .join(ResourceLease, LeaseEvent.lease_id == ResourceLease.id)
        .outerjoin(Resource, LeaseEvent.resource_id == Resource.id)
        .outerjoin(User, LeaseEvent.actor_user_id == User.id)
    )
    if conditions:
        count_statement = count_statement.where(and_(*conditions))
    rows = db.execute(statement).all()
    items = [
        LeaseEventRead(
            id=event.id,
            lease_id=event.lease_id,
            resource_id=event.resource_id,
            resource_code=resource_code,
            primary_ip=primary_ip,
            resource_type=resource_type,
            actor_user_id=event.actor_user_id,
            actor_username=actor_username,
            event_type=event.event_type,
            detail=event.detail,
            created_at=event.created_at,
        )
        for event, resource_code, primary_ip, resource_type, actor_username in rows
    ]
    total = db.scalar(count_statement) or 0
    return items, total


def now_utc() -> datetime:
    return datetime.now(UTC)


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def serialize_lease(db: Session, lease: ResourceLease) -> LeaseRead:
    user = db.get(User, lease.user_id)
    return LeaseRead(
        id=lease.id,
        resource_id=lease.resource_id,
        user_id=lease.user_id,
        username=user.username if user else None,
        purpose=lease.purpose,
        starts_at=lease.starts_at,
        expected_ends_at=lease.expected_ends_at,
        released_at=lease.released_at,
        released_by_user_id=lease.released_by_user_id,
        release_reason=lease.release_reason,
    )


def lease_to_summary(db: Session, lease: ResourceLease | None) -> dict[str, object | None]:
    if lease is None:
        return {
            "current_lease_id": None,
            "current_lease_user_id": None,
            "current_lease_username": None,
            "current_lease_user_role": None,
            "current_lease_purpose": None,
            "current_lease_expected_ends_at": None,
        }
    user = db.get(User, lease.user_id)
    return {
        "current_lease_id": lease.id,
        "current_lease_user_id": lease.user_id,
        "current_lease_username": user.username if user else None,
        "current_lease_user_role": user.role if user else None,
        "current_lease_purpose": lease.purpose,
        "current_lease_expected_ends_at": lease.expected_ends_at,
    }


def get_active_lease(
    db: Session,
    lease_id: str,
    *,
    for_update: bool = False,
) -> ResourceLease | None:
    """按 ID 取未释放的租约。

    for_update=True 时加行锁，供占用/释放/续期等需要在同一事务内串行化的场景
    防止并发修改同一租约。返回 None 表示租约不存在或已释放。
    """
    statement = select(ResourceLease).where(
        ResourceLease.id == lease_id,
        ResourceLease.released_at.is_(None),
    )
    if for_update:
        statement = statement.with_for_update()
    return db.execute(statement).scalar_one_or_none()


def get_resource_active_lease(db: Session, resource: Resource) -> ResourceLease | None:
    if resource.current_lease_id:
        lease = get_active_lease(db, resource.current_lease_id)
        if lease is not None:
            return lease

    statement = select(ResourceLease).where(
        ResourceLease.resource_id == resource.id,
        ResourceLease.released_at.is_(None),
    )
    return db.execute(statement).scalar_one_or_none()


def get_active_leases_by_resource_id(
    db: Session,
    resources: list[Resource],
) -> dict[str, ResourceLease]:
    resource_ids = [resource.id for resource in resources]
    if not resource_ids:
        return {}

    statement = select(ResourceLease).where(
        ResourceLease.resource_id.in_(resource_ids),
        ResourceLease.released_at.is_(None),
    )
    leases = db.execute(statement).scalars().all()
    return {lease.resource_id: lease for lease in leases}


def record_lease_event(
    db: Session,
    *,
    lease: ResourceLease,
    actor_user_id: str | None,
    event_type: LeaseEventType,
    detail: dict[str, object] | None = None,
) -> LeaseEvent:
    """写一条租约事件到审计流，用于页面详情和租约日志回溯。flush 后即可取到 id。"""
    event = LeaseEvent(
        lease_id=lease.id,
        resource_id=lease.resource_id,
        actor_user_id=actor_user_id,
        event_type=event_type.value,
        detail=detail or {},
    )
    db.add(event)
    db.flush()
    return event


def release_expired_leases(db: Session) -> int:
    """懒释放(Lazy Release)过期租约。

    物理资源：直接置为 released 并把资源占用状态恢复 idle。
    虚拟资源：不在此处直接释放，而是把 occupancy 标记 expired 并跨模块入队
    enqueue_vm_destroy(force=True)，由 VM 模块异步销毁后再清账。若入队失败，
    只把错误记到 resource.extra，不影响其他租约释放——下次调用会重试入队。
    全程对租约和资源行加锁，避免与并发的占用/释放产生竞态。
    """
    current_time = now_utc()
    statement = (
        select(ResourceLease)
        .where(
            ResourceLease.released_at.is_(None),
            ResourceLease.expected_ends_at.is_not(None),
            ResourceLease.expected_ends_at <= current_time,
        )
        .with_for_update()
    )
    expired_leases = list(db.execute(statement).scalars().all())
    for lease in expired_leases:
        resource = db.get(Resource, lease.resource_id, with_for_update=True)
        if resource is not None and resource.resource_type == ResourceType.VIRTUAL.value:
            extra = resource.extra or {}
            from app.modules.vms.service import enqueue_vm_destroy

            already_enqueued = get_vm_destroy_execution(resource) is not None
            if resource.occupancy_status != OccupancyStatus.EXPIRED.value:
                resource.occupancy_status = OccupancyStatus.EXPIRED.value
            if not already_enqueued:
                try:
                    task_id = enqueue_vm_destroy(
                        resource_id=resource.id,
                        lease_id=lease.id,
                        actor_user_id=None,
                        reason="expired",
                        force=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    resource.extra = {
                        **extra,
                        "vm_destroy_enqueue_error": str(exc),
                        "vm_destroy_enqueue_failed_at": current_time.isoformat(),
                    }
                else:
                    mark_vm_destroy_queued(
                        resource,
                        task_id=task_id,
                        enqueued_at=current_time,
                    )
            continue

        lease.released_at = current_time
        lease.release_reason = "expired"
        if resource is not None and resource.current_lease_id == lease.id:
            resource.current_lease_id = None
            resource.occupancy_status = OccupancyStatus.IDLE.value
        record_lease_event(
            db,
            lease=lease,
            actor_user_id=None,
            event_type=LeaseEventType.AUTO_RELEASE,
            detail={"reason": "expired"},
        )

    if expired_leases:
        db.flush()
    return len(expired_leases)


def ensure_occupy_allowed(resource: Resource, actor: User, payload: LeaseCreate) -> datetime | None:
    """占用前的业务规则校验，返回规范化后的 expected_ends_at。

    不可破坏约束：
    - 仅 active 且当前 idle 的资源可被占用。
    - 关键资源(is_critical)只有 ADMIN 可占用。
    - TE/TSE 必须提供未来时间且不超过 14 天的 expected_ends_at；ADMIN 可给
      None 表示永久租约，给则也必须在未来。
    容差 LEASE_DEADLINE_TOLERANCE 用于吸收边界时刻的时钟漂移。
    """
    if resource.management_status != ManagementStatus.ACTIVE.value:
        raise LeasePolicyError("Only active resources can be occupied")
    if resource.occupancy_status != OccupancyStatus.IDLE.value or resource.current_lease_id:
        raise LeaseConflictError("Resource is already occupied")
    if resource.is_critical and actor.role != UserRole.ADMIN.value:
        raise LeasePolicyError("Only ADMIN can occupy critical resources")

    expected_ends_at = normalize_datetime(payload.expected_ends_at)
    if actor.role != UserRole.ADMIN.value:
        if expected_ends_at is None:
            raise LeasePolicyError("TE and TSE leases require expected_ends_at")
        if expected_ends_at <= now_utc():
            raise LeasePolicyError("expected_ends_at must be in the future")
        if expected_ends_at > now_utc() + MAX_NON_ADMIN_LEASE + LEASE_DEADLINE_TOLERANCE:
            raise LeasePolicyError("TE and TSE leases cannot exceed 14 days")
    elif expected_ends_at is not None and expected_ends_at <= now_utc():
        raise LeasePolicyError("expected_ends_at must be in the future")

    return expected_ends_at


def create_lease(
    db: Session,
    *,
    resource: Resource,
    actor: User,
    payload: LeaseCreate,
) -> ResourceLease:
    """创建租约并把资源占用状态从 idle 置为 occupied。调用前须已通过 ensure_occupy_allowed。"""
    expected_ends_at = ensure_occupy_allowed(resource, actor, payload)
    lease = ResourceLease(
        resource_id=resource.id,
        user_id=actor.id,
        purpose=payload.purpose.strip(),
        expected_ends_at=expected_ends_at,
    )
    db.add(lease)
    db.flush()

    resource.current_lease_id = lease.id
    resource.occupancy_status = OccupancyStatus.OCCUPIED.value
    record_lease_event(
        db,
        lease=lease,
        actor_user_id=actor.id,
        event_type=LeaseEventType.OCCUPY,
        detail={
            "purpose": lease.purpose,
            "expected_ends_at": expected_ends_at.isoformat() if expected_ends_at else None,
        },
    )
    db.flush()
    return lease


def extend_lease(
    db: Session,
    *,
    lease: ResourceLease,
    actor: User,
    payload: LeaseExtend,
) -> ResourceLease:
    """
    续期租约。仅租约本人可续；永久租约不可续；新结束时间须晚于当前结束时间
    且不晚于当前时间起 MAX_LEASE_EXTENSION(7 天)加容差。
    """
    if lease.released_at is not None:
        raise LeaseConflictError("Lease is already released")
    if lease.user_id != actor.id:
        raise LeasePolicyError("Only the lease owner can extend this lease")
    if lease.expected_ends_at is None:
        raise LeasePolicyError("Permanent leases cannot be extended")

    expected_ends_at = normalize_datetime(payload.expected_ends_at)
    if expected_ends_at is None:
        raise LeasePolicyError("expected_ends_at is required")

    now = now_utc()
    current_expected_ends_at = normalize_datetime(lease.expected_ends_at)
    if expected_ends_at <= now:
        raise LeasePolicyError("expected_ends_at must be in the future")
    if expected_ends_at <= current_expected_ends_at:
        raise LeasePolicyError("expected_ends_at must be later than current lease end")
    if expected_ends_at > now + MAX_LEASE_EXTENSION + LEASE_DEADLINE_TOLERANCE:
        raise LeasePolicyError("Lease extension cannot exceed 7 days from now")

    lease.expected_ends_at = expected_ends_at
    record_lease_event(
        db,
        lease=lease,
        actor_user_id=actor.id,
        event_type=LeaseEventType.EXTEND,
        detail={
            "previous_expected_ends_at": current_expected_ends_at.isoformat(),
            "expected_ends_at": expected_ends_at.isoformat(),
        },
    )
    db.flush()
    return lease


@dataclass(frozen=True)
class LeaseReleaseCommand:
    """租约释放命令：租约本体、操作者、释放载荷与策略开关。"""

    lease: ResourceLease
    actor: User
    payload: LeaseRelease
    force: bool = False
    allow_virtual: bool = False


def release_lease(
    db: Session,
    *,
    command: LeaseReleaseCommand,
) -> ResourceLease:
    """释放租约并把资源恢复 idle。

    权限矩阵：本人可自释放；ADMIN 可强制释放任意租约；TSE 可强制释放 TE 的
    租约；其余强制释放一律拒绝。虚拟机租约默认禁止从这里释放(allow_virtual
    默认 False)，必须走 VM 模块的释放入口先销毁 VM 再清账，避免出现 VM 仍在
    运行但租约已释放的不一致状态。
    """
    lease = command.lease
    actor = command.actor
    payload = command.payload
    force = command.force
    allow_virtual = command.allow_virtual
    if lease.released_at is not None:
        raise LeaseConflictError("Lease is already released")

    resource = db.get(Resource, lease.resource_id)
    if (
        resource is not None
        and resource.resource_type == ResourceType.VIRTUAL.value
        and not allow_virtual
    ):
        raise LeasePolicyError("虚拟机租约必须通过虚拟机释放功能处理")
    if resource is not None and active_physical_test_usage(db, resource.id) is not None:
        raise LeaseConflictError("物理机正在执行测试，不能释放租约")

    lease_user = db.get(User, lease.user_id)
    if force:
        if actor.role == UserRole.ADMIN.value:
            pass
        elif (
            actor.role == UserRole.TSE.value
            and lease_user
            and lease_user.role == UserRole.TE.value
        ):
            pass
        else:
            raise LeasePolicyError("Actor cannot force release this lease")
    elif lease.user_id != actor.id:
        raise LeasePolicyError("Only the lease owner can release this lease")

    release_time = now_utc()
    lease.released_at = release_time
    lease.released_by_user_id = actor.id
    lease.release_reason = payload.reason

    if resource is not None and resource.current_lease_id == lease.id:
        resource.current_lease_id = None
        resource.occupancy_status = OccupancyStatus.IDLE.value

    record_lease_event(
        db,
        lease=lease,
        actor_user_id=actor.id,
        event_type=LeaseEventType.FORCE_RELEASE if force else LeaseEventType.RELEASE,
        detail={"reason": payload.reason},
    )
    db.flush()
    return lease


def ensure_credentials_allowed(
    db: Session,
    *,
    resource: Resource,
    actor: User,
) -> None:
    """凭据查看的鉴权边界(最终边界，前端可见性只用于体验)。

    - 关键资源：仅 ADMIN 可查看凭据。
    - 非关键资源：ADMIN 可看；其余角色必须是该资源当前占用者本人。
    不满足则抛 CredentialPolicyError。
    """
    if resource.is_critical:
        if actor.role != UserRole.ADMIN.value:
            raise CredentialPolicyError("Only ADMIN can view critical resource credentials")
        return

    if actor.role == UserRole.ADMIN.value:
        return

    lease = get_resource_active_lease(db, resource)
    if lease is None or lease.user_id != actor.id:
        raise CredentialPolicyError("Only current occupier can view credentials")


def read_resource_credentials(
    db: Session,
    *,
    resource: Resource,
    actor: User,
) -> ResourceCredentialRead:
    """
    解密并返回资源凭据(SSH + BMC)。调用前须通过 ensure_credentials_allowed。
    密文无法解密时抛 CredentialReadError，提示 RESOURCE_SECRET_KEY 可能不一致。
    """
    ensure_credentials_allowed(db, resource=resource, actor=actor)
    try:
        return ResourceCredentialRead(
            ssh_username=resource.ssh_username,
            ssh_password=decrypt_secret(resource.ssh_password_ciphertext),
            bmc_username=resource.physical_spec.bmc_username if resource.physical_spec else None,
            bmc_password=(
                decrypt_secret(resource.physical_spec.bmc_password_ciphertext)
                if resource.resource_type == ResourceType.PHYSICAL.value and resource.physical_spec
                else None
            ),
        )
    except InvalidToken as exc:
        raise CredentialReadError("Resource credentials cannot be decrypted") from exc


def read_resource_ssh_credentials(
    db: Session,
    *,
    resource: Resource,
    actor: User,
) -> ResourceSshCredentialRead:
    """解密并返回资源 SSH 凭据(供飞书远程命令等场景)。

    鉴权与解密语义同 read_resource_credentials。
    """
    ensure_credentials_allowed(db, resource=resource, actor=actor)
    try:
        return ResourceSshCredentialRead(
            ssh_username=resource.ssh_username,
            ssh_password=decrypt_secret(resource.ssh_password_ciphertext),
        )
    except InvalidToken as exc:
        raise CredentialReadError("Resource SSH credentials cannot be decrypted") from exc

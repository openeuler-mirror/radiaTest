# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import re
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import Integer, and_, case, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.credentials import encrypt_secret
from app.core.pagination import PAGE_SIZE, PageParams
from app.modules.leases.models import ResourceLease
from app.modules.leases.service import (
    get_active_leases_by_resource_id,
    get_resource_active_lease,
    lease_to_summary,
)
from app.modules.resources.models import (
    ConnectivityStatus,
    ManagementStatus,
    PhysicalResourceSpec,
    Resource,
    ResourceType,
    VirtualResourceSpec,
)
from app.modules.resources.physical_install_models import (
    InstallImageBaseVariant,
    PhysicalInstallImage,
)
from app.modules.resources.schemas import (
    ResourceCreate,
    ResourceListParams,
    ResourceRead,
    ResourceUpdate,
)
from app.modules.test_management.physical_resources import (
    PhysicalTestUsage,
    active_physical_test_usage,
    active_physical_test_usages,
)
from app.modules.users.models import User, UserRole

# 资源台账服务：查询、创建、更新、硬件探测回写与 PXE 安装镜像维护。
# 凭据密文统一经 app.core.credentials 加解密；权限与租约规则跨模块委托给
# leases 模块，resources 只负责资源本身的不变量与序列化。


class ResourceAlreadyExistsError(Exception):
    """resource_code 已存在，创建时唯一约束冲突。"""


class ResourceInvariantError(Exception):
    """物理机必填凭据/连通字段缺失，违反资源不变量。"""


class ResourcePolicyError(Exception):
    """资源管理策略被拒绝(角色不足以创建/编辑、TSE 越权等)。"""


class ResourceBusyError(Exception):
    """物理资源正在执行测试，禁止会破坏测试环境的写操作。"""


FILTER_COLUMNS = {
    "resource_code": Resource.resource_code,
    "resource_type": Resource.resource_type,
    "name": Resource.name,
    "management_status": Resource.management_status,
    "occupancy_status": Resource.occupancy_status,
    "primary_ip": Resource.primary_ip,
    "mac_address": Resource.mac_address,
    "arch": Resource.arch,
    "os_version": Resource.os_version,
    "kernel_version": Resource.kernel_version,
    "usage_scenario": Resource.usage_scenario,
    "bmc_ip": PhysicalResourceSpec.bmc_ip,
    "cpu_model": PhysicalResourceSpec.cpu_model,
    "current_lease_username": User.username,
    "current_lease_purpose": ResourceLease.purpose,
}

RESOURCE_FIELDS = {
    "name",
    "management_status",
    "connectivity_status",
    "is_critical",
    "primary_ip",
    "mac_address",
    "arch",
    "os_version",
    "kernel_version",
    "ssh_username",
    "tags",
    "usage_scenario",
    "extra",
}

PHYSICAL_SPEC_FIELDS = {
    "device_location",
    "device_distribution",
    "bmc_ip",
    "bmc_username",
    "cpu_model",
    "cpu_count",
    "memory_count",
    "memory_spec",
    "hdd_count",
    "hdd_spec",
    "ssd_count",
    "ssd_spec",
    "ssd_card_count",
    "ssd_card_spec",
    "board_sn",
}

VIRTUAL_SPEC_FIELDS = {
    "vm_name",
    "vnc_port",
    "vnc_websocket_port",
    "vcpu_count",
    "memory_mb",
    "disk_gb",
    "host_resource_id",
    "system_disk_path",
    "data_disk_count",
    "data_disk_size_gb",
    "data_disk_paths",
}

_MISSING_LEASE = object()
_MISSING_TEST_USAGE = object()
_NATURAL_SORT_PATTERN = re.compile(r"(\d+)")

NaturalSortPart = tuple[int, int | str]
NaturalSortKey = tuple[NaturalSortPart, ...]


def serialize_resource(
    db: Session,
    resource: Resource,
    current_lease: object = _MISSING_LEASE,
    test_usage: PhysicalTestUsage | None | object = _MISSING_TEST_USAGE,
) -> ResourceRead:
    physical_spec = resource.physical_spec
    virtual_spec = resource.virtual_spec
    if current_lease is _MISSING_LEASE:
        current_lease = get_resource_active_lease(db, resource)
    if test_usage is _MISSING_TEST_USAGE:
        test_usage = active_physical_test_usage(db, resource.id)
    physical_data = {
        field_name: getattr(physical_spec, field_name, None) for field_name in PHYSICAL_SPEC_FIELDS
    }
    virtual_data = {
        field_name: getattr(virtual_spec, field_name, None) for field_name in VIRTUAL_SPEC_FIELDS
    }
    virtual_data["data_disk_paths"] = virtual_data["data_disk_paths"] or []
    host_primary_ip = None
    if virtual_spec and virtual_spec.host_resource_id:
        host = db.get(Resource, virtual_spec.host_resource_id)
        host_primary_ip = host.primary_ip if host else None

    return ResourceRead.model_validate(
        {
            **resource.__dict__,
            **physical_data,
            **virtual_data,
            **lease_to_summary(db, current_lease if current_lease is not _MISSING_LEASE else None),
            "has_ssh_password": bool(resource.ssh_password_ciphertext),
            "has_bmc_password": bool(physical_spec and physical_spec.bmc_password_ciphertext),
            "host_primary_ip": host_primary_ip,
            "test_status": "testing" if test_usage else "idle",
            "current_test_job_id": test_usage.test_job_id if test_usage else None,
        }
    )


def get_resource(db: Session, resource_id: str) -> Resource | None:
    statement = (
        select(Resource)
        .options(selectinload(Resource.physical_spec), selectinload(Resource.virtual_spec))
        .where(Resource.id == resource_id, Resource.deleted_at.is_(None))
    )
    return db.execute(statement).scalar_one_or_none()


def resource_reuse_unavailable_reason(db: Session, resource_id: str) -> str | None:
    """返回保留环境复用该资源时的不可用原因。"""
    resource = get_resource(db, resource_id)
    if resource is None or not resource.primary_ip:
        return "来源资源不可用"
    if resource.management_status != ManagementStatus.ACTIVE.value:
        return "来源资源未处于可用管理状态"
    if resource.connectivity_status == ConnectivityStatus.UNREACHABLE.value:
        return "来源资源当前不可达"
    lease = get_resource_active_lease(db, resource)
    if lease is None:
        return "来源资源租约已释放"
    if lease.expected_ends_at is not None:
        ends_at = lease.expected_ends_at
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=UTC)
        if ends_at <= datetime.now(UTC):
            return "来源资源租约已过期"
    return None


def get_resource_including_deleted(db: Session, resource_id: str) -> Resource | None:
    statement = (
        select(Resource)
        .options(selectinload(Resource.physical_spec), selectinload(Resource.virtual_spec))
        .where(Resource.id == resource_id)
    )
    return db.execute(statement).scalar_one_or_none()


def get_resource_by_code(db: Session, resource_code: str) -> Resource | None:
    statement = select(Resource).where(
        Resource.resource_code == resource_code,
        Resource.deleted_at.is_(None),
    )
    return db.execute(statement).scalar_one_or_none()


def ensure_resource_invariants(resource: Resource) -> None:
    """校验物理机资源的必填连通字段(primary_ip/ssh/bmc)，缺失抛 ResourceInvariantError。

    虚拟资源不校验(其凭据由 VM 模块管理)。此校验在创建和更新后执行，是
    物理机可被占用/探测的前提，避免台架上出现无凭据的空壳资源。
    """
    if resource.resource_type != ResourceType.PHYSICAL.value:
        return

    physical = resource.physical_spec
    missing = []
    if not resource.primary_ip:
        missing.append("primary_ip")
    if not resource.ssh_username:
        missing.append("ssh_username")
    if not resource.ssh_password_ciphertext:
        missing.append("ssh_password")
    if physical is None or not physical.bmc_ip:
        missing.append("bmc_ip")
    if physical is None or not physical.bmc_username:
        missing.append("bmc_username")
    if physical is None or not physical.bmc_password_ciphertext:
        missing.append("bmc_password")
    if missing:
        raise ResourceInvariantError(f"物理机资源缺少必填字段：{', '.join(missing)}")


def natural_sort_key(value: str | None) -> NaturalSortKey:
    """把字符串拆成数字/非数字段，使 IP/编号按人类直觉排序(如 10 排在 9 之后、2 之前)。

    None/空值排到最后(以 (2,"") 标记)，保证无 IP 资源不抢占前列。
    """
    if not value:
        return ((2, ""),)
    parts: list[NaturalSortPart] = []
    for part in _NATURAL_SORT_PATTERN.split(value.casefold()):
        if not part:
            continue
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return tuple(parts)


def resource_default_sort_key(resource: Resource) -> tuple[NaturalSortKey, str]:
    return (natural_sort_key(resource.primary_ip), resource.id)


def _resource_conditions(params: ResourceListParams) -> list[object]:
    conditions: list[object] = [Resource.deleted_at.is_(None)]
    filter_conditions = []

    for field_name, column in FILTER_COLUMNS.items():
        value = getattr(params, field_name)
        if value:
            filter_conditions.append(column.ilike(f"%{value}%"))

    if filter_conditions:
        conditions.append(
            or_(*filter_conditions) if params.match == "or" else and_(*filter_conditions)
        )
    return conditions


def _resource_statement(params: ResourceListParams):
    return (
        select(Resource)
        .outerjoin(Resource.physical_spec)
        .outerjoin(Resource.virtual_spec)
        .outerjoin(ResourceLease, Resource.current_lease_id == ResourceLease.id)
        .outerjoin(User, ResourceLease.user_id == User.id)
        .options(selectinload(Resource.physical_spec), selectinload(Resource.virtual_spec))
        .where(*_resource_conditions(params))
    )


def _primary_ip_order_columns(db: Session) -> tuple[object, ...]:
    """构造按 IP 数值大小排序的列：先把 primary_ip 拆成 4 段整数，再按段排序。

    PostgreSQL 用正则判 IPv4 并 split_part 取段；其他方言(SQLite)用
    instr/substr 模拟。address_kind 把 NULL IP 排到末尾。这是 list 与
    paginate 排序结果不一致的根因——list 在 Python 层用 natural_sort_key，
    paginate 在 DB 层用此列；两者都保证 NULL/非 IPv4 排末尾。
    """
    primary_ip = Resource.primary_ip
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        is_ipv4 = primary_ip.op("~")(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
        octets = tuple(
            case(
                (is_ipv4, cast(func.split_part(primary_ip, ".", index), Integer)),
                else_=None,
            )
            for index in range(1, 5)
        )
        address_kind = case((primary_ip.is_(None), 2), (is_ipv4, 0), else_=1)
    else:
        remaining = primary_ip
        parsed_octets = []
        for _ in range(3):
            separator = func.instr(remaining, ".")
            parsed_octets.append(cast(func.substr(remaining, 1, separator - 1), Integer))
            remaining = func.substr(remaining, separator + 1)
        parsed_octets.append(cast(remaining, Integer))
        octets = tuple(parsed_octets)
        address_kind = case((primary_ip.is_(None), 2), else_=0)

    return (
        address_kind,
        *octets,
        func.lower(primary_ip),
        Resource.id,
    )


def list_resources(
    db: Session,
    *,
    params: ResourceListParams,
    offset: int = 0,
    limit: int | None = 50,
) -> list[Resource]:
    statement = _resource_statement(params)
    resources = list(db.execute(statement).scalars().unique().all())
    resources.sort(key=resource_default_sort_key)
    if limit is None:
        return resources[offset:]
    return resources[offset:offset + limit]


def paginate_resources(
    db: Session,
    *,
    params: ResourceListParams,
    pagination: PageParams,
) -> tuple[list[Resource], int]:
    conditions = _resource_conditions(params)
    total = (
        db.scalar(
            select(func.count(Resource.id))
            .outerjoin(Resource.physical_spec)
            .outerjoin(Resource.virtual_spec)
            .outerjoin(ResourceLease, Resource.current_lease_id == ResourceLease.id)
            .outerjoin(User, ResourceLease.user_id == User.id)
            .where(*conditions)
        )
        or 0
    )
    statement = (
        _resource_statement(params)
        .order_by(*_primary_ip_order_columns(db))
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    resources = list(db.execute(statement).scalars().unique().all())
    return resources, total


def create_resource(db: Session, payload: ResourceCreate) -> Resource:
    if get_resource_by_code(db, payload.resource_code) is not None:
        raise ResourceAlreadyExistsError(payload.resource_code)

    payload_data = payload.model_dump(mode="json")
    resource_data = {
        field_name: payload_data[field_name]
        for field_name in RESOURCE_FIELDS
        if field_name in payload_data
    }
    resource = Resource(
        resource_code=payload.resource_code,
        resource_type=payload.resource_type.value,
        ssh_password_ciphertext=encrypt_secret(payload.ssh_password) or "",
        **resource_data,
    )
    if payload.resource_type == ResourceType.PHYSICAL:
        resource.physical_spec = PhysicalResourceSpec(
            bmc_password_ciphertext=encrypt_secret(payload.bmc_password),
            **{
                field_name: payload_data[field_name]
                for field_name in PHYSICAL_SPEC_FIELDS
                if field_name in payload_data
            },
        )
    else:
        resource.virtual_spec = VirtualResourceSpec(
            **{
                field_name: payload_data[field_name]
                for field_name in VIRTUAL_SPEC_FIELDS
                if field_name in payload_data
            },
        )

    db.add(resource)
    db.flush()
    return resource


def create_managed_resource(
    db: Session,
    *,
    actor: User,
    payload: ResourceCreate,
) -> Resource:
    """带角色策略的资源创建：仅 ADMIN/TSE 可创建；TSE 只能创建 active 资源。

    凭据在此处加密落库，明文不入库不入日志。
    """
    if actor.role not in {UserRole.ADMIN.value, UserRole.TSE.value}:
        raise ResourcePolicyError("Resource manager role required")
    if actor.role == UserRole.TSE.value and payload.management_status != ManagementStatus.ACTIVE:
        raise ResourcePolicyError("TSE can only create active resources")
    return create_resource(db, payload)


def update_resource(db: Session, resource: Resource, payload: ResourceUpdate) -> Resource:
    update_data = payload.model_dump(exclude_unset=True, mode="json")

    for field_name, value in update_data.items():
        if field_name in RESOURCE_FIELDS:
            setattr(resource, field_name, value)

    if "ssh_password" in update_data:
        resource.ssh_password_ciphertext = encrypt_secret(payload.ssh_password) or ""

    if resource.resource_type == ResourceType.PHYSICAL.value:
        if resource.physical_spec is None:
            resource.physical_spec = PhysicalResourceSpec()
        for field_name in PHYSICAL_SPEC_FIELDS:
            if field_name in update_data:
                setattr(resource.physical_spec, field_name, update_data[field_name])
        if "bmc_password" in update_data:
            resource.physical_spec.bmc_password_ciphertext = encrypt_secret(payload.bmc_password)

    if resource.resource_type == ResourceType.VIRTUAL.value:
        if resource.virtual_spec is None:
            resource.virtual_spec = VirtualResourceSpec()
        for field_name in VIRTUAL_SPEC_FIELDS:
            if field_name in update_data:
                setattr(resource.virtual_spec, field_name, update_data[field_name])

    ensure_resource_invariants(resource)
    db.flush()
    return resource


def update_managed_resource(
    db: Session,
    *,
    actor: User,
    resource: Resource,
    payload: ResourceUpdate,
) -> Resource:
    """带角色策略的资源更新。

    TSE 的不可破坏约束：不能改 management_status(仅 ADMIN)、不能编辑他人占用的
    资源、只能编辑 active 资源。ADMIN 无限制。更新后跑 ensure_resource_invariants
    保证物理机凭据/连通字段不被清空。
    """
    if actor.role not in {UserRole.ADMIN.value, UserRole.TSE.value}:
        raise ResourcePolicyError("Resource manager role required")
    ensure_resource_not_testing(db, resource, action="修改资源")
    if actor.role == UserRole.TSE.value:
        if "management_status" in payload.model_fields_set:
            raise ResourcePolicyError("Only ADMIN can modify management status")
        active_lease = get_resource_active_lease(db, resource)
        if active_lease is not None and active_lease.user_id != actor.id:
            raise ResourcePolicyError("TSE cannot edit resources occupied by others")
        if resource.management_status != ManagementStatus.ACTIVE.value:
            raise ResourcePolicyError("TSE can only edit active resources")
    return update_resource(db, resource, payload)


def ensure_resource_not_testing(
    db: Session,
    resource: Resource,
    *,
    action: str,
) -> None:
    """阻止会破坏物理测试环境的资源写操作。"""
    if active_physical_test_usage(db, resource.id) is not None:
        raise ResourceBusyError(f"物理机正在执行测试，不能{action}")


def serialize_resources(db: Session, resources: Iterable[Resource]) -> list[ResourceRead]:
    resource_list = list(resources)
    active_leases = get_active_leases_by_resource_id(db, resource_list)
    test_usages = active_physical_test_usages(db, [resource.id for resource in resource_list])
    return [
        serialize_resource(
            db,
            resource,
            active_leases.get(resource.id),
            test_usages.get(resource.id),
        )
        for resource in resource_list
    ]


def upsert_install_image(
    db: Session,
    *,
    os_version: str,
    arch: str,
    efi_url: str,
    repo_url: str,
) -> bool:
    """按 (os_version, arch) 插入或更新物理机 PXE 安装镜像。

    新建行返回 True，更新已有行返回 False。
    """
    existing = db.execute(
        select(PhysicalInstallImage).where(
            PhysicalInstallImage.os_version == os_version,
            PhysicalInstallImage.arch == arch,
        )
    ).scalar_one_or_none()
    created = False
    if existing is None:
        db.add(
            PhysicalInstallImage(
                os_version=os_version,
                arch=arch,
                efi_url=efi_url,
                repo_url=repo_url,
            )
        )
        created = True
    else:
        existing.efi_url = efi_url
        existing.repo_url = repo_url
    db.flush()
    return created


def apply_hardware_probe(db: Session, resource: Resource, probe: dict[str, object]) -> None:
    """用探测值覆盖 resource + physical_spec 字段。

    仅当 probe 中某字段为非 None 时才覆盖，避免某子项探测失败(None)抹掉既有值。
    """
    for field in ("arch", "kernel_version", "mac_address"):
        value = probe.get(field)
        if value:
            setattr(resource, field, value)
    if resource.physical_spec is None:
        resource.physical_spec = PhysicalResourceSpec(resource_id=resource.id)
        db.add(resource.physical_spec)
    spec = resource.physical_spec
    for field in (
        "cpu_model",
        "cpu_count",
        "memory_count",
        "memory_spec",
        "hdd_count",
        "hdd_spec",
        "ssd_count",
        "ssd_spec",
        "ssd_card_count",
        "ssd_card_spec",
        "board_sn",
    ):
        value = probe.get(field)
        if value is not None:
            setattr(spec, field, value)
    db.commit()


def install_source_exists(
    db: Session, *, os_version: str, round_label: str
) -> bool:
    """公开查询：某 (os_version, round) 是否已在 94 登记本地装机源。

    供 rc_management「94 装机源」只读提示使用，避免跨模块直访 ORM。
    """
    # 轮次标签（alpha/rcN）与装机源 round 前缀匹配：rc4 → rc4_openeuler-*
    return bool(
        db.scalar(
            select(PhysicalInstallImage.id).where(
                PhysicalInstallImage.os_version == os_version,
                PhysicalInstallImage.round.like(
                    f"{round_label}\_openeuler-%", escape="\\"
                ),
            ).limit(1)
        )
    )


def get_base_kernel_variant(db: Session, os_version: str) -> str | None:
    """公开查询：发行版安装基础内核变体（install_image_base_variants）。"""
    row = db.get(InstallImageBaseVariant, os_version)
    return row.base_kernel_variant if row else None

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResourceType(StrEnum):
    """资源类型：PHYSICAL 物理机(带 BMC)、VIRTUAL 虚拟机(由 VM 模块创建)。"""

    PHYSICAL = "PHYSICAL"
    VIRTUAL = "VIRTUAL"


class ManagementStatus(StrEnum):
    """管理状态：决定资源是否允许进入租约流转。仅 active 可占用。"""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class ConnectivityStatus(StrEnum):
    """连通状态：按需探测记录的网络可达性，非实时。"""

    UNKNOWN = "unknown"
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"


class OccupancyStatus(StrEnum):
    """占用状态：资源与租约的当前关系。expired 表示租约超期待懒释放。"""

    IDLE = "idle"
    OCCUPIED = "occupied"
    EXPIRED = "expired"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Resource(Base):
    """测试资源台账主表，物理与虚拟共用。

    resource_code 是稳定业务身份(物理用 SN、虚拟用 VM UUID)，创建后不变。
    current_lease_id 指向当前未释放租约(冗余字段，真相源在 resource_leases
    的部分唯一索引)；occupancy_status 是冗余的占用快照，与租约状态需保持
    一致。软删除：deleted_at 非空即视为删除，查询一律带 deleted_at IS NULL。
    """

    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    resource_code: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    management_status: Mapped[str] = mapped_column(
        String(16),
        index=True,
        nullable=False,
        default=ManagementStatus.ACTIVE.value,
    )
    connectivity_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ConnectivityStatus.UNKNOWN.value,
    )
    occupancy_status: Mapped[str] = mapped_column(
        String(16),
        index=True,
        nullable=False,
        default=OccupancyStatus.IDLE.value,
    )
    current_lease_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    primary_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    arch: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kernel_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ssh_username: Mapped[str] = mapped_column(String(64), nullable=False)
    ssh_password_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    usage_scenario: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    physical_spec: Mapped[PhysicalResourceSpec | None] = relationship(
        back_populates="resource",
        cascade="all, delete-orphan",
        uselist=False,
    )
    virtual_spec: Mapped[VirtualResourceSpec | None] = relationship(
        back_populates="resource",
        cascade="all, delete-orphan",
        uselist=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PhysicalResourceSpec(Base):
    """物理机专属规格：BMC、CPU、内存、磁盘、板卡 SN 等。

    与 Resource 一对一，CASCADE 删除。bmc_password_ciphertext 存加密凭据。
    """

    __tablename__ = "physical_resource_specs"

    resource_id: Mapped[str] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    device_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_distribution: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bmc_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    bmc_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bmc_password_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpu_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cpu_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_spec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hdd_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hdd_spec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssd_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ssd_spec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssd_card_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ssd_card_spec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    board_sn: Mapped[str | None] = mapped_column(String(128), nullable=True)

    resource: Mapped[Resource] = relationship(back_populates="physical_spec")


class VirtualResourceSpec(Base):
    """虚拟机专属规格：vCPU/内存/磁盘/VNC 端口/宿主引用等。

    host_resource_id 指向承载该 VM 的物理资源；data_disk_paths 为列表。
    与 Resource 一对一，CASCADE 删除。
    """

    __tablename__ = "virtual_resource_specs"

    resource_id: Mapped[str] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vm_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vnc_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vnc_websocket_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vcpu_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    host_resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    system_disk_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    data_disk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_disk_size_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_disk_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    resource: Mapped[Resource] = relationship(back_populates="virtual_spec")

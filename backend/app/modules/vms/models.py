# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VMRequestStatus(StrEnum):
    """VM 申请状态机。

    pending -> creating -> succeeded/failed；pending 可 cancel -> cancelled。
    懒判断会把超过 60 分钟仍 creating 的申请标失败(只改库，不连宿主)。
    """

    PENDING = "pending"
    QUEUED = "queued"
    CREATING = "creating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VMInstallType(StrEnum):
    """VM 安装方式：auto 用镜像仓库 qcow2，manual 用用户上传的 ISO。"""

    AUTO = "auto"
    MANUAL = "manual"


def utc_now() -> datetime:
    return datetime.now(UTC)


class VMRequest(Base):
    """VM 创建申请记录。

    承载申请规格(规格/镜像/磁盘)与执行结果(resource_id/task_id/错误)。
    host_attempts 追加每次宿主尝试，用于失败定位。状态机见 VMRequestStatus。
    """

    __tablename__ = "vm_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    requester_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=VMRequestStatus.PENDING.value,
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    expected_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    dist: Mapped[str] = mapped_column(String(64), nullable=False)
    os_version: Mapped[str] = mapped_column(String(128), nullable=False)
    image_round: Mapped[str] = mapped_column(String(64), nullable=False)
    arch: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    kernel_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kernel_variant: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kernel_rpm_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    install_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=VMInstallType.AUTO.value,
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)

    vcpu_count: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    disk_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    data_disk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_disk_size_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    extra_nic_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    resource_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    host_resource_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_attempts: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

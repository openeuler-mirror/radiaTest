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
from uuid import uuid4

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PhysicalInstallImage(Base):
    """物理机 PXE 安装镜像。ADMIN 手动维护（本地镜像源由登记扫描回填）。

    - official：`efi_url + repo_url`（安装源 = 94 本地 OS 树）。
    - RC（dailybuild 开发版）：`repo_url` 由本地源登记指向本地 OS 树；
      变体自身树存在 → 直接装该树；变体树缺失 → repo_url=基础树，
      `swap_kernel_variant` 记录装后换内核目标（full 变体目录名，如
      `26.09-with-kernel-6.18`），None 表示不换。
    - `iso_url` 保留仅作展示，不再作为安装源（不向 PXE 服务器下载 ISO）。
    """

    __tablename__ = "physical_install_images"
    __table_args__ = (
        UniqueConstraint(
            "os_version",
            "arch",
            "round",
            "kernel_variant",
            name="uq_pii_os_arch_round_kernel",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    os_version: Mapped[str] = mapped_column(String(64), nullable=False)
    arch: Mapped[str] = mapped_column(String(32), nullable=False)
    efi_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    round: Mapped[str | None] = mapped_column(String(64), nullable=True)
    iso_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    kernel_variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    swap_kernel_variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class InstallImageBaseVariant(Base):
    """发行版安装基础内核变体（前端 ADMIN 可编辑）。

    登记扫描时作为"缺树变体"的兜底安装源基础；`base_kernel_variant` 存内核
    版本号（如 ``6.6``），目录匹配按 ``*-with-kernel-<base_kernel_variant>`` 后缀。
    """

    __tablename__ = "install_image_base_variants"

    os_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    base_kernel_variant: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

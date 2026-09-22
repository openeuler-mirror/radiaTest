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

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VersionStatus(StrEnum):
    """版本状态：测试中 / 已结束。"""

    TESTING = "testing"
    FINISHED = "finished"


class CompareKind(StrEnum):
    """比对内容（对应交付 7 文件的两大维度之一）：

    - binary：轮次间同 name.arch 的二进制包对比；
    - source：轮次间 src rpm 对比；
    - isomer：同一轮内 x86_64 vs aarch64 同名包（同名异构）；
    - repeat：同名同架构多版本并存（重复包）。
    """

    BINARY = "binary"
    SOURCE = "source"
    ISOMER = "isomer"
    REPEAT = "repeat"


class CompareStatus(StrEnum):
    """比对任务实例状态：pending / running / succeeded / failed。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Version(Base):
    """版本：RC 版本测试的长期对象（如 openEuler-26.09-DevStation）。

    由迁移从 physical_install_images 去重 os_version 回填；版本只承载元信息，
    不参与 PXE 装配（装机源仍在 physical_install_images，与比对隔离）。
    """

    __tablename__ = "versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # name 与 physical_install_images.os_version 同约定（带 openEuler- 前缀）
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    version_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=VersionStatus.TESTING.value
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    milestones: Mapped[list["ReleaseMilestone"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class ReleaseMilestone(Base):
    """RC 里程碑（轮次）：挂在版本下，一个轮次是后续测试活动（比对/引例/模块）的载体。

    build_url 为比对构建根 URL（121.36.84.172/dailybuild/EBS-<product>/…）；程序据此
    拼 everything / EPOL/main / source 及各架构清单。pxe_round_label 从 build_url 自动
    推导（如 rc4_openeuler-2026-09-07-…），用于“94 是否有装机源”只读提示，不参与 PXE。
    """

    __tablename__ = "milestones"
    __table_args__ = (
        UniqueConstraint("version_id", "name", name="uq_milestones_version_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(
        ForeignKey("versions.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    kernel_variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    build_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pxe_round_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    compare_base_milestone_id: Mapped[str | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    version: Mapped["Version"] = relationship(back_populates="milestones")


class MilestoneCompare(Base):
    """软件包比对任务实例：一次比对一条，可回溯历史。

    同 (milestone, base) 允许多次实例（决策 7）；页面用最新实例做汇总。
    """

    __tablename__ = "rc_milestone_compares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    milestone_id: Mapped[str] = mapped_column(
        ForeignKey("milestones.id"), index=True, nullable=False
    )
    base_milestone_id: Mapped[str] = mapped_column(
        ForeignKey("milestones.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CompareStatus.PENDING.value
    )
    total_changed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PackageCompareResult(Base):
    """比对结果行：只存非 SAME 变更行（决策 8）。

    pkg_name 为 spec 裸包名（不是 name.arch），作为下一期 mugen 用例匹配键
    （MugenCase.suite_name == pkg_name）；repeat 行展示用存 name.arch。
    rpm_base / rpm_target：binary/source/repeat 为基准/目标轮 rpm 文件名
    （repeat 为多行 \n 拼接）；isomer 为 rpm_x86 / rpm_arm。
    """

    __tablename__ = "rc_package_compare_results"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    compare_id: Mapped[str] = mapped_column(
        ForeignKey("rc_milestone_compares.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    repo_path: Mapped[str] = mapped_column(String(32), nullable=False)
    pkg_name: Mapped[str] = mapped_column(String(255), nullable=False)
    arch: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    rpm_base: Mapped[str | None] = mapped_column(Text, nullable=True)
    rpm_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        # 组合索引支撑 results 接口按 compare_id + kind/repo/arch/status 筛选
        Index(
            "ix_rc_results_compare_kind_repo",
            "compare_id",
            "kind",
            "repo_path",
            "arch",
            "status",
        ),
    )

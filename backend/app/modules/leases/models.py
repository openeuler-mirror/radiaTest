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

from sqlalchemy import JSON, DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LeaseEventType(StrEnum):
    """租约事件类型，写入 lease_events.event_type，用于租约日志回溯与页面详情。"""

    OCCUPY = "occupy"
    EXTEND = "extend"
    RELEASE = "release"
    FORCE_RELEASE = "force_release"
    AUTO_RELEASE = "auto_release"


def utc_now() -> datetime:
    return datetime.now(UTC)


class ResourceLease(Base):
    """资源租约：某用户在一段时间内占用资源的记录。

    不可破坏约束：同一资源同一时刻至多一条未释放租约，由
    uq_resource_leases_active_resource 部分唯一索引(released_at IS NULL)在
    数据库层保证，占用/释放的并发安全以此为最终防线。普通用户租约有
    expected_ends_at，ADMIN 可置 None 表示永久租约。
    """

    __tablename__ = "resource_leases"
    __table_args__ = (
        # 部分唯一索引：仅约束未释放的租约，允许同一资源的历史租约多行共存。
        Index(
            "uq_resource_leases_active_resource",
            "resource_id",
            unique=True,
            postgresql_where=text("released_at IS NULL"),
            sqlite_where=text("released_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    resource_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expected_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    released_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class LeaseEvent(Base):
    """租约事件流：占用/续期/释放/强制释放/懒释放的追加写入记录，用于审计回溯。"""

    __tablename__ = "lease_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lease_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    detail: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

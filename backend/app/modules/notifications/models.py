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

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationType(StrEnum):
    """通知类型，写入 notification_type，决定标题模板与投递渠道。"""

    LEASE_EXPIRING = "lease.expiring"
    TICKET_COMMENTED = "ticket.commented"
    TICKET_ASSIGNED = "ticket.assigned"
    TICKET_REASSIGNED = "ticket.reassigned"
    TICKET_REJECTED = "ticket.rejected"
    TICKET_COMPLETED = "ticket.completed"
    TICKET_UPDATED = "ticket.updated"


class NotificationTargetType(StrEnum):
    """通知指向的目标类型，用于拼接前端跳转 URL。"""

    TICKET = "ticket"
    VIRTUAL_MACHINE = "virtual_machine"
    PHYSICAL_RESOURCE = "physical_resource"


class FeishuDeliveryStatus(StrEnum):
    """飞书投递状态机：PENDING(待发) → SENT，或 PENDING → FAILED。"""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Notification(Base):
    """站内通知，可选附带飞书投递。

    幂等去重靠 deduplication_key 唯一约束：同一事件对同一接收人只产一条，
    防止重试或重复触发产生重复通知。feishu_status 为空表示不投递飞书
    (接收人未绑定飞书身份)。
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "ix_notifications_recipient_read_created",
            "recipient_user_id",
            "read_at",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    recipient_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    deduplication_key: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    feishu_status: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        index=True,
    )
    feishu_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    feishu_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

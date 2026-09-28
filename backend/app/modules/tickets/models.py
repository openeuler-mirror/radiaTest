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

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TicketType(StrEnum):
    """工单类型：REQ(需求)/BUG(缺陷)，提交后不可变。"""

    REQ = "REQ"
    BUG = "BUG"


class TicketStatus(StrEnum):
    """工单状态机：PENDING → ACCEPTED → COMPLETED，或 PENDING → REJECTED。

    受理/拒绝/完成等状态转换由 commands 层用乐观并发(expected_status)保证，
    只允许从指定前序状态转入，防止并发操作跳变。
    """

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class TicketPriority(StrEnum):
    """工单优先级，可为空(UNSET)，受理时由管理员设定。"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Ticket(Base):
    """工单：用户提交的需求/缺陷单，带状态机、优先级与责任人。

    生命周期关键时间点：planned_completion_at(受理时设定的计划完成时间，
    用于判定 is_overdue)与 completed_at(实际完成时间)。rejection_reason 在
    拒绝时写入并带上处理人前缀。
    """

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    submitter_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    ticket_type: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        index=True,
        nullable=False,
        default=TicketStatus.PENDING.value,
    )
    priority: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    assignee_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=True,
    )
    planned_completion_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class TicketComment(Base):
    """工单评论，随工单级联删除(ondelete CASCADE)。作者须为管理员、提出人或责任人。"""

    __tablename__ = "ticket_comments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    author_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

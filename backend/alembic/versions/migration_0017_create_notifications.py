# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create notifications

Revision ID: 20260717_0017
Revises: 20260716_0016
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260728_0028"
down_revision: str | None = "20260728_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=36), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("target_url", sa.String(length=512), nullable=True),
        sa.Column("deduplication_key", sa.String(length=512), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feishu_status", sa.String(length=16), nullable=True),
        sa.Column("feishu_error", sa.Text(), nullable=True),
        sa.Column("feishu_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_key"),
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["recipient_user_id", "read_at", "created_at"],
    )
    op.create_index(
        op.f("ix_notifications_created_at"),
        "notifications",
        ["created_at"],
    )
    op.create_index(
        op.f("ix_notifications_feishu_status"),
        "notifications",
        ["feishu_status"],
    )
    op.create_index(
        op.f("ix_notifications_notification_type"),
        "notifications",
        ["notification_type"],
    )
    op.create_index(
        op.f("ix_notifications_read_at"),
        "notifications",
        ["read_at"],
    )
    op.create_index(
        op.f("ix_notifications_recipient_user_id"),
        "notifications",
        ["recipient_user_id"],
    )


def downgrade() -> None:
    op.drop_table("notifications")

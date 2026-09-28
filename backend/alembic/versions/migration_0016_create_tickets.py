# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create tickets

Revision ID: 20260716_0016
Revises: 20260715_0015
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260728_0027"
down_revision: str | None = "20260715_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), sa.Identity(start=1), nullable=False),
        sa.Column("submitter_user_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_type", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=True),
        sa.Column("assignee_user_id", sa.String(length=36), nullable=True),
        sa.Column("planned_completion_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submitter_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_assignee_user_id"), "tickets", ["assignee_user_id"])
    op.create_index(
        op.f("ix_tickets_planned_completion_at"),
        "tickets",
        ["planned_completion_at"],
    )
    op.create_index(op.f("ix_tickets_priority"), "tickets", ["priority"])
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"])
    op.create_index(op.f("ix_tickets_submitter_user_id"), "tickets", ["submitter_user_id"])
    op.create_index(op.f("ix_tickets_ticket_type"), "tickets", ["ticket_type"])

    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.String(length=36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_comments_author_user_id"),
        "ticket_comments",
        ["author_user_id"],
    )
    op.create_index(
        op.f("ix_ticket_comments_ticket_id"),
        "ticket_comments",
        ["ticket_id"],
    )


def downgrade() -> None:
    op.drop_table("ticket_comments")
    op.drop_table("tickets")

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create resource leases

Revision ID: 20260629_0005
Revises: 20260629_0004
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260629_0005"
down_revision: str | None = "20260629_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resource_leases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("release_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_resource_leases_expected_ends_at"),
        "resource_leases",
        ["expected_ends_at"],
    )
    op.create_index(op.f("ix_resource_leases_released_at"), "resource_leases", ["released_at"])
    op.create_index(op.f("ix_resource_leases_resource_id"), "resource_leases", ["resource_id"])
    op.create_index(op.f("ix_resource_leases_user_id"), "resource_leases", ["user_id"])
    op.create_index(
        "uq_resource_leases_active_resource",
        "resource_leases",
        ["resource_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )

    op.create_table(
        "lease_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lease_id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lease_events_actor_user_id"), "lease_events", ["actor_user_id"])
    op.create_index(op.f("ix_lease_events_event_type"), "lease_events", ["event_type"])
    op.create_index(op.f("ix_lease_events_lease_id"), "lease_events", ["lease_id"])
    op.create_index(op.f("ix_lease_events_resource_id"), "lease_events", ["resource_id"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_user_id",
            "method",
            "path",
            "idempotency_key",
            name="uq_idempotency_records_scope",
        ),
    )
    op.add_column("resources", sa.Column("current_lease_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_resources_current_lease_id"), "resources", ["current_lease_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_resources_current_lease_id"), table_name="resources")
    op.drop_column("resources", "current_lease_id")
    op.drop_table("idempotency_records")
    op.drop_index(op.f("ix_lease_events_resource_id"), table_name="lease_events")
    op.drop_index(op.f("ix_lease_events_lease_id"), table_name="lease_events")
    op.drop_index(op.f("ix_lease_events_event_type"), table_name="lease_events")
    op.drop_index(op.f("ix_lease_events_actor_user_id"), table_name="lease_events")
    op.drop_table("lease_events")
    op.drop_index(op.f("ix_resource_leases_user_id"), table_name="resource_leases")
    op.drop_index("uq_resource_leases_active_resource", table_name="resource_leases")
    op.drop_index(op.f("ix_resource_leases_resource_id"), table_name="resource_leases")
    op.drop_index(op.f("ix_resource_leases_released_at"), table_name="resource_leases")
    op.drop_index(op.f("ix_resource_leases_expected_ends_at"), table_name="resource_leases")
    op.drop_table("resource_leases")

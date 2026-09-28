# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create feishu integration tables

Revision ID: 20260707_0009
Revises: 20260702_0008
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260707_0009"
down_revision: str | None = "20260702_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feishu_app_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=128), nullable=False),
        sa.Column("app_secret", sa.String(length=512), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("environment", name="uq_feishu_app_configs_environment"),
    )
    op.create_index(
        op.f("ix_feishu_app_configs_created_by_user_id"),
        "feishu_app_configs",
        ["created_by_user_id"],
    )
    op.create_index(
        op.f("ix_feishu_app_configs_environment"),
        "feishu_app_configs",
        ["environment"],
    )

    op.create_table(
        "user_identities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("open_id", sa.String(length=128), nullable=False),
        sa.Column("union_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "open_id", name="uq_user_identities_provider_open_id"),
        sa.UniqueConstraint("provider", "union_id", name="uq_user_identities_provider_union_id"),
        sa.UniqueConstraint("provider", "user_id", name="uq_user_identities_provider_user"),
    )
    op.create_index(op.f("ix_user_identities_open_id"), "user_identities", ["open_id"])
    op.create_index(op.f("ix_user_identities_provider"), "user_identities", ["provider"])
    op.create_index(op.f("ix_user_identities_union_id"), "user_identities", ["union_id"])
    op.create_index(op.f("ix_user_identities_user_id"), "user_identities", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_user_identities_user_id"), table_name="user_identities")
    op.drop_index(op.f("ix_user_identities_union_id"), table_name="user_identities")
    op.drop_index(op.f("ix_user_identities_provider"), table_name="user_identities")
    op.drop_index(op.f("ix_user_identities_open_id"), table_name="user_identities")
    op.drop_table("user_identities")
    op.drop_index(
        op.f("ix_feishu_app_configs_environment"),
        table_name="feishu_app_configs",
    )
    op.drop_index(
        op.f("ix_feishu_app_configs_created_by_user_id"),
        table_name="feishu_app_configs",
    )
    op.drop_table("feishu_app_configs")

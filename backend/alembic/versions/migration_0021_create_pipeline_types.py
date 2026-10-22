# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create pipeline_types table

Revision ID: 20260721_0021
Revises: 20260720_0020
Create Date: 2026-07-21

Adds the `pipeline_types` table that drives pipeline type registration. Seeded
with two system types (`update` A-class code-driven, `release` B-class
data-driven). `pipeline_configs.pipeline_type` is a logical FK to
`pipeline_types.name` (no physical FK constraint, so deleting a user-created
type with no configs left doesn't cascade). See ADR 0010.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260721_0021"
down_revision: str | None = "20260720_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column(
            "strategy_kind",
            sa.String(64),
            nullable=False,
            server_default="direct_run",
        ),
        sa.Column(
            "test_framework", sa.String(64), nullable=False, server_default="mugen"
        ),
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "default_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_pipeline_types_name", "pipeline_types", ["name"], unique=True
    )
    op.create_index(
        "ix_pipeline_types_strategy_kind", "pipeline_types", ["strategy_kind"]
    )

    # Seed system types (idempotent: INSERT ... ON CONFLICT DO NOTHING).
    op.execute(
        """
        INSERT INTO pipeline_types (
            id, name, display_name, strategy_kind,
            test_framework, is_system, default_config,
            created_at, updated_at
        )
        VALUES
            (
                gen_random_uuid()::text, 'update', 'Update 测试流水线',
                'update_strategy', 'mugen', true, '{}'::json,
                now(), now()
            ),
            (
                gen_random_uuid()::text, 'release', 'Release 测试流水线',
                'direct_run', 'mugen', true, '{}'::json,
                now(), now()
            )
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_types_strategy_kind", table_name="pipeline_types")
    op.drop_index("ix_pipeline_types_name", table_name="pipeline_types")
    op.drop_table("pipeline_types")

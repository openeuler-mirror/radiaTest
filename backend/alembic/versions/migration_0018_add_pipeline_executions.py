# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add pipeline_executions table and execution_id on runs

Revision ID: 20260717_0018
Revises: 20260717_0017
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260717_0018"
down_revision: str | None = "20260717_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "config_id",
            sa.String(36),
            sa.ForeignKey("update_pipeline_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("triggered_by", sa.String(64), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("versions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("archs", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_pipeline_executions_config_id",
        "pipeline_executions",
        ["config_id"],
    )
    op.create_index(
        "ix_pipeline_executions_status",
        "pipeline_executions",
        ["status"],
    )

    op.add_column(
        "update_pipeline_runs",
        sa.Column(
            "execution_id",
            sa.String(36),
            sa.ForeignKey("pipeline_executions.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_update_pipeline_runs_execution_id",
        "update_pipeline_runs",
        ["execution_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_update_pipeline_runs_execution_id",
        table_name="update_pipeline_runs",
    )
    op.drop_column("update_pipeline_runs", "execution_id")
    op.drop_index("ix_pipeline_executions_status", table_name="pipeline_executions")
    op.drop_index("ix_pipeline_executions_config_id", table_name="pipeline_executions")
    op.drop_table("pipeline_executions")

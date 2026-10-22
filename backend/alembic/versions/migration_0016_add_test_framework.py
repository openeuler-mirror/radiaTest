# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add test_framework and pipeline_run_node_infos

Revision ID: 20260716_0016
Revises: 20260716_0015
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260716_0016"
down_revision: str | None = "20260716_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE test_module_templates ADD COLUMN IF NOT EXISTS "
        "test_framework VARCHAR(64) NOT NULL DEFAULT 'mugen'"
    )
    op.execute(
        "ALTER TABLE update_pipeline_configs ADD COLUMN IF NOT EXISTS "
        "test_framework VARCHAR(64) NOT NULL DEFAULT 'mugen'"
    )

    _bind = op.get_bind()
    if not sa.inspect(_bind).has_table("pipeline_run_node_infos"):
        op.create_table(
            "pipeline_run_node_infos",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "run_job_id",
                sa.String(36),
                sa.ForeignKey("update_pipeline_run_jobs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("resource_id", sa.String(36), nullable=True),
            sa.Column("resource_code", sa.String(128), nullable=True),
            sa.Column("primary_ip", sa.String(64), nullable=True),
            sa.Column("role", sa.String(32), nullable=True),
            sa.Column("env_set_index", sa.Integer(), nullable=True),
            sa.Column("node_index", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_pipeline_run_node_infos_run_job_id",
            "pipeline_run_node_infos",
            ["run_job_id"],
        )
        op.create_index(
            "ix_pipeline_run_node_infos_resource_id",
            "pipeline_run_node_infos",
            ["resource_id"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_pipeline_run_node_infos_resource_id",
        table_name="pipeline_run_node_infos",
    )
    op.drop_index(
        "ix_pipeline_run_node_infos_run_job_id",
        table_name="pipeline_run_node_infos",
    )
    op.drop_table("pipeline_run_node_infos")
    op.drop_column("update_pipeline_configs", "test_framework")
    op.drop_column("test_module_templates", "test_framework")

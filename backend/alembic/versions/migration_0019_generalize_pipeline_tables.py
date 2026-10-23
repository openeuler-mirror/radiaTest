# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""generalize pipeline tables (drop update_ prefix) and add columns

Revision ID: 20260720_0019
Revises: 20260717_0018
Create Date: 2026-07-20

Renames update_pipeline_* tables to pipeline_* (pipeline is a general capability,
update is the first pipeline_type), adds pipeline_configs.pipeline_type,
test_jobs.keep_env and test_jobs.result_parser.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260720_0019"
down_revision: str | None = "20260717_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename tables: drop update_ prefix (pipeline is general, update is a type)
    op.rename_table("update_pipeline_configs", "pipeline_configs")
    op.rename_table("update_pipeline_runs", "pipeline_runs")
    op.rename_table("update_pipeline_run_jobs", "pipeline_run_jobs")

    # pipeline_configs.pipeline_type (default update; release etc. later)
    op.add_column(
        "pipeline_configs",
        sa.Column(
            "pipeline_type",
            sa.String(64),
            nullable=False,
            server_default="update",
        ),
    )
    op.create_index(
        "ix_pipeline_configs_pipeline_type",
        "pipeline_configs",
        ["pipeline_type"],
    )
    # pipeline_configs.dist / image_round (VM 镜像发现需要)
    op.add_column(
        "pipeline_configs",
        sa.Column("dist", sa.String(64), nullable=False, server_default="openEuler"),
    )
    op.add_column(
        "pipeline_configs",
        sa.Column("image_round", sa.String(64), nullable=False, server_default=""),
    )

    # test_jobs.keep_env (全保留环境, pipeline 用)
    op.add_column(
        "test_jobs",
        sa.Column(
            "keep_env",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # test_jobs.result_parser (run_case 按此选解析器, builder 从模板复制)
    op.add_column(
        "test_jobs",
        sa.Column("result_parser", sa.String(64), nullable=True),
    )

    # pipeline_executions.status server_default pending (read-time 聚合, 初始 pending)
    op.alter_column(
        "pipeline_executions",
        "status",
        server_default="pending",
    )


def downgrade() -> None:
    op.alter_column(
        "pipeline_executions",
        "status",
        server_default="running",
    )
    op.drop_column("test_jobs", "result_parser")
    op.drop_column("test_jobs", "keep_env")
    op.drop_column("pipeline_configs", "image_round")
    op.drop_column("pipeline_configs", "dist")
    op.drop_index(
        "ix_pipeline_configs_pipeline_type",
        table_name="pipeline_configs",
    )
    op.drop_column("pipeline_configs", "pipeline_type")
    op.rename_table("pipeline_run_jobs", "update_pipeline_run_jobs")
    op.rename_table("pipeline_runs", "update_pipeline_runs")
    op.rename_table("pipeline_configs", "update_pipeline_configs")

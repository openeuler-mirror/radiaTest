# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add Pipeline RunJob rerun linkage

Revision ID: 20260827_0034
Revises: 20260827_0033
Create Date: 2026-08-27
"""

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0034"
down_revision: str | None = "20260827_0033"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    for column in ("rerun_source_run_job_id", "rerun_root_run_job_id"):
        op.add_column("pipeline_run_jobs", sa.Column(column, sa.String(36), nullable=True))
        op.create_index(f"ix_pipeline_run_jobs_{column}", "pipeline_run_jobs", [column])
        op.create_foreign_key(
            f"fk_pipeline_run_jobs_{column}",
            "pipeline_run_jobs",
            "pipeline_run_jobs",
            [column],
            ["id"],
            ondelete="SET NULL",
        )
    op.add_column(
        "pipeline_run_jobs",
        sa.Column(
            "rerun_case_selections",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.alter_column("pipeline_run_jobs", "rerun_case_selections", server_default=None)


def downgrade() -> None:
    op.drop_column("pipeline_run_jobs", "rerun_case_selections")
    for column in ("rerun_root_run_job_id", "rerun_source_run_job_id"):
        op.drop_constraint(
            f"fk_pipeline_run_jobs_{column}", "pipeline_run_jobs", type_="foreignkey"
        )
        op.drop_index(f"ix_pipeline_run_jobs_{column}", table_name="pipeline_run_jobs")
        op.drop_column("pipeline_run_jobs", column)

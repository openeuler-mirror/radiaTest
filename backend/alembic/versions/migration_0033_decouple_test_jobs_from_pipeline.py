# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""decouple Test Job execution state from Pipeline

Revision ID: 20260827_0033
Revises: 20260819_0032
Create Date: 2026-08-27

PipelineRunJob already owns the Test Job reference. Copy the only execution
input Test Job previously resolved from Pipeline into its own snapshot, then
remove the reverse Test Job to Pipeline RunJob link.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0033"
down_revision: str | None = "20260819_0032"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "test_jobs",
        sa.Column("physical_usage_scenario", sa.String(length=128), nullable=True),
    )
    # pipeline_run_job_id 由 20260716_0015 加入，但 20260715_0015 重建 test_jobs 时
    # 未保留该列；在全新库按迁移链 upgrade 时，此处列已不存在。仅当列仍在时回填并
    # 清理，全新库本就无数据可回填，跳过即可。已迁移过的库不会重跑本步。
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("test_jobs")}
    if "pipeline_run_job_id" not in columns:
        return
    op.execute(
        """
        UPDATE test_jobs AS job
        SET physical_usage_scenario = template.name || '-update'
        FROM pipeline_run_jobs AS run_job
        JOIN test_module_templates AS template
          ON template.id = run_job.module_template_id
        WHERE job.pipeline_run_job_id = run_job.id
        """
    )
    indexes = {idx["name"] for idx in inspector.get_indexes("test_jobs")}
    if "ix_test_jobs_pipeline_run_job_id" in indexes:
        op.drop_index("ix_test_jobs_pipeline_run_job_id", table_name="test_jobs")
    op.drop_column("test_jobs", "pipeline_run_job_id")


def downgrade() -> None:
    op.add_column(
        "test_jobs",
        sa.Column("pipeline_run_job_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_test_jobs_pipeline_run_job_id",
        "test_jobs",
        ["pipeline_run_job_id"],
        unique=False,
    )
    op.execute(
        """
        UPDATE test_jobs AS job
        SET pipeline_run_job_id = run_job.id
        FROM pipeline_run_jobs AS run_job
        WHERE run_job.test_job_id = job.id
        """
    )
    op.drop_column("test_jobs", "physical_usage_scenario")

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""align test_log_artifacts.job_id to integer

Revision ID: 20260728_0031
Revises: 20260728_0030
Create Date: 2026-08-14

TestLogArtifact.job_id stores TestJob.id, which is Integer (Identity).
Migration 0030 aligned pipeline_run_jobs.test_job_id to integer but missed
test_log_artifacts.job_id, leaving it as String(36). The _self_collect_logs
query (TestLogArtifact.job_id == job.id) compares VARCHAR with INTEGER,
triggering "operator does not exist" errors on PostgreSQL.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "20260728_0031"
down_revision: str | None = "20260728_0030"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "test_log_artifacts",
        "job_id",
        existing_type=sa.String(length=36),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="job_id::integer",
    )


def downgrade() -> None:
    op.alter_column(
        "test_log_artifacts",
        "job_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=36),
        existing_nullable=False,
        postgresql_using="job_id::text",
    )

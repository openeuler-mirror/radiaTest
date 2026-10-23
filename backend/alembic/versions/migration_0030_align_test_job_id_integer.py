# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""align pipeline_run_jobs.test_job_id to integer

Revision ID: 20260728_0030
Revises: 20260728_0029
Create Date: 2026-08-12

TestJob.id is Integer (Identity), so the foreign-key-shaped
PipelineRunJob.test_job_id must also be Integer to match. air9's original
create migration (0015) declared it String(36) when TestJob.id was a UUID
string; the merged model kept feature's Integer TestJob.id, so this column
is aligned here to avoid int-vs-str mismatches in get_case_mugen_log and
related joins.
"""


import sqlalchemy as sa

from alembic import op

revision: str = "20260728_0030"
down_revision: str | None = "20260728_0029"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "pipeline_run_jobs",
        "test_job_id",
        existing_type=sa.String(length=36),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="test_job_id::integer",
    )


def downgrade() -> None:
    op.alter_column(
        "pipeline_run_jobs",
        "test_job_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=36),
        existing_nullable=True,
        postgresql_using="test_job_id::text",
    )

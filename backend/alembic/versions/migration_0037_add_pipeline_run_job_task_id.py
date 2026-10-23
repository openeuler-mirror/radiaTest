# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""track Pipeline RunJob Celery tasks

Revision ID: 20260903_0037
Revises: 20260828_0036
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0037"
down_revision: str | None = "20260828_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_run_jobs",
        sa.Column("task_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_pipeline_run_jobs_task_id",
        "pipeline_run_jobs",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_jobs_task_id", table_name="pipeline_run_jobs")
    op.drop_column("pipeline_run_jobs", "task_id")

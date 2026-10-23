# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add cancel_requested to pipeline_run_jobs and test_jobs

Revision ID: 20260903_0038
Revises: 20260903_0037
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0038"
down_revision: str | None = "20260903_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_run_jobs",
        sa.Column(
            "cancel_requested", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "test_jobs",
        sa.Column(
            "cancel_requested", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("pipeline_run_jobs", "cancel_requested")
    op.drop_column("test_jobs", "cancel_requested")

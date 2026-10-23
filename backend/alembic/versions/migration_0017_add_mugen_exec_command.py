# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add mugen_exec_command to module templates and test jobs

Revision ID: 20260717_0017
Revises: 20260716_0016
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260717_0017"
down_revision: str | None = "20260716_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_module_templates",
        sa.Column("mugen_exec_command", sa.Text(), nullable=True),
    )
    op.add_column(
        "test_jobs",
        sa.Column("mugen_exec_command", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_jobs", "mugen_exec_command")
    op.drop_column("test_module_templates", "mugen_exec_command")

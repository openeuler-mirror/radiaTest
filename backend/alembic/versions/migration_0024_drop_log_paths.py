# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""drop log_paths from test_module_templates

Revision ID: 20260723_0024
Revises: 20260721_0023
Create Date: 2026-07-23

The `log_paths` column was a vestigial design artifact — stored in DB but
never read by any code. The actual log collection (`_self_collect_logs`)
does `ls -1F /tmp/module-logs/` and collects everything, ignoring
`log_paths`. Drop the column to avoid confusion.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260723_0024"
down_revision: str | None = "20260721_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("test_module_templates", "log_paths")


def downgrade() -> None:
    op.add_column(
        "test_module_templates",
        sa.Column("log_paths", sa.JSON(), nullable=False, server_default="[]"),
    )

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""simplify resource identity fields

Revision ID: 20260630_0006
Revises: 20260629_0005
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260630_0006"
down_revision: str | None = "20260629_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("resources", "name", existing_type=sa.String(length=128), nullable=True)
    op.drop_column("resources", "description")
    op.drop_column("physical_resource_specs", "system_sn")


def downgrade() -> None:
    op.add_column(
        "physical_resource_specs",
        sa.Column("system_sn", sa.String(length=128), nullable=True),
    )
    op.add_column("resources", sa.Column("description", sa.Text(), nullable=True))
    op.execute("UPDATE resources SET name = resource_code WHERE name IS NULL")
    op.alter_column("resources", "name", existing_type=sa.String(length=128), nullable=False)

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add vm install type

Revision ID: 20260710_0010
Revises: 20260707_0009
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260710_0010"
down_revision: str | None = "20260707_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "resources",
        "primary_ip",
        existing_type=sa.String(length=64),
        nullable=True,
    )
    op.add_column(
        "vm_requests",
        sa.Column(
            "install_type",
            sa.String(length=16),
            nullable=False,
            server_default="auto",
        ),
    )
    op.alter_column("vm_requests", "install_type", server_default=None)


def downgrade() -> None:
    op.drop_column("vm_requests", "install_type")
    op.execute("UPDATE resources SET primary_ip = '' WHERE primary_ip IS NULL")
    op.alter_column(
        "resources",
        "primary_ip",
        existing_type=sa.String(length=64),
        nullable=False,
    )

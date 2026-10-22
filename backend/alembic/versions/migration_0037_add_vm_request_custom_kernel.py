# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add kernel_variant/kernel_rpm_url to vm_requests for custom kernel swap

Revision ID: 20260901_0037
Revises: 20260828_0036
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0037"
down_revision: str | None = "20260828_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vm_requests",
        sa.Column("kernel_variant", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "vm_requests",
        sa.Column("kernel_rpm_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vm_requests", "kernel_rpm_url")
    op.drop_column("vm_requests", "kernel_variant")

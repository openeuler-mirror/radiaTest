# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""harden idempotency records

Revision ID: 20260717_0018
Revises: 20260717_0017
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260728_0029"
down_revision: str | None = "20260728_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "idempotency_records",
        sa.Column("state", sa.String(length=16), server_default="completed", nullable=False),
    )
    op.alter_column("idempotency_records", "status_code", existing_type=sa.Integer(), nullable=True)
    op.alter_column("idempotency_records", "response_body", existing_type=sa.JSON(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM idempotency_records WHERE state != 'completed'")
    op.alter_column("idempotency_records", "response_body", existing_type=sa.JSON(), nullable=False)
    op.alter_column(
        "idempotency_records",
        "status_code",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("idempotency_records", "state")

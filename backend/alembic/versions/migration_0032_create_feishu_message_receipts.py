# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create Feishu message receipts for inbound message deduplication

Revision ID: 20260819_0032
Revises: 20260728_0031
Create Date: 2026-08-19
"""

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0032"
down_revision: str | None = "20260728_0031"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "feishu_message_receipts",
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_index(
        "ix_feishu_message_receipts_created_at",
        "feishu_message_receipts",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_feishu_message_receipts_created_at",
        table_name="feishu_message_receipts",
    )
    op.drop_table("feishu_message_receipts")

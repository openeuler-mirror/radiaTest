# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""milestones.build_url 允许为空（自动生成的轮次骨架后补构建 URL）

Revision ID: 20260910_0046
Revises: 20260910_0044
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0046"
down_revision: str | None = "20260910_0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "milestones",
        "build_url",
        existing_type=sa.String(1024),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("DELETE FROM milestones WHERE build_url IS NULL")
    op.alter_column(
        "milestones",
        "build_url",
        existing_type=sa.String(1024),
        nullable=False,
    )

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""replace env_type_split bool with env_type (vm/physical/both)

Revision ID: 20260725_0025
Revises: 20260724_0025
Create Date: 2026-07-25

The ``env_type_split`` bool (True=both, False=vm) could not express
"physical only". Replaced by ``env_type`` (vm/physical/both). kernel was
misconfigured (env_type_split=False -> vm) but kernel must run on physical
only; backfill kernel -> physical.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260725_0025"
down_revision: str | None = "20260724_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_module_templates",
        sa.Column("env_type", sa.String(length=16), nullable=False, server_default="vm"),
    )
    op.execute(
        "UPDATE test_module_templates SET env_type = CASE "
        "WHEN name = 'kernel' THEN 'physical' "
        "WHEN env_type_split = true THEN 'both' "
        "ELSE 'vm' END"
    )
    op.drop_column("test_module_templates", "env_type_split")


def downgrade() -> None:
    op.add_column(
        "test_module_templates",
        sa.Column(
            "env_type_split", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.execute("UPDATE test_module_templates SET env_type_split = (env_type = 'both')")
    op.drop_column("test_module_templates", "env_type")

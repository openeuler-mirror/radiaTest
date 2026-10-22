# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""rename mugen_suite to suite_name and add pipeline_type to test_module_templates

Revision ID: 20260721_0023
Revises: 20260721_0022
Create Date: 2026-07-21

Renames `test_module_templates.mugen_suite` → `suite_name` (framework-agnostic,
aligns with `MugenCase.suite_name`). Adds `pipeline_type` column (default 'update')
for UI partitioning by pipeline type. Backfills existing `release-*` templates
with `pipeline_type='release'`. See ADR 0012.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260721_0023"
down_revision: str | None = "20260721_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. rename mugen_suite → suite_name
    op.alter_column(
        "test_module_templates",
        "mugen_suite",
        new_column_name="suite_name",
    )
    # 2. add pipeline_type column (default 'update')
    op.add_column(
        "test_module_templates",
        sa.Column(
            "pipeline_type",
            sa.String(64),
            nullable=False,
            server_default="update",
        ),
    )
    op.create_index(
        "ix_test_module_templates_pipeline_type",
        "test_module_templates",
        ["pipeline_type"],
    )
    # 3. backfill: templates named 'release-*' get pipeline_type='release'
    op.execute(
        """
        UPDATE test_module_templates
        SET pipeline_type = 'release'
        WHERE name LIKE 'release-%'
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_test_module_templates_pipeline_type",
        table_name="test_module_templates",
    )
    op.drop_column("test_module_templates", "pipeline_type")
    op.alter_column(
        "test_module_templates",
        "suite_name",
        new_column_name="mugen_suite",
    )

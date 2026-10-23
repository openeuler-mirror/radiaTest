# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""pipeline config_data JSON for type-specific config (seam for non-update types)

Revision ID: 20260720_0020
Revises: 20260720_0019
Create Date: 2026-07-20

Drops module_template_ids + repo_base_url columns (update-specific) and moves them
into a generic config_data JSON blob. Common fields (name/pipeline_type/versions/
archs/dist/image_round/test_framework) stay. This reserves the seam for non-update
pipeline types (release suites, non-mugen benchmark lists, ...) without adding
columns per type.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260720_0020"
down_revision: str | None = "20260720_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. add config_data JSON (nullable first so we can backfill)
    op.add_column(
        "pipeline_configs",
        sa.Column("config_data", sa.JSON(), nullable=True),
    )
    # 2. backfill from module_template_ids + repo_base_url (postgres json_build_object)
    op.execute(
        "UPDATE pipeline_configs SET config_data = json_build_object("
        "'module_template_ids', COALESCE(module_template_ids, '[]'::json), "
        "'repo_base_url', COALESCE(repo_base_url, '')"
        ") WHERE config_data IS NULL"
    )
    op.alter_column("pipeline_configs", "config_data", nullable=False)
    # 3. drop the update-specific columns
    op.drop_column("pipeline_configs", "module_template_ids")
    op.drop_column("pipeline_configs", "repo_base_url")


def downgrade() -> None:
    op.add_column(
        "pipeline_configs",
        sa.Column("module_template_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "pipeline_configs",
        sa.Column("repo_base_url", sa.String(255), nullable=False, server_default=""),
    )
    op.execute(
        "UPDATE pipeline_configs SET module_template_ids = config_data->'module_template_ids', "
        "repo_base_url = COALESCE(config_data->>'repo_base_url', '')"
    )
    op.drop_column("pipeline_configs", "config_data")

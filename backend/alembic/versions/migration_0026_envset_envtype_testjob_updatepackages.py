# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add env_type to test_env_sets + update_packages to test_jobs

Revision ID: 20260727_0026
Revises: 20260725_0025
Create Date: 2026-07-27

TestEnvSet.env_type (nullable str) — per-env-set env type (vm/physical) so that
a single RunJob (env_type=both) can contain mixed env_sets. execute_env_set
checks env_set.env_type instead of job.env_type.

TestJob.update_packages (JSON list) — the package list from fetch_update_packages,
stored at build time so the API can return it immediately (early display) without
waiting for pre_env + self-collect.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260727_0026"
down_revision: str | None = "20260725_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_env_sets",
        sa.Column("env_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "test_jobs",
        sa.Column("update_packages", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("test_jobs", "update_packages")
    op.drop_column("test_env_sets", "env_type")

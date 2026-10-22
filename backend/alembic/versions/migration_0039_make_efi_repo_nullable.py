# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""make efi_url/repo_url nullable for ISO mode

Revision ID: 20260902_0039
Revises: 20260902_0038
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0039"
down_revision: str | None = "20260902_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ISO 模式不填 efi_url/repo_url，需允许 NULL
    op.alter_column(
        "physical_install_images",
        "efi_url",
        existing_type=sa.String(length=512),
        nullable=True,
    )
    op.alter_column(
        "physical_install_images",
        "repo_url",
        existing_type=sa.String(length=512),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "physical_install_images",
        "repo_url",
        existing_type=sa.String(length=512),
        nullable=False,
    )
    op.alter_column(
        "physical_install_images",
        "efi_url",
        existing_type=sa.String(length=512),
        nullable=False,
    )

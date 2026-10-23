# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create physical_install_images table

Revision ID: 20260724_0025
Revises: 20260723_0024
Create Date: 2026-07-24

Stores PXE installation images for physical machines:
os_version, arch, efi_url (grub EFI download), repo_url (repo root
with images/pxeboot/). ADMIN manually maintains. See ADR 0014.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0025"
down_revision: str | None = "20260723_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "physical_install_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("os_version", sa.String(64), nullable=False),
        sa.Column("arch", sa.String(32), nullable=False),
        sa.Column("efi_url", sa.String(512), nullable=False),
        sa.Column("repo_url", sa.String(512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("os_version", "arch", name="uq_pii_os_arch"),
    )


def downgrade() -> None:
    op.drop_table("physical_install_images")

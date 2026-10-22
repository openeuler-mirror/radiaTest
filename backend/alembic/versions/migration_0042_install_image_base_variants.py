# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add swap_kernel_variant to physical_install_images + install_image_base_variants table

Revision ID: 20260905_0042
Revises: 20260903_0041
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_0042"
down_revision: str | None = "20260903_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "physical_install_images",
        sa.Column("swap_kernel_variant", sa.String(64), nullable=True),
    )
    op.create_table(
        "install_image_base_variants",
        sa.Column("os_version", sa.String(64), nullable=False),
        sa.Column("base_kernel_variant", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("os_version"),
    )
    # 默认 DevStation 基础变体 = 6.6（94 本地只同步了 k6.6 OS 树）。
    op.execute(
        "INSERT INTO install_image_base_variants (os_version, base_kernel_variant, updated_at) "
        "VALUES ('openEuler-26.09-DevStation', '6.6', now()) "
        "ON CONFLICT (os_version) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("install_image_base_variants")
    op.drop_column("physical_install_images", "swap_kernel_variant")
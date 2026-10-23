# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add round/iso_url/kernel_variant to physical_install_images

Revision ID: 20260902_0038
Revises: 20260901_0037
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0038"
down_revision: str | None = "20260901_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "physical_install_images",
        sa.Column("round", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "physical_install_images",
        sa.Column("iso_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "physical_install_images",
        sa.Column("kernel_variant", sa.String(length=64), nullable=True),
    )
    # 现有 official 行回填 round=official（efi+repo 模式，无轮次概念）
    op.execute(
        "UPDATE physical_install_images SET round='official' WHERE round IS NULL"
    )
    # 唯一约束：os_version+arch -> os_version+arch+round+kernel_variant
    # （RC 同 os_version+arch 可有多轮次×多内核变体行）
    op.drop_constraint("uq_pii_os_arch", "physical_install_images", type_="unique")
    op.create_unique_constraint(
        "uq_pii_os_arch_round_kernel",
        "physical_install_images",
        ["os_version", "arch", "round", "kernel_variant"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_pii_os_arch_round_kernel", "physical_install_images", type_="unique"
    )
    op.create_unique_constraint(
        "uq_pii_os_arch", "physical_install_images", ["os_version", "arch"]
    )
    op.drop_column("physical_install_images", "kernel_variant")
    op.drop_column("physical_install_images", "iso_url")
    op.drop_column("physical_install_images", "round")

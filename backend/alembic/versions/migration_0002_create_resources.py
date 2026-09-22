# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create resources table

Revision ID: 20260627_0002
Revises: 20260623_0001
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260627_0002"
down_revision: str | None = "20260623_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_code", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("management_status", sa.String(length=16), nullable=False),
        sa.Column("connectivity_status", sa.String(length=16), nullable=False),
        sa.Column("occupancy_status", sa.String(length=16), nullable=False),
        sa.Column("is_critical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("primary_ip", sa.String(length=64), nullable=False),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("arch", sa.String(length=32), nullable=True),
        sa.Column("os_version", sa.String(length=128), nullable=True),
        sa.Column("kernel_version", sa.String(length=128), nullable=True),
        sa.Column("ssh_username", sa.String(length=64), nullable=False),
        sa.Column("ssh_password", sa.String(length=512), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("usage_scenario", sa.String(length=128), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column("device_location", sa.String(length=255), nullable=True),
        sa.Column("device_distribution", sa.String(length=64), nullable=True),
        sa.Column("bmc_ip", sa.String(length=64), nullable=True),
        sa.Column("bmc_username", sa.String(length=64), nullable=True),
        sa.Column("bmc_password", sa.String(length=512), nullable=True),
        sa.Column("cpu_model", sa.String(length=128), nullable=True),
        sa.Column("cpu_count", sa.Integer(), nullable=True),
        sa.Column("memory_count", sa.Integer(), nullable=True),
        sa.Column("memory_spec", sa.String(length=255), nullable=True),
        sa.Column("hdd_count", sa.Integer(), nullable=True),
        sa.Column("hdd_spec", sa.String(length=255), nullable=True),
        sa.Column("ssd_count", sa.Integer(), nullable=True),
        sa.Column("ssd_spec", sa.String(length=255), nullable=True),
        sa.Column("ssd_card_count", sa.Integer(), nullable=True),
        sa.Column("ssd_card_spec", sa.String(length=255), nullable=True),
        sa.Column("system_sn", sa.String(length=128), nullable=True),
        sa.Column("board_sn", sa.String(length=128), nullable=True),
        sa.Column("vnc_port", sa.Integer(), nullable=True),
        sa.Column("vcpu_count", sa.Integer(), nullable=True),
        sa.Column("memory_mb", sa.Integer(), nullable=True),
        sa.Column("disk_gb", sa.Integer(), nullable=True),
        sa.Column("host_resource_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resources_arch"), "resources", ["arch"], unique=False)
    op.create_index(op.f("ix_resources_bmc_ip"), "resources", ["bmc_ip"], unique=False)
    op.create_index(
        op.f("ix_resources_management_status"),
        "resources",
        ["management_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_resources_occupancy_status"),
        "resources",
        ["occupancy_status"],
        unique=False,
    )
    op.create_index(op.f("ix_resources_primary_ip"), "resources", ["primary_ip"], unique=False)
    op.create_index(op.f("ix_resources_resource_code"), "resources", ["resource_code"], unique=True)
    op.create_index(
        op.f("ix_resources_resource_type"),
        "resources",
        ["resource_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resources_resource_type"), table_name="resources")
    op.drop_index(op.f("ix_resources_resource_code"), table_name="resources")
    op.drop_index(op.f("ix_resources_primary_ip"), table_name="resources")
    op.drop_index(op.f("ix_resources_occupancy_status"), table_name="resources")
    op.drop_index(op.f("ix_resources_management_status"), table_name="resources")
    op.drop_index(op.f("ix_resources_bmc_ip"), table_name="resources")
    op.drop_index(op.f("ix_resources_arch"), table_name="resources")
    op.drop_table("resources")

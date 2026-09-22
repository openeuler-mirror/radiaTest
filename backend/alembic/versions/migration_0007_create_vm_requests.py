# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create vm requests

Revision ID: 20260701_0007
Revises: 20260630_0006
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260701_0007"
down_revision: str | None = "20260630_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "virtual_resource_specs",
        sa.Column("vm_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "virtual_resource_specs",
        sa.Column("system_disk_path", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "virtual_resource_specs",
        sa.Column("data_disk_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "virtual_resource_specs",
        sa.Column("data_disk_size_gb", sa.Integer(), nullable=True),
    )
    op.add_column(
        "virtual_resource_specs",
        sa.Column("data_disk_paths", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.alter_column("virtual_resource_specs", "data_disk_paths", server_default=None)

    op.create_table(
        "vm_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("requester_user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("expected_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dist", sa.String(length=64), nullable=False),
        sa.Column("os_version", sa.String(length=128), nullable=False),
        sa.Column("image_round", sa.String(length=64), nullable=False),
        sa.Column("arch", sa.String(length=32), nullable=False),
        sa.Column("kernel_version", sa.String(length=128), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("vcpu_count", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("disk_gb", sa.Integer(), nullable=False),
        sa.Column("data_disk_count", sa.Integer(), nullable=False),
        sa.Column("data_disk_size_gb", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("host_resource_id", sa.String(length=36), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("host_attempts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vm_requests_arch"), "vm_requests", ["arch"], unique=False)
    op.create_index(
        op.f("ix_vm_requests_host_resource_id"),
        "vm_requests",
        ["host_resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vm_requests_requester_user_id"),
        "vm_requests",
        ["requester_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vm_requests_resource_id"),
        "vm_requests",
        ["resource_id"],
        unique=False,
    )
    op.create_index(op.f("ix_vm_requests_status"), "vm_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vm_requests_status"), table_name="vm_requests")
    op.drop_index(op.f("ix_vm_requests_resource_id"), table_name="vm_requests")
    op.drop_index(op.f("ix_vm_requests_requester_user_id"), table_name="vm_requests")
    op.drop_index(op.f("ix_vm_requests_host_resource_id"), table_name="vm_requests")
    op.drop_index(op.f("ix_vm_requests_arch"), table_name="vm_requests")
    op.drop_table("vm_requests")

    op.drop_column("virtual_resource_specs", "data_disk_paths")
    op.drop_column("virtual_resource_specs", "data_disk_size_gb")
    op.drop_column("virtual_resource_specs", "data_disk_count")
    op.drop_column("virtual_resource_specs", "system_disk_path")
    op.drop_column("virtual_resource_specs", "vm_name")

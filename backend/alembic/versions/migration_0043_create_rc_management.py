# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create rc_management tables (DDL only; 数据回填见 0044)

Revision ID: 20260910_0043
Revises: 20260905_0042
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_0043"
down_revision: str | None = "20260905_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "versions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("version_type", sa.String(16), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_versions_name", "versions", ["name"], unique=True)

    op.create_table(
        "milestones",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("kernel_variant", sa.String(64), nullable=True),
        sa.Column("build_url", sa.String(1024), nullable=False),
        sa.Column("pxe_round_label", sa.String(128), nullable=True),
        sa.Column("compare_base_milestone_id", sa.String(36), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["versions.id"]),
        sa.ForeignKeyConstraint(
            ["compare_base_milestone_id"],
            ["milestones.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "name", name="uq_milestones_version_name"),
    )
    op.create_index("ix_milestones_version_id", "milestones", ["version_id"])

    op.create_table(
        "rc_milestone_compares",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("milestone_id", sa.String(36), nullable=False),
        sa.Column("base_milestone_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("total_changed", sa.Integer(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(64), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"]),
        sa.ForeignKeyConstraint(["base_milestone_id"], ["milestones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rc_milestone_compares_milestone_id", "rc_milestone_compares", ["milestone_id"]
    )

    op.create_table(
        "rc_package_compare_results",
        sa.Column("id", sa.Integer(), sa.Identity(start=1), nullable=False),
        sa.Column("compare_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("repo_path", sa.String(32), nullable=False),
        sa.Column("pkg_name", sa.String(255), nullable=False),
        sa.Column("arch", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("rpm_base", sa.Text(), nullable=True),
        sa.Column("rpm_target", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["compare_id"], ["rc_milestone_compares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rc_results_compare_kind_repo",
        "rc_package_compare_results",
        ["compare_id", "kind", "repo_path", "arch", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_rc_results_compare_kind_repo", table_name="rc_package_compare_results")
    op.drop_table("rc_package_compare_results")
    op.drop_index("ix_rc_milestone_compares_milestone_id", table_name="rc_milestone_compares")
    op.drop_table("rc_milestone_compares")
    op.drop_index("ix_milestones_version_id", table_name="milestones")
    op.drop_table("milestones")
    op.drop_index("ix_versions_name", table_name="versions")
    op.drop_table("versions")

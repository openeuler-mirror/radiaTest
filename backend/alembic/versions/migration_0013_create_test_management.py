# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create test management tables

Revision ID: 20260714_0013
Revises: 20260713_0012
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_0013"
down_revision: str | None = "20260713_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mugen_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("suite_name", sa.String(length=255), nullable=False),
        sa.Column("case_name", sa.String(length=255), nullable=False),
        sa.Column("env_type", sa.String(length=32), nullable=False),
        sa.Column("node_num", sa.Integer(), nullable=False),
        sa.Column("add_disk_num", sa.Integer(), nullable=False),
        sa.Column("add_nic_num", sa.Integer(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suite_name", "case_name", name="uq_mugen_cases_suite_case"),
    )
    op.create_index(op.f("ix_mugen_cases_case_name"), "mugen_cases", ["case_name"])
    op.create_index(op.f("ix_mugen_cases_commit_sha"), "mugen_cases", ["commit_sha"])
    op.create_index(op.f("ix_mugen_cases_env_type"), "mugen_cases", ["env_type"])
    op.create_index(op.f("ix_mugen_cases_suite_name"), "mugen_cases", ["suite_name"])

    op.create_table(
        "test_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("framework", sa.String(length=32), nullable=False),
        sa.Column("env_type", sa.String(length=32), nullable=False),
        sa.Column("dist", sa.String(length=64), nullable=False),
        sa.Column("os_version", sa.String(length=128), nullable=False),
        sa.Column("image_round", sa.String(length=64), nullable=False),
        sa.Column("arch", sa.String(length=32), nullable=False),
        sa.Column("mugen_commit_sha", sa.String(length=64), nullable=False),
        sa.Column("env_set_num", sa.Integer(), nullable=False),
        sa.Column("keep_failed_env", sa.Boolean(), nullable=False),
        sa.Column("pre_env_script", sa.Text(), nullable=True),
        sa.Column("post_env_script", sa.Text(), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_jobs_creator_user_id"), "test_jobs", ["creator_user_id"])
    op.create_index(op.f("ix_test_jobs_env_type"), "test_jobs", ["env_type"])
    op.create_index(op.f("ix_test_jobs_framework"), "test_jobs", ["framework"])
    op.create_index(op.f("ix_test_jobs_mugen_commit_sha"), "test_jobs", ["mugen_commit_sha"])
    op.create_index(op.f("ix_test_jobs_status"), "test_jobs", ["status"])
    op.create_index(op.f("ix_test_jobs_task_id"), "test_jobs", ["task_id"])

    op.create_table(
        "test_env_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("set_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("node_num", sa.Integer(), nullable=False),
        sa.Column("add_disk_num", sa.Integer(), nullable=False),
        sa.Column("add_nic_num", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["test_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "set_index", name="uq_test_env_sets_job_index"),
    )
    op.create_index(op.f("ix_test_env_sets_job_id"), "test_env_sets", ["job_id"])
    op.create_index(op.f("ix_test_env_sets_status"), "test_env_sets", ["status"])

    op.create_table(
        "test_env_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("env_set_id", sa.String(length=36), nullable=False),
        sa.Column("node_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("vm_request_id", sa.String(length=36), nullable=True),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("primary_ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["env_set_id"], ["test_env_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("env_set_id", "node_index", name="uq_test_env_nodes_env_set_index"),
    )
    op.create_index(op.f("ix_test_env_nodes_env_set_id"), "test_env_nodes", ["env_set_id"])
    op.create_index(op.f("ix_test_env_nodes_resource_id"), "test_env_nodes", ["resource_id"])
    op.create_index(op.f("ix_test_env_nodes_status"), "test_env_nodes", ["status"])
    op.create_index(op.f("ix_test_env_nodes_vm_request_id"), "test_env_nodes", ["vm_request_id"])

    op.create_table(
        "test_case_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("env_set_id", sa.String(length=36), nullable=False),
        sa.Column("suite_name", sa.String(length=255), nullable=False),
        sa.Column("case_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout_summary", sa.Text(), nullable=True),
        sa.Column("stderr_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["env_set_id"], ["test_env_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["test_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_case_runs_case_name"), "test_case_runs", ["case_name"])
    op.create_index(op.f("ix_test_case_runs_env_set_id"), "test_case_runs", ["env_set_id"])
    op.create_index(op.f("ix_test_case_runs_job_id"), "test_case_runs", ["job_id"])
    op.create_index(op.f("ix_test_case_runs_status"), "test_case_runs", ["status"])
    op.create_index(op.f("ix_test_case_runs_suite_name"), "test_case_runs", ["suite_name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_test_case_runs_suite_name"), table_name="test_case_runs")
    op.drop_index(op.f("ix_test_case_runs_status"), table_name="test_case_runs")
    op.drop_index(op.f("ix_test_case_runs_job_id"), table_name="test_case_runs")
    op.drop_index(op.f("ix_test_case_runs_env_set_id"), table_name="test_case_runs")
    op.drop_index(op.f("ix_test_case_runs_case_name"), table_name="test_case_runs")
    op.drop_table("test_case_runs")

    op.drop_index(op.f("ix_test_env_nodes_vm_request_id"), table_name="test_env_nodes")
    op.drop_index(op.f("ix_test_env_nodes_status"), table_name="test_env_nodes")
    op.drop_index(op.f("ix_test_env_nodes_resource_id"), table_name="test_env_nodes")
    op.drop_index(op.f("ix_test_env_nodes_env_set_id"), table_name="test_env_nodes")
    op.drop_table("test_env_nodes")

    op.drop_index(op.f("ix_test_env_sets_status"), table_name="test_env_sets")
    op.drop_index(op.f("ix_test_env_sets_job_id"), table_name="test_env_sets")
    op.drop_table("test_env_sets")

    op.drop_index(op.f("ix_test_jobs_task_id"), table_name="test_jobs")
    op.drop_index(op.f("ix_test_jobs_status"), table_name="test_jobs")
    op.drop_index(op.f("ix_test_jobs_mugen_commit_sha"), table_name="test_jobs")
    op.drop_index(op.f("ix_test_jobs_framework"), table_name="test_jobs")
    op.drop_index(op.f("ix_test_jobs_env_type"), table_name="test_jobs")
    op.drop_index(op.f("ix_test_jobs_creator_user_id"), table_name="test_jobs")
    op.drop_table("test_jobs")

    op.drop_index(op.f("ix_mugen_cases_suite_name"), table_name="mugen_cases")
    op.drop_index(op.f("ix_mugen_cases_env_type"), table_name="mugen_cases")
    op.drop_index(op.f("ix_mugen_cases_commit_sha"), table_name="mugen_cases")
    op.drop_index(op.f("ix_mugen_cases_case_name"), table_name="mugen_cases")
    op.drop_table("mugen_cases")

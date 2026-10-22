# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add test job templates and readable job ids

Revision ID: 20260715_0015
Revises: 20260714_0014
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260715_0015"
down_revision: str | None = "20260727_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _drop_test_job_tables() -> None:
    op.drop_table("test_case_runs")
    op.drop_table("test_env_nodes")
    op.drop_table("test_env_sets")
    op.drop_table("test_jobs")


def _create_test_job_tables(*, readable_ids: bool) -> None:
    job_id_type = sa.Integer() if readable_ids else sa.String(length=36)
    job_id_args = (sa.Identity(start=10000),) if readable_ids else ()

    op.create_table(
        "test_jobs",
        sa.Column("id", job_id_type, *job_id_args, nullable=False),
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
        sa.Column("job_id", job_id_type, nullable=False),
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
        sa.Column("job_id", job_id_type, nullable=False),
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


def upgrade() -> None:
    op.execute("DELETE FROM task_events WHERE subject_type = 'test_job'")
    op.execute(
        "DELETE FROM idempotency_records "
        "WHERE method = 'POST' AND path = '/api/v1/test-jobs'"
    )
    _drop_test_job_tables()
    _create_test_job_tables(readable_ids=True)

    op.create_table(
        "test_job_templates",
        sa.Column("id", sa.Integer(), sa.Identity(start=1), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("framework", sa.String(length=32), nullable=False),
        sa.Column("env_type", sa.String(length=32), nullable=False),
        sa.Column("dist", sa.String(length=64), nullable=False),
        sa.Column("os_version", sa.String(length=128), nullable=False),
        sa.Column("image_round", sa.String(length=64), nullable=False),
        sa.Column("arch", sa.String(length=32), nullable=False),
        sa.Column("env_set_num", sa.Integer(), nullable=False),
        sa.Column("keep_failed_env", sa.Boolean(), nullable=False),
        sa.Column("pre_env_script", sa.Text(), nullable=True),
        sa.Column("post_env_script", sa.Text(), nullable=True),
        sa.Column("case_selections", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_test_job_templates_name_ci",
        "test_job_templates",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        op.f("ix_test_job_templates_creator_user_id"),
        "test_job_templates",
        ["creator_user_id"],
    )


def downgrade() -> None:
    op.drop_table("test_job_templates")
    _drop_test_job_tables()
    _create_test_job_tables(readable_ids=False)

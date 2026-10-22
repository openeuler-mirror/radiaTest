# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create update test pipeline tables

Revision ID: 20260716_0015
Revises: 20260714_0014
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260716_0015"
down_revision: str | None = "20260714_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "test_module_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("mugen_suite", sa.String(255), nullable=False),
        sa.Column("env_set_num", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("node_num", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("case_filter", sa.String(64), nullable=False, server_default="none"),
        sa.Column("env_type_split", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("skip_packages", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("pre_env_script", sa.Text(), nullable=False, server_default=""),
        sa.Column("post_env_script", sa.Text(), nullable=False, server_default=""),
        sa.Column("log_paths", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("result_parser", sa.String(64), nullable=False, server_default="none"),
        sa.Column("test_framework", sa.String(64), nullable=False, server_default="mugen"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_test_module_templates_name", "test_module_templates", ["name"])

    op.create_table(
        "update_pipeline_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("module_template_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("versions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("archs", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "repo_base_url",
            sa.String(255),
            nullable=False,
            server_default="http://121.36.84.172/repo.openeuler.org",
        ),
        sa.Column("test_framework", sa.String(64), nullable=False, server_default="mugen"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_update_pipeline_configs_name", "update_pipeline_configs", ["name"])

    op.create_table(
        "update_pipeline_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "config_id",
            sa.String(36),
            sa.ForeignKey("update_pipeline_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("triggered_by", sa.String(64), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_update_pipeline_runs_config_id", "update_pipeline_runs", ["config_id"])
    op.create_index("ix_update_pipeline_runs_version", "update_pipeline_runs", ["version"])
    op.create_index("ix_update_pipeline_runs_status", "update_pipeline_runs", ["status"])

    op.create_table(
        "update_pipeline_run_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "pipeline_run_id",
            sa.String(36),
            sa.ForeignKey("update_pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "module_template_id",
            sa.String(36),
            sa.ForeignKey("test_module_templates.id"),
            nullable=False,
        ),
        sa.Column("arch", sa.String(32), nullable=False),
        sa.Column("env_type", sa.String(32), nullable=True),
        sa.Column("test_job_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_update_pipeline_run_jobs_pipeline_run_id",
        "update_pipeline_run_jobs",
        ["pipeline_run_id"],
    )
    op.create_index(
        "ix_update_pipeline_run_jobs_module_template_id",
        "update_pipeline_run_jobs",
        ["module_template_id"],
    )
    op.create_index(
        "ix_update_pipeline_run_jobs_test_job_id",
        "update_pipeline_run_jobs",
        ["test_job_id"],
    )

    op.create_table(
        "pipeline_run_node_infos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_job_id",
            sa.String(36),
            sa.ForeignKey("update_pipeline_run_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("resource_code", sa.String(128), nullable=True),
        sa.Column("primary_ip", sa.String(64), nullable=True),
        sa.Column("role", sa.String(32), nullable=True),
        sa.Column("env_set_index", sa.Integer(), nullable=True),
        sa.Column("node_index", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_pipeline_run_node_infos_run_job_id",
        "pipeline_run_node_infos",
        ["run_job_id"],
    )
    op.create_index(
        "ix_pipeline_run_node_infos_resource_id",
        "pipeline_run_node_infos",
        ["resource_id"],
    )

    op.create_table(
        "test_case_run_details",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_run_id", sa.String(36), nullable=False),
        sa.Column("sub_test_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_test_case_run_details_case_run_id",
        "test_case_run_details",
        ["case_run_id"],
    )

    op.create_table(
        "test_log_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pipeline_run_id", sa.String(36), nullable=True),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("arch", sa.String(32), nullable=False),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("artifact_name", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_test_log_artifacts_pipeline_run_id",
        "test_log_artifacts",
        ["pipeline_run_id"],
    )
    op.create_index(
        "ix_test_log_artifacts_job_id", "test_log_artifacts", ["job_id"]
    )

    op.add_column(
        "test_jobs",
        sa.Column("pipeline_run_job_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_test_jobs_pipeline_run_job_id", "test_jobs", ["pipeline_run_job_id"])


def downgrade() -> None:
    op.drop_index("ix_test_jobs_pipeline_run_job_id", table_name="test_jobs")
    op.drop_column("test_jobs", "pipeline_run_job_id")

    op.drop_index("ix_test_log_artifacts_job_id", table_name="test_log_artifacts")
    op.drop_index("ix_test_log_artifacts_pipeline_run_id", table_name="test_log_artifacts")
    op.drop_table("test_log_artifacts")

    op.drop_index("ix_test_case_run_details_case_run_id", table_name="test_case_run_details")
    op.drop_table("test_case_run_details")

    op.drop_index("ix_update_pipeline_run_jobs_test_job_id", table_name="update_pipeline_run_jobs")
    op.drop_index(
        "ix_update_pipeline_run_jobs_module_template_id", table_name="update_pipeline_run_jobs"
    )
    op.drop_index(
        "ix_update_pipeline_run_jobs_pipeline_run_id", table_name="update_pipeline_run_jobs"
    )
    op.drop_table("update_pipeline_run_jobs")

    op.drop_index("ix_update_pipeline_runs_status", table_name="update_pipeline_runs")
    op.drop_index("ix_update_pipeline_runs_version", table_name="update_pipeline_runs")
    op.drop_index("ix_update_pipeline_runs_config_id", table_name="update_pipeline_runs")
    op.drop_table("update_pipeline_runs")

    op.drop_index("ix_update_pipeline_configs_name", table_name="update_pipeline_configs")
    op.drop_table("update_pipeline_configs")

    op.drop_index("ix_test_module_templates_name", table_name="test_module_templates")
    op.drop_table("test_module_templates")

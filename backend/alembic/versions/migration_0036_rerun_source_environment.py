# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""reuse source environment for Pipeline RunJob reruns

Revision ID: 20260828_0036
Revises: 20260828_0035
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0036"
down_revision: str | None = "20260828_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DOCKER_RERUN_ENV = """#!/bin/bash
set -Eeuo pipefail
export LANG="en_US.UTF-8"
docker restart openEuler_test
for _ in $(seq 1 30); do
    test "$(docker inspect -f '{{.State.Running}}' openEuler_test 2>/dev/null)" = "true" && break
    sleep 2
done
test "$(docker inspect -f '{{.State.Running}}' openEuler_test 2>/dev/null)" = "true"
"""


def upgrade() -> None:
    op.add_column(
        "test_module_templates",
        sa.Column("rerun_env_script", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "test_jobs",
        sa.Column("rerun_env_script", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column("test_jobs", sa.Column("rerun_source_job_id", sa.Integer(), nullable=True))
    op.create_index("ix_test_jobs_rerun_source_job_id", "test_jobs", ["rerun_source_job_id"])
    op.create_foreign_key(
        "fk_test_jobs_rerun_source_job_id",
        "test_jobs",
        "test_jobs",
        ["rerun_source_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "test_env_sets", sa.Column("rerun_source_env_set_id", sa.String(36), nullable=True)
    )
    op.create_index(
        "ix_test_env_sets_rerun_source_env_set_id",
        "test_env_sets",
        ["rerun_source_env_set_id"],
    )
    op.create_foreign_key(
        "fk_test_env_sets_rerun_source_env_set_id",
        "test_env_sets",
        "test_env_sets",
        ["rerun_source_env_set_id"],
        ["id"],
        ondelete="SET NULL",
    )
    for column in ("rerun_source_case_run_id", "rerun_root_case_run_id"):
        op.add_column("test_case_runs", sa.Column(column, sa.String(36), nullable=True))
        op.create_index(f"ix_test_case_runs_{column}", "test_case_runs", [column])
        op.create_foreign_key(
            f"fk_test_case_runs_{column}",
            "test_case_runs",
            "test_case_runs",
            [column],
            ["id"],
            ondelete="SET NULL",
        )
    templates = sa.table(
        "test_module_templates",
        sa.column("name", sa.String()),
        sa.column("rerun_env_script", sa.Text()),
    )
    op.execute(
        templates.update()
        .where(templates.c.name == "docker", templates.c.rerun_env_script == "")
        .values(rerun_env_script=DOCKER_RERUN_ENV)
    )
    op.execute(
        sa.text(
            """
            UPDATE test_jobs AS job
            SET rerun_env_script = :script
            FROM pipeline_run_jobs AS run_job
            JOIN test_module_templates AS template
              ON template.id = run_job.module_template_id
            WHERE run_job.test_job_id = job.id
              AND template.name = 'docker'
              AND job.rerun_env_script = ''
            """
        ).bindparams(script=DOCKER_RERUN_ENV)
    )


def downgrade() -> None:
    for column in ("rerun_root_case_run_id", "rerun_source_case_run_id"):
        op.drop_constraint(f"fk_test_case_runs_{column}", "test_case_runs", type_="foreignkey")
        op.drop_index(f"ix_test_case_runs_{column}", table_name="test_case_runs")
        op.drop_column("test_case_runs", column)
    op.drop_constraint(
        "fk_test_env_sets_rerun_source_env_set_id", "test_env_sets", type_="foreignkey"
    )
    op.drop_index("ix_test_env_sets_rerun_source_env_set_id", table_name="test_env_sets")
    op.drop_column("test_env_sets", "rerun_source_env_set_id")
    op.drop_constraint("fk_test_jobs_rerun_source_job_id", "test_jobs", type_="foreignkey")
    op.drop_index("ix_test_jobs_rerun_source_job_id", table_name="test_jobs")
    op.drop_column("test_jobs", "rerun_source_job_id")
    op.drop_column("test_jobs", "rerun_env_script")
    op.drop_column("test_module_templates", "rerun_env_script")

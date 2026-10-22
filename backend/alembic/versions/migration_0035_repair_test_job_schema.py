# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""repair Test Job schema after table rebuild

Revision ID: 20260828_0035
Revises: 20260827_0034
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0035"
down_revision: str | None = "20260827_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """补回旧表重建丢失的字段，并收敛无法继续执行的 RunJob。"""
    inspector = sa.inspect(op.get_bind())
    test_job_columns = {
        column["name"] for column in inspector.get_columns("test_jobs")
    }
    missing_test_job_columns = {
        "keep_env": sa.Column(
            "keep_env",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        "mugen_exec_command": sa.Column(
            "mugen_exec_command", sa.Text(), nullable=True
        ),
        "result_parser": sa.Column(
            "result_parser", sa.String(length=64), nullable=True
        ),
        "update_packages": sa.Column(
            "update_packages",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    }
    for name, column in missing_test_job_columns.items():
        if name not in test_job_columns:
            op.add_column("test_jobs", column)

    env_set_columns = {
        column["name"] for column in inspector.get_columns("test_env_sets")
    }
    if "env_type" not in env_set_columns:
        op.add_column(
            "test_env_sets",
            sa.Column("env_type", sa.String(length=32), nullable=True),
        )

    pipeline_run_jobs = sa.table(
        "pipeline_run_jobs",
        sa.column("status", sa.String()),
        sa.column("test_job_id", sa.Integer()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        pipeline_run_jobs.update()
        .where(
            pipeline_run_jobs.c.status == "running",
            pipeline_run_jobs.c.test_job_id.is_(None),
        )
        .values(status="error", updated_at=sa.func.now())
    )


def downgrade() -> None:
    """结构修复不回退，避免重新制造与 0034 模型不一致的数据库。"""


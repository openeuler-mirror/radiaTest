# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""create task events

Revision ID: 20260702_0008
Revises: 20260701_0007
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260702_0008"
down_revision: str | None = "20260701_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("phase", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("host_resource_id", sa.String(length=36), nullable=True),
        sa.Column("host_ip", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_events_celery_task_id"), "task_events", ["celery_task_id"])
    op.create_index(op.f("ix_task_events_error_code"), "task_events", ["error_code"])
    op.create_index(op.f("ix_task_events_host_resource_id"), "task_events", ["host_resource_id"])
    op.create_index(op.f("ix_task_events_phase"), "task_events", ["phase"])
    op.create_index(op.f("ix_task_events_subject_id"), "task_events", ["subject_id"])
    op.create_index(op.f("ix_task_events_subject_type"), "task_events", ["subject_type"])
    op.create_index(op.f("ix_task_events_task_type"), "task_events", ["task_type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_task_events_task_type"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_subject_type"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_subject_id"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_phase"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_host_resource_id"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_error_code"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_celery_task_id"), table_name="task_events")
    op.drop_table("task_events")

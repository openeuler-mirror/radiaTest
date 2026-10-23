# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""add image_round to pipeline_executions (trigger-level override)

Revision ID: 20260721_0022
Revises: 20260721_0021
Create Date: 2026-07-21

Adds `pipeline_executions.image_round` (nullable). When set, it overrides
`pipeline_configs.image_round` for this trigger event's TestJobs. Used by
release-type pipelines where each trigger corresponds to a new RC build round.
Builder reads execution.image_round first, falls back to config.image_round.
See ADR 0010.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260721_0022"
down_revision: str | None = "20260721_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_executions",
        sa.Column("image_round", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_executions", "image_round")

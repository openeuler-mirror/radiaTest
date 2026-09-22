# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""no-op（回填取消，版本改手动创建；原 DML 见部署于 2026-09-10 前的环境）

Revision ID: 20260910_0044
Revises: 20260910_0043
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260910_0044"
down_revision: str | None = "20260910_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    回填已取消（2026-09-10 决策）：版本改为用户手动创建，不再从
    physical_install_images 自动回填。保留迁移位次维持已执行环境的历史链。
    """
    pass


def downgrade() -> None:
    op.execute("DELETE FROM versions WHERE created_by = 'migration'")

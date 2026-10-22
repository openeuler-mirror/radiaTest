# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""merge fork cancel branch and upstream kernel/release migration branches

fork 侧 (task_id/cancel_requested) 与上游侧 (custom_kernel/iso_kernel/
efi_repo_nullable/pipeline_extras) 都从 20260828_0036 分叉,合并同步后出现
两个 head。本迁移只做图收敛,不含任何 schema 操作:两侧已部署库无论停在
哪个 head,`alembic upgrade head` 都能沿图走到唯一 head。

Revision ID: 20260903_0041
Revises: ("20260903_0038", "20260903_0040")
Create Date: 2026-09-04
"""

from collections.abc import Sequence

revision: str = "20260903_0041"
down_revision: str | tuple[str, str] | None = ("20260903_0038", "20260903_0040")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

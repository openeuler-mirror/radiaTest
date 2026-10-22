# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""来源环境重跑迁移测试。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from app.modules.pipelines.seed import DOCKER_RERUN_ENV


def _load_migration() -> ModuleType:
    path = (
        Path(__file__).parents[1]
        / "alembic/versions/migration_0036_rerun_source_environment.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0036", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_docker_rerun_script_matches_seed() -> None:
    migration = _load_migration()

    assert migration.DOCKER_RERUN_ENV == DOCKER_RERUN_ENV

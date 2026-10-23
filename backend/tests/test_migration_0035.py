# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Test Job 结构漂移修复迁移测试。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_migration() -> ModuleType:
    path = (
        Path(__file__).parents[1]
        / "alembic/versions/migration_0035_repair_test_job_schema.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0035", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("test_job_columns", "env_set_columns", "expected_additions"),
    [
        (
            {"id"},
            {"id"},
            {
                ("test_jobs", "keep_env"),
                ("test_jobs", "mugen_exec_command"),
                ("test_jobs", "result_parser"),
                ("test_jobs", "update_packages"),
                ("test_env_sets", "env_type"),
            },
        ),
        (
            {
                "id",
                "keep_env",
                "mugen_exec_command",
                "result_parser",
                "update_packages",
            },
            {"id", "env_type"},
            set(),
        ),
    ],
)


def test_upgrade_repairs_missing_columns_idempotently(
    monkeypatch: pytest.MonkeyPatch,
    test_job_columns: set[str],
    env_set_columns: set[str],
    expected_additions: set[tuple[str, str]],
) -> None:
    migration = _load_migration()
    additions: list[tuple[str, str]] = []
    statements: list[object] = []

    class Inspector:
        @staticmethod
        def get_columns(table_name: str) -> list[dict[str, str]]:
            names = test_job_columns if table_name == "test_jobs" else env_set_columns
            return [{"name": name} for name in names]

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: Inspector())
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: additions.append((table, column.name)),
    )
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert set(additions) == expected_additions
    assert len(statements) == 1
    sql = str(statements[0].compile(compile_kwargs={"literal_binds": True}))
    assert "pipeline_run_jobs.status = 'running'" in sql
    assert "pipeline_run_jobs.test_job_id IS NULL" in sql

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""基础内核变体配置（T0）服务测试 + 迁移 0042 加载冒烟。"""

from __future__ import annotations

import importlib.util
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.resources.install_sources import (
    ensure_default_install_base_variants,
    get_install_image_base_variant,
    set_install_image_base_variant,
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()


def test_ensure_default_seeds_devstation_6_6(db: Session) -> None:
    ensure_default_install_base_variants(db)
    assert get_install_image_base_variant(db, "openEuler-26.09-DevStation") == "6.6"


def test_set_and_get_base_variant(db: Session) -> None:
    from app.modules.resources.physical_install_models import PhysicalInstallImage

    db.add(
        PhysicalInstallImage(
            os_version="openEuler-26.09-DevStation", arch="x86_64", kernel_variant="6.18"
        )
    )
    db.commit()
    set_install_image_base_variant(db, "openEuler-26.09-DevStation", "6.18")
    assert get_install_image_base_variant(db, "openEuler-26.09-DevStation") == "6.18"


def test_set_base_variant_rejects_missing_os(db: Session) -> None:
    with pytest.raises(ValueError):
        set_install_image_base_variant(db, "openEuler-99.99-Unknown", "6.6")


def test_migration_0042_loads_and_has_upgrade() -> None:
    path = (
        Path(__file__).parents[1]
        / "alembic/versions/20260905_0042_install_image_base_variants.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0042", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "20260905_0042"
    assert callable(module.upgrade)
    assert callable(module.downgrade)
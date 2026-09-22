# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.resources.physical_install_models import PhysicalInstallImage
from app.modules.resources.service import upsert_install_image


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
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


def test_upsert_creates_new_image(db_session: Session) -> None:
    created = upsert_install_image(
        db_session,
        os_version="openEuler-24.03-LTS",
        arch="x86_64",
        efi_url="http://h/efi/grubx64.efi",
        repo_url="http://h/repo/x86_64",
    )

    assert created is True

    img = db_session.execute(
        select(PhysicalInstallImage).where(
            PhysicalInstallImage.os_version == "openEuler-24.03-LTS",
            PhysicalInstallImage.arch == "x86_64",
        )
    ).scalar_one()
    assert img.efi_url == "http://h/efi/grubx64.efi"
    assert img.repo_url == "http://h/repo/x86_64"


def test_upsert_updates_existing_on_same_os_and_arch(db_session: Session) -> None:
    upsert_install_image(
        db_session,
        os_version="openEuler-24.03-LTS",
        arch="x86_64",
        efi_url="http://h/efi/old.efi",
        repo_url="http://h/repo/old",
    )

    created = upsert_install_image(
        db_session,
        os_version="openEuler-24.03-LTS",
        arch="x86_64",
        efi_url="http://h/efi/new.efi",
        repo_url="http://h/repo/new",
    )

    assert created is False

    db_session.expunge_all()
    img = db_session.execute(
        select(PhysicalInstallImage).where(
            PhysicalInstallImage.os_version == "openEuler-24.03-LTS",
            PhysicalInstallImage.arch == "x86_64",
        )
    ).scalar_one()
    assert img.efi_url == "http://h/efi/new.efi"
    assert img.repo_url == "http://h/repo/new"

    rows = db_session.execute(select(PhysicalInstallImage)).scalars().all()
    assert len(rows) == 1


def test_upsert_treats_different_arch_as_separate(db_session: Session) -> None:
    upsert_install_image(
        db_session,
        os_version="openEuler-24.03-LTS",
        arch="x86_64",
        efi_url="http://h/efi/x64.efi",
        repo_url="http://h/repo/x64",
    )

    created = upsert_install_image(
        db_session,
        os_version="openEuler-24.03-LTS",
        arch="aarch64",
        efi_url="http://h/efi/arm.efi",
        repo_url="http://h/repo/arm",
    )

    assert created is True

    rows = db_session.execute(select(PhysicalInstallImage)).scalars().all()
    assert len(rows) == 2
    archs = sorted(r.arch for r in rows)
    assert archs == ["aarch64", "x86_64"]

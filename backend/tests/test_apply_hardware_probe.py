# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.resources.models import Resource
from app.modules.resources.service import apply_hardware_probe


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


def _make_resource(db: Session, **kw) -> Resource:
    r = Resource(
        resource_code=kw.pop("resource_code", "R1"),
        resource_type="PHYSICAL",
        ssh_username="root",
        ssh_password_ciphertext="x",
        **kw,
    )
    db.add(r)
    db.commit()
    return r


def test_apply_overwrites_resource_and_spec(db_session: Session):
    r = _make_resource(db_session, arch="x86_64", os_version="old")
    probe = {
        "arch": "aarch64",
        "os_version": "openEuler 24.03",
        "kernel_version": "6.6.0",
        "cpu_model": "Kunpeng 920",
        "cpu_count": 96,
        "memory_count": 2,
        "memory_spec": "DDR4 2933 MT/s",
        "hdd_count": 1,
        "hdd_spec": "ST500 447GB",
        "ssd_count": 1,
        "ssd_spec": "MX500 1863GB",
        "ssd_card_count": 1,
        "ssd_card_spec": "Samsung 476GB",
        "board_sn": "SL123",
    }
    apply_hardware_probe(db_session, r, probe)
    db_session.refresh(r)
    assert r.arch == "aarch64"
    assert r.os_version == "old"
    assert r.kernel_version == "6.6.0"
    spec = r.physical_spec
    assert spec is not None
    assert spec.cpu_model == "Kunpeng 920"
    assert spec.cpu_count == 96
    assert spec.memory_count == 2
    assert spec.memory_spec == "DDR4 2933 MT/s"
    assert spec.hdd_count == 1
    assert spec.board_sn == "SL123"


def test_apply_skips_none_keeps_existing(db_session: Session):
    r = _make_resource(db_session, arch="x86_64", os_version="old")
    apply_hardware_probe(db_session, r, {"arch": None, "cpu_count": None, "os_version": None})
    db_session.refresh(r)
    assert r.arch == "x86_64"
    assert r.os_version == "old"


def test_apply_creates_spec_if_missing(db_session: Session):
    r = _make_resource(db_session)
    assert r.physical_spec is None
    apply_hardware_probe(db_session, r, {"cpu_count": 96, "board_sn": "X"})
    db_session.refresh(r)
    assert r.physical_spec is not None
    assert r.physical_spec.cpu_count == 96
    assert r.physical_spec.board_sn == "X"

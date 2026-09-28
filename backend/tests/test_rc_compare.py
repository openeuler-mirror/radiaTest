# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""rc_compare T5/T6 测试：离线比对计算、触发/结果查询接口（fetch 注入离线数据）。"""

from __future__ import annotations

from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.rc_management.compare_service import compute_compare
from app.modules.rc_management.models import (
    MilestoneCompare,
    PackageCompareResult,
    ReleaseMilestone,
)
from app.modules.rc_management.schemas import MilestoneCreate, VersionCreate
from app.modules.rc_management.service import (
    create_compare,
    create_milestone,
    create_version,
    list_milestones,
)
from app.modules.users.models import UserRole
from app.modules.users.service import create_user

BUILD_T = (
    "http://121.36.84.172/dailybuild/EBS-openEuler-26.09-DevStation/"
    "rc4_openeuler-2026-09-07-02-46-54/26.09-with-kernel-6.6/"
)
BUILD_B = (
    "http://121.36.84.172/dailybuild/EBS-openEuler-26.09-DevStation/"
    "rc3_openeuler-2026-08-28-04-39-54/26.09-with-kernel-6.6/"
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _fake_lists() -> Callable[..., list[str] | None]:
    data = {
        (BUILD_T, "x86_64"): [
            "kernel-6.18.0-0.rc2.oe2609.x86_64.rpm",
            "aide-0.19.4-1.oe2609.x86_64.rpm",
            "only-target-1-1.oe2609.x86_64.rpm",
            "llvm-bolt-17.0.6-9.oe2609.x86_64.rpm",
            "llvm-bolt-17.0.6-67.oe2609.x86_64.rpm",
        ],  # noqa: E501
        (BUILD_T, "aarch64"): [
            "kernel-6.18.0-0.rc2.oe2609.aarch64.rpm",
            "aide-0.19.4-1.oe2609.aarch64.rpm",
            "dbus-1.14.10-1.oe2609.aarch64.rpm",
        ],
        (BUILD_T, "src"): ["kernel-6.18.0-0.rc2.oe2609.src.rpm"],
        (BUILD_B, "x86_64"): [
            "kernel-6.18.0-0.rc1.oe2609.x86_64.rpm",
            "aide-0.19.3-1.oe2609.x86_64.rpm",
            "removed-pkg-1-1.oe2609.x86_64.rpm",
        ],
        (BUILD_B, "aarch64"): [
            "kernel-6.18.0-0.rc1.oe2609.aarch64.rpm",
            "aide-0.19.3-1.oe2609.aarch64.rpm",
            "dbus-1.14.10-1.oe2609.aarch64.rpm",
        ],
        (BUILD_B, "src"): ["kernel-6.18.0-0.rc1.oe2609.src.rpm"],
    }
    epol = {
        "x86_64": ["epol-1-1.oe2609.x86_64.rpm"],
        "aarch64": ["epol-1-1.oe2609.aarch64.rpm"],
        "src": ["epol-1-1.oe2609.src.rpm"],
    }

    def fetch(cache_dir, build_url, repo_path, *, source=False, arch=None):  # noqa: ANN001
        if repo_path == "EPOL_main":
            epol_key = "src" if source else arch
            if epol_key not in epol:
                raise KeyError(epol_key)
            return epol[epol_key]
        return data.get((build_url, "src" if source else arch))

    return fetch


def _make_client(db: Session) -> TestClient:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed_milestones(db: Session) -> tuple[ReleaseMilestone, ReleaseMilestone]:
    v = create_version(db, VersionCreate(name="openEuler-26.09-DevStation"), created_by="u1")
    r3 = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="round3", build_url=BUILD_B), created_by="u1"
    )
    r4 = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="round4", build_url=BUILD_T), created_by="u1"
    )
    return r3, r4


def test_compute_compare_offline(db: Session) -> None:
    r3, r4 = _seed_milestones(db)
    compare = MilestoneCompare(
        milestone_id=r4.id, base_milestone_id=r3.id, status="pending", triggered_by="u1"
    )
    db.add(compare)
    db.commit()

    total, summary = compute_compare(
        db, compare, fetch=_fake_lists(), cache_dir=Path("/tmp/nx")
    )
    assert total == 12
    assert summary == {
        "binary": {"ADD": 2, "VER_UP": 2, "REL_UP": 2, "DEL": 1},
        "source": {"REL_UP": 1},
        "repeat": {"REPEAT": 1},
        "isomer": {"LACK": 3},
    }
    by = {(r.kind, r.pkg_name) for r in db.execute(select(PackageCompareResult)).scalars()}
    assert ("binary", "kernel") in by
    assert ("binary", "only-target") in by
    assert ("binary", "removed-pkg") in by
    assert ("binary", "llvm-bolt") in by
    assert ("source", "kernel") in by
    assert ("repeat", "llvm-bolt.x86_64") in by
    assert ("isomer", "only-target") in by
    assert ("isomer", "dbus") in by


def test_compare_requires_build_urls(db: Session) -> None:
    from app.modules.rc_management.errors import MilestoneBuildUrlMissingError

    v = create_version(
        db, VersionCreate(name="openEuler-26.09-DevStation", rc_round_count=3),
        created_by="u1",
    )
    rounds = list_milestones(db, v.id)
    # 骨架轮次带通配 URL；手动置空模拟未登记构建（如历史数据）
    target = db.get(ReleaseMilestone, rounds[1].id)
    target.build_url = None
    db.commit()
    with pytest.raises(MilestoneBuildUrlMissingError):
        create_compare(db, rounds[1].id, rounds[0].id, triggered_by="u1")


def test_cross_version_compare_rejected(db: Session) -> None:
    r3, r4 = _seed_milestones(db)
    v2 = create_version(db, VersionCreate(name="openEuler-24.03-LTS-SP4"), created_by="u1")
    other = create_milestone(
        db, MilestoneCreate(version_id=v2.id, name="round1", build_url=BUILD_B), created_by="u1"
    )
    from app.modules.rc_management.errors import CompareVersionMismatchError

    with pytest.raises(CompareVersionMismatchError):
        create_compare(db, r4.id, other.id, triggered_by="u1")
    del r3


def test_compare_trigger_and_results_api(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    create_user(db, username="tse01", password="test-pass", role=UserRole.TSE)
    db.commit()
    from app.modules.rc_management import tasks

    client = _make_client(db)
    token = (
        client.post(
            "/api/v1/auth/login",
            json={"username": "tse01", "password": "test-pass"},
        )
        .json()["access_token"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    vid = client.post(
        "/api/v1/versions",
        json={"name": "openEuler-26.09-DevStation"},
        headers=headers,
    ).json()["id"]
    b = client.post(
        "/api/v1/milestones",
        json={"version_id": vid, "name": "round3", "build_url": BUILD_B},
        headers=headers,
    ).json()
    t = client.post(
        "/api/v1/milestones",
        json={"version_id": vid, "name": "round4", "build_url": BUILD_T},
        headers=headers,
    ).json()

    dispatched: list[str] = []
    monkeypatch.setattr(tasks.run_rc_compare_task, "delay", lambda cid: dispatched.append(cid))

    resp = client.post(
        f"/api/v1/milestones/{t['id']}/compares",
        json={"base_milestone_id": b["id"]},
        headers=headers,
    )
    assert resp.status_code == 202, resp.text
    cid = resp.json()["id"]
    assert dispatched == [cid]

    # 进行中不可重复触发
    dup = client.post(
        f"/api/v1/milestones/{t['id']}/compares",
        json={"base_milestone_id": b["id"]},
        headers=headers,
    )
    assert dup.status_code == 409

    # 模拟任务执行后查询结果
    compare = db.get(MilestoneCompare, cid)
    compute_compare(db, compare, fetch=_fake_lists(), cache_dir=Path("/tmp/nx"))
    resp = client.get(f"/api/v1/compares/{cid}/results", params={"kind": "binary"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 7  # binary 变更行

    status_resp = client.get(f"/api/v1/compares/{cid}", headers=headers)
    assert status_resp.json()["status"] == "succeeded"
    assert status_resp.json()["total_changed"] == 12

    # 导出端点：默认 pkglist_for 被替换为离线 fetch，返回 zip
    from app.modules.rc_management import export_service

    monkeypatch.setattr(export_service, "pkglist_for", _fake_lists())
    export_resp = client.get(f"/api/v1/compares/{cid}/export", headers=headers)
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/zip"
    assert b"PK" in export_resp.content  # zip magic
# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""rc_management T2 API 测试：版本/里程碑 CRUD、TSE/ADMIN 写权限、错误映射。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.users.models import User, UserRole
from app.modules.users.service import create_user

BUILD_URL = (
    "http://121.36.84.172/dailybuild/EBS-openEuler-26.09-DevStation/"
    "rc4_openeuler-2026-09-07-02-46-54/26.09-with-kernel-6.6/"
)


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


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def add_user(db: Session, *, username: str, role: UserRole) -> User:
    user = create_user(db, username=username, password="test-pass", role=role)
    db.commit()
    return user


def login(client: TestClient, username: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": "test-pass"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed(client: TestClient, token: str) -> str:
    resp = client.post(
        "/api/v1/versions",
        json={"name": "openEuler-26.09-DevStation", "version_type": "INNOVATION"},
        headers=headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_te_cannot_write_versions(client: TestClient, db_session: Session) -> None:
    add_user(db_session, username="ted", role=UserRole.TE)
    add_user(db_session, username="tse", role=UserRole.TSE)
    te = login(client, "ted")
    tse = login(client, "tse")

    # TE 写被 403
    assert (
        client.post(
            "/api/v1/versions",
            json={"name": "openEuler-24.03-LTS-SP4"},
            headers=headers(te),
        ).status_code
        == 403
    )
    # TSE 可写
    resp = client.post(
        "/api/v1/versions",
        json={"name": "openEuler-24.03-LTS-SP4"},
        headers=headers(tse),
    )
    assert resp.status_code == 201


def test_version_and_milestone_crud_flow(client: TestClient, db_session: Session) -> None:
    add_user(db_session, username="tse", role=UserRole.TSE)
    tse = login(client, "tse")
    token = tse

    vid = _seed(client, token)

    # 编辑 + 状态
    r = client.put(
        f"/api/v1/versions/{vid}",
        json={"status": "finished"},
        headers=headers(token),
    )
    assert r.status_code == 200 and r.json()["status"] == "finished"

    # 创建里程碑：自动推导 pxe_round_label
    r = client.post(
        "/api/v1/milestones",
        json={"version_id": vid, "name": "round4", "build_url": BUILD_URL},
        headers=headers(token),
    )
    assert r.status_code == 201, r.text
    ms = r.json()
    assert ms["pxe_round_label"] == "rc4_openeuler-2026-09-07-02-46-54"
    assert ms["has_pxe_source"] is False

    # invalid build_url -> 400
    r = client.post(
        "/api/v1/milestones",
        json={"version_id": vid, "name": "round5", "build_url": "http://x//"},
        headers=headers(token),
    )  # noqa: E501
    assert r.status_code == 400

    # 版本详情下拉取里程碑
    r = client.get(f"/api/v1/versions/{vid}/milestones", headers=headers(token))
    assert r.status_code == 200 and [m["name"] for m in r.json()] == [
        "alpha",
        "round4",
    ]

    # 无比对记录：版本可删（alpha/round4 骨架级联）；有比对记录时后端返回 409
    assert client.delete(f"/api/v1/versions/{vid}", headers=headers(token)).status_code == 204


def test_read_requires_login(client: TestClient) -> None:
    resp = client.get("/api/v1/versions")
    assert resp.status_code == 401
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
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.users.models import UserRole
from app.modules.users.service import create_user


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


def _login(client: TestClient, db_session: Session, *, username: str, role: UserRole) -> str:
    create_user(
        db_session,
        username=username,
        password="test-pass",
        role=role,
        display_name=username,
    )
    db_session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test-pass"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_test_job_returns_business_error_when_idempotency_key_present(
    client: TestClient,
    db_session: Session,
) -> None:
    """带 Idempotency-Key 的创建请求被业务拒绝时返回 400，不是 500。

    幂等入口返回的是 HTTP 判定对象，其 .record 才是待废弃的 IdempotencyRecord。
    把判定对象直接当记录传下去会在失败分支抛 AttributeError，把业务 400 变成 500。
    """
    token = _login(client, db_session, username="te1", role=UserRole.TE)

    response = client.post(
        "/api/v1/test-jobs",
        json={
            "name": "no index",
            "os_version": "openEuler-24.03-LTS-SP4",
            "image_round": "round-9",
            "arch": "aarch64",
            "cases": [{"suite_name": "suite-a"}],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "reject-empty-index",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Mugen 用例索引为空"

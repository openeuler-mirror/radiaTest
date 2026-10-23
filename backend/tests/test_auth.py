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
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.users.models import UserRole
from app.modules.users.service import create_user


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


def test_login_and_read_current_user(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        username="admin",
        password="admin-pass",
        role=UserRole.ADMIN,
        display_name="管理员",
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin-pass"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    user = me_response.json()
    assert user["id"]
    assert user["username"] == "admin"
    assert user["display_name"] == "管理员"
    assert user["role"] == "ADMIN"
    assert user["is_active"] is True
    assert user["last_login_at"]
    assert user["created_at"]

    audit_log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "auth.login")
    )
    assert audit_log is not None
    assert audit_log.actor_user_id == user["id"]
    assert audit_log.target_type == "user"
    assert audit_log.target_id == user["id"]
    assert audit_log.detail == {}


def test_login_rejects_wrong_password(client: TestClient, db_session: Session) -> None:
    create_user(
        db_session,
        username="admin",
        password="admin-pass",
        role=UserRole.ADMIN,
        display_name="管理员",
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "invalid_credentials",
        "message": "用户名或密码错误",
        "details": None,
    }
    assert response.headers["WWW-Authenticate"] == "Bearer"

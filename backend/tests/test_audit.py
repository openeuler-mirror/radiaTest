# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.service import record_audit_log
from app.modules.users.models import User, UserRole
from app.modules.users.service import create_user


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_user(db: Session, *, username: str, role: UserRole) -> User:
    user = create_user(
        db,
        username=username,
        password="test-pass",
        role=role,
        display_name=username,
    )
    db.commit()
    return user


def login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test-pass"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


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


def test_admin_can_list_and_filter_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    actor = add_user(db_session, username="te1", role=UserRole.TE)
    now = datetime(2026, 7, 10, 10, 0, tzinfo=UTC)
    matched = record_audit_log(
        db_session,
        actor_user_id=actor.id,
        action="resource.update",
        target_type="resource",
        target_id="resource-1",
        detail={"fields": ["tags"]},
    )
    matched.created_at = now
    old_log = record_audit_log(
        db_session,
        actor_user_id=None,
        action="feishu.remote_command",
        target_type="resource",
        target_id="resource-2",
        detail={"exit_code": 0},
    )
    old_log.created_at = now - timedelta(days=2)
    db_session.commit()
    token = login(client, admin.username)

    response = client.get(
        "/api/v1/audit-logs",
        params={
            "action": "resource",
            "actor_username": "te",
            "target_type": "resource",
            "started_at": (now - timedelta(hours=1)).isoformat(),
            "ended_at": (now + timedelta(hours=1)).isoformat(),
        },
        headers=auth_header(token),
    )

    assert response.status_code == 200
    body = response.json()
    rows = body["items"]
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert len(rows) == 1
    assert rows[0]["id"] == matched.id
    assert rows[0]["actor_user_id"] == actor.id
    assert rows[0]["actor_username"] == actor.username
    assert rows[0]["action"] == "resource.update"
    assert rows[0]["target_type"] == "resource"
    assert rows[0]["target_id"] == "resource-1"
    assert rows[0]["detail"] == {"fields": ["tags"]}


def test_non_admin_cannot_list_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    user = add_user(db_session, username="te1", role=UserRole.TE)
    token = login(client, user.username)

    response = client.get("/api/v1/audit-logs", headers=auth_header(token))

    assert response.status_code == 403


def test_audit_logs_use_fixed_server_side_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    for index in range(51):
        record_audit_log(
            db_session,
            actor_user_id=admin.id,
            action="pagination.test",
            target_type="pagination",
            target_id=str(index),
        )
    db_session.commit()
    token = login(client, admin.username)

    first = client.get(
        "/api/v1/audit-logs",
        params={"action": "pagination.test", "page": 1},
        headers=auth_header(token),
    )
    second = client.get(
        "/api/v1/audit-logs",
        params={"action": "pagination.test", "page": 2},
        headers=auth_header(token),
    )
    out_of_range = client.get(
        "/api/v1/audit-logs",
        params={"action": "pagination.test", "page": 3},
        headers=auth_header(token),
    )
    invalid = client.get(
        "/api/v1/audit-logs",
        params={"page": 0},
        headers=auth_header(token),
    )

    assert first.status_code == 200
    assert first.json()["total"] == 51
    assert first.json()["page_size"] == 50
    assert len(first.json()["items"]) == 50
    assert second.json()["page"] == 2
    assert len(second.json()["items"]) == 1
    assert out_of_range.json()["items"] == []
    assert invalid.status_code == 422

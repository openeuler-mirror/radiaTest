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
from app.modules.users.models import User, UserRole
from app.modules.users.service import create_user, verify_password


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str = "test-pass") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def add_user(
    db: Session,
    *,
    username: str,
    role: UserRole,
    password: str = "test-pass",
    display_name: str | None = None,
) -> User:
    user = create_user(
        db,
        username=username,
        password=password,
        role=role,
        display_name=display_name or username,
    )
    db.commit()
    return user


def audit_logs(db: Session) -> list[AuditLog]:
    return list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.action != "auth.login")
            .order_by(AuditLog.created_at)
        )
        .scalars()
        .all()
    )


def get_user(db: Session, username: str) -> User:
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    return user


def assert_audit_without_password(log: AuditLog, *, action: str, target_user_id: str) -> None:
    assert log.action == action
    assert log.target_type == "user"
    assert log.target_id == target_user_id
    assert "password" not in str(log.detail).lower()


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


def test_admin_can_create_list_update_and_reset_user_password(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN, display_name="管理员")
    token = login(client, "admin")

    create_response = client.post(
        "/api/v1/users",
        json={
            "username": "tse",
            "display_name": "测试系统工程师",
            "role": "TSE",
            "password": "tse-pass",
        },
        headers=auth_header(token),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["username"] == "tse"
    assert created["display_name"] == "测试系统工程师"
    assert created["role"] == "TSE"
    assert created["is_active"] is True

    list_response = client.get(
        "/api/v1/users?username=ts&role=TSE&is_active=true",
        headers=auth_header(token),
    )

    assert list_response.status_code == 200
    assert [user["username"] for user in list_response.json()] == ["tse"]

    patch_response = client.patch(
        f"/api/v1/users/{created['id']}",
        json={"display_name": "测试工程师", "role": "TE", "is_active": False},
        headers=auth_header(token),
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["display_name"] == "测试工程师"
    assert patch_response.json()["role"] == "TE"
    assert patch_response.json()["is_active"] is False

    reset_response = client.post(
        f"/api/v1/users/{created['id']}/reset-password",
        json={"password": "new-pass"},
        headers=auth_header(token),
    )

    assert reset_response.status_code == 204
    target = get_user(db_session, "tse")
    assert verify_password("new-pass", target.password_hash)

    logs = audit_logs(db_session)
    assert [log.action for log in logs] == [
        "user.create",
        "user.update",
        "user.reset_password",
    ]
    assert {log.actor_user_id for log in logs} == {admin.id}
    for log in logs:
        assert_audit_without_password(log, action=log.action, target_user_id=target.id)


def test_non_admin_cannot_manage_users(client: TestClient, db_session: Session) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    token = login(client, "te1")

    response = client.get("/api/v1/users", headers=auth_header(token))

    assert response.status_code == 403


def test_admin_cannot_disable_or_demote_self_or_last_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    token = login(client, "admin")

    disable_self = client.patch(
        f"/api/v1/users/{admin.id}",
        json={"is_active": False},
        headers=auth_header(token),
    )
    demote_self = client.patch(
        f"/api/v1/users/{admin.id}",
        json={"role": "TSE"},
        headers=auth_header(token),
    )

    assert disable_self.status_code == 400
    assert demote_self.status_code == 400

    other_admin = add_user(db_session, username="admin2", role=UserRole.ADMIN)
    disable_other = client.patch(
        f"/api/v1/users/{other_admin.id}",
        json={"is_active": False},
        headers=auth_header(token),
    )
    assert disable_other.status_code == 200

    demote_last_active_admin = client.patch(
        f"/api/v1/users/{admin.id}",
        json={"role": "TSE"},
        headers=auth_header(token),
    )
    assert demote_last_active_admin.status_code == 400


def test_user_can_change_own_password(client: TestClient, db_session: Session) -> None:
    user = add_user(db_session, username="te1", role=UserRole.TE)
    token = login(client, "te1")

    response = client.post(
        "/api/v1/users/me/change-password",
        json={"old_password": "test-pass", "password": "changed-pass"},
        headers=auth_header(token),
    )

    assert response.status_code == 204
    assert verify_password("changed-pass", user.password_hash)
    logs = audit_logs(db_session)
    assert len(logs) == 1
    assert_audit_without_password(
        logs[0],
        action="user.change_own_password",
        target_user_id=user.id,
    )


def test_change_password_rejects_invalid_current_password(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    token = login(client, "te1")

    response = client.post(
        "/api/v1/users/me/change-password",
        json={"old_password": "wrong-pass", "password": "changed-pass"},
        headers=auth_header(token),
    )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "invalid_current_password",
        "message": "当前密码错误",
        "details": None,
    }

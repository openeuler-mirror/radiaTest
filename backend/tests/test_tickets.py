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
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.api_runtime import APIError
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.tickets.errors import TicketVersionConflictError
from app.modules.tickets.models import Ticket
from app.modules.tickets.router import raise_ticket_error
from app.modules.users.models import User, UserRole
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


def test_ticket_version_conflict_has_a_stable_error_code() -> None:
    with pytest.raises(APIError) as captured:
        raise_ticket_error(TicketVersionConflictError("工单已被其他操作更新"))

    assert captured.value.status_code == 409
    assert captured.value.code == "ticket_version_conflict"


def add_user(
    db: Session,
    *,
    username: str,
    role: UserRole,
    active: bool = True,
) -> User:
    user = create_user(
        db,
        username=username,
        password="test-pass",
        role=role,
        display_name=f"{username} display",
    )
    user.is_active = active
    db.commit()
    return user


def login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test-pass"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_ticket(
    client: TestClient,
    token: str,
    *,
    ticket_type: str = "REQ",
    title: str = "支持新测试需求",
    body: str = "正文",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/tickets",
        json={"ticket_type": ticket_type, "title": title, "body": body},
        headers=headers(token),
    )
    assert response.status_code == 201
    return response.json()


def test_ticket_submitter_can_create_edit_and_everyone_can_read(
    client: TestClient,
    db_session: Session,
) -> None:
    submitter = add_user(db_session, username="te1", role=UserRole.TE)
    add_user(db_session, username="tse1", role=UserRole.TSE)
    submitter_token = login(client, "te1")
    viewer_token = login(client, "tse1")

    ticket = create_ticket(
        client,
        submitter_token,
        title="<script>alert('x')</script>",
        body="select * from tickets;\n第二行",
    )
    assert ticket["title"] == "<script>alert('x')</script>"
    assert ticket["body"] == "select * from tickets;\n第二行"
    updated = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        json={"title": "更新后的标题", "body": "更新后的正文"},
        headers=headers(submitter_token),
    )
    detail = client.get(
        f"/api/v1/tickets/{ticket['id']}",
        headers=headers(viewer_token),
    )

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["title"] == "更新后的标题"
    assert detail.json()["body"] == "更新后的正文"
    assert detail.json()["submitter_user_id"] == submitter.id
    assert detail.json()["comments"] == []
    assert (
        db_session.scalars(
            select(AuditLog).where(AuditLog.action.not_like("auth.%"))
        ).all()
        == []
    )


def test_only_pending_submitter_can_edit_ticket(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    add_user(db_session, username="te2", role=UserRole.TE)
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    te1_token = login(client, "te1")
    te2_token = login(client, "te2")
    admin_token = login(client, "admin")
    ticket = create_ticket(client, te1_token)

    other_edit = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        json={"title": "越权修改"},
        headers=headers(te2_token),
    )
    accepted = client.post(
        f"/api/v1/tickets/{ticket['id']}/accept",
        json={
            "priority": "HIGH",
            "assignee_user_id": admin.id,
            "planned_completion_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
        headers=headers(admin_token),
    )
    late_edit = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        json={"body": "状态变化后修改"},
        headers=headers(te1_token),
    )

    assert other_edit.status_code == 403
    assert accepted.status_code == 200
    assert late_edit.status_code == 409
    assert late_edit.json()["error"]["code"] == "ticket_state_conflict"


def test_admin_submitter_cannot_edit_ticket_content(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="admin", role=UserRole.ADMIN)
    admin_token = login(client, "admin")
    ticket = create_ticket(client, admin_token)

    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        json={"title": "管理员修改"},
        headers=headers(admin_token),
    )

    assert response.status_code == 403


def test_ticket_content_update_rejects_explicit_null(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    token = login(client, "te1")
    ticket = create_ticket(client, token)

    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        json={"title": None},
        headers=headers(token),
    )

    assert response.status_code == 422


def test_admin_can_accept_adjust_and_complete_ticket(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    assignee = add_user(db_session, username="admin2", role=UserRole.ADMIN)
    submitter_token = login(client, "te1")
    admin_token = login(client, "admin")
    ticket = create_ticket(client, submitter_token)

    accepted = client.post(
        f"/api/v1/tickets/{ticket['id']}/accept",
        json={
            "priority": "MEDIUM",
            "assignee_user_id": assignee.id,
            "planned_completion_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
        headers=headers(admin_token),
    )
    adjusted = client.patch(
        f"/api/v1/tickets/{ticket['id']}/handling",
        json={
            "priority": "HIGH",
            "assignee_user_id": admin.id,
            "planned_completion_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
        headers=headers(admin_token),
    )
    completed = client.post(
        f"/api/v1/tickets/{ticket['id']}/complete",
        headers=headers(admin_token),
    )

    assert accepted.status_code == 200
    assert adjusted.status_code == 200
    assert adjusted.json()["priority"] == "HIGH"
    assert adjusted.json()["assignee_user_id"] == admin.id
    assert adjusted.json()["is_overdue"] is True
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["completed_at"] is not None
    assert completed.json()["is_overdue"] is False


def test_accept_requires_active_admin_and_future_planned_time(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    inactive = add_user(
        db_session,
        username="admin2",
        role=UserRole.ADMIN,
        active=False,
    )
    submitter_token = login(client, "te1")
    admin_token = login(client, "admin")
    ticket = create_ticket(client, submitter_token)

    inactive_assignee = client.post(
        f"/api/v1/tickets/{ticket['id']}/accept",
        json={
            "priority": "LOW",
            "assignee_user_id": inactive.id,
            "planned_completion_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
        headers=headers(admin_token),
    )
    past_time = client.post(
        f"/api/v1/tickets/{ticket['id']}/accept",
        json={
            "priority": "LOW",
            "assignee_user_id": admin.id,
            "planned_completion_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        },
        headers=headers(admin_token),
    )

    assert inactive_assignee.status_code == 400
    assert past_time.status_code == 400


def test_non_admin_cannot_process_ticket(
    client: TestClient,
    db_session: Session,
) -> None:
    te = add_user(db_session, username="te1", role=UserRole.TE)
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    token = login(client, "te1")
    ticket = create_ticket(client, token)
    payload = {
        "priority": "LOW",
        "assignee_user_id": admin.id,
        "planned_completion_at": (
            datetime.now(UTC) + timedelta(days=1)
        ).isoformat(),
    }

    accepted = client.post(
        f"/api/v1/tickets/{ticket['id']}/accept",
        json=payload,
        headers=headers(token),
    )
    rejected = client.post(
        f"/api/v1/tickets/{ticket['id']}/reject",
        json={"reason": "越权拒绝"},
        headers=headers(token),
    )
    completed = client.post(
        f"/api/v1/tickets/{ticket['id']}/complete",
        headers=headers(token),
    )

    assert te.role == UserRole.TE.value
    assert accepted.status_code == 403
    assert rejected.status_code == 403
    assert completed.status_code == 403


def test_admin_can_reject_once_with_username_prefix(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    add_user(db_session, username="admin", role=UserRole.ADMIN)
    submitter_token = login(client, "te1")
    admin_token = login(client, "admin")
    ticket = create_ticket(client, submitter_token)

    rejected = client.post(
        f"/api/v1/tickets/{ticket['id']}/reject",
        json={"reason": "信息不足"},
        headers=headers(admin_token),
    )
    repeated = client.post(
        f"/api/v1/tickets/{ticket['id']}/reject",
        json={"reason": "再次拒绝"},
        headers=headers(admin_token),
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["rejection_reason"] == "[admin] 信息不足"
    assert repeated.status_code == 409


def test_ticket_comment_permissions_and_order(
    client: TestClient,
    db_session: Session,
) -> None:
    add_user(db_session, username="te1", role=UserRole.TE)
    add_user(db_session, username="te2", role=UserRole.TE)
    admin = add_user(db_session, username="admin", role=UserRole.ADMIN)
    submitter_token = login(client, "te1")
    outsider_token = login(client, "te2")
    admin_token = login(client, "admin")
    ticket = create_ticket(client, submitter_token)
    original_updated_at = ticket["updated_at"]

    denied = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "无权评论"},
        headers=headers(outsider_token),
    )
    first = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "提交人评论"},
        headers=headers(submitter_token),
    )
    second = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "管理员评论"},
        headers=headers(admin_token),
    )

    assert denied.status_code == 403
    assert first.status_code == 201
    assert second.status_code == 201
    assert [comment["body"] for comment in second.json()["comments"]] == [
        "提交人评论",
        "管理员评论",
    ]
    assert second.json()["updated_at"] == original_updated_at
    assert second.json()["comments"][1]["author_user_id"] == admin.id


def test_ticket_filters_and_fixed_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    submitter = add_user(db_session, username="te1", role=UserRole.TE)
    token = login(client, "te1")
    db_session.add_all(
        [
            Ticket(
                submitter_user_id=submitter.id,
                ticket_type="BUG" if index % 2 else "REQ",
                title=f"network issue {index}",
                body="body",
                status="PENDING",
            )
            for index in range(51)
        ]
    )
    db_session.commit()

    first = client.get(
        "/api/v1/tickets",
        params={"page": 1, "ticket_type": "BUG", "title": "network"},
        headers=headers(token),
    )
    second = client.get(
        "/api/v1/tickets",
        params={"page": 2},
        headers=headers(token),
    )
    or_filtered = client.get(
        "/api/v1/tickets",
        params={"match": "or", "ticket_id": 1, "ticket_type": "BUG"},
        headers=headers(token),
    )
    unset_priority = client.get(
        "/api/v1/tickets",
        params={"priority": "UNSET"},
        headers=headers(token),
    )

    assert first.status_code == 200
    assert first.json()["total"] == 25
    assert first.json()["items"][0]["id"] > first.json()["items"][-1]["id"]
    assert second.json()["total"] == 51
    assert len(second.json()["items"]) == 1
    assert or_filtered.json()["total"] == 26
    assert unset_priority.json()["total"] == 51

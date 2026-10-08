# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Generator
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.feishu.models import (
    ExternalIdentityProvider,
    FeishuAppConfig,
    UserIdentity,
)
from app.modules.leases.models import ResourceLease
from app.modules.notifications import delivery
from app.modules.notifications import tasks as notification_tasks
from app.modules.notifications.delivery import deliver_feishu_notification
from app.modules.notifications.models import (
    FeishuDeliveryStatus,
    Notification,
    NotificationTargetType,
    NotificationType,
)
from app.modules.notifications.service import (
    cleanup_expired_notifications,
    create_expiration_reminders,
)
from app.modules.resources.models import Resource, ResourceType
from app.modules.tickets import commands as ticket_commands
from app.modules.tickets.models import Ticket, TicketStatus
from app.modules.users.models import User, UserRole
from app.modules.users.service import create_user
from app.worker import celery_app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
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


def add_user(db: Session, *, username: str, role: UserRole = UserRole.TE) -> User:
    user = create_user(
        db,
        username=username,
        password="test-pass",
        role=role,
        display_name=f"{username} display",
    )
    db.commit()
    return user


def login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test-pass"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_notification(
    db: Session,
    *,
    recipient_user_id: str,
    key: str,
    read: bool = False,
) -> Notification:
    notification = Notification(
        recipient_user_id=recipient_user_id,
        notification_type=NotificationType.TICKET_UPDATED.value,
        title="工单已更新",
        body="通知正文",
        target_type=NotificationTargetType.TICKET.value,
        target_id="1",
        target_url="/tickets/1",
        deduplication_key=key,
        read_at=datetime.now(UTC) if read else None,
    )
    db.add(notification)
    db.commit()
    return notification


def test_notification_api_isolates_users_and_marks_read(
    client: TestClient,
    db_session: Session,
) -> None:
    user = add_user(db_session, username="te1")
    other = add_user(db_session, username="te2")
    own_unread = add_notification(db_session, recipient_user_id=user.id, key="own-unread")
    add_notification(db_session, recipient_user_id=user.id, key="own-read", read=True)
    other_notification = add_notification(
        db_session,
        recipient_user_id=other.id,
        key="other-unread",
    )
    auth = login(client, "te1")

    listed = client.get("/api/v1/notifications", headers=auth)
    count = client.get("/api/v1/notifications/unread-count", headers=auth)
    denied = client.patch(
        f"/api/v1/notifications/{other_notification.id}/read",
        headers=auth,
    )
    marked = client.patch(
        f"/api/v1/notifications/{own_unread.id}/read",
        headers=auth,
    )
    all_read = client.post("/api/v1/notifications/read-all", headers=auth)

    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert listed.json()["items"][0]["id"] == own_unread.id
    assert count.json() == {"count": 1}
    assert denied.status_code == 404
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None
    assert all_read.json() == {"count": 0}


def test_notification_api_uses_fixed_fifty_item_pages(
    client: TestClient,
    db_session: Session,
) -> None:
    user = add_user(db_session, username="te1")
    db_session.add_all(
        [
            Notification(
                recipient_user_id=user.id,
                notification_type=NotificationType.TICKET_UPDATED.value,
                title=f"通知 {index}",
                body="通知正文",
                deduplication_key=f"page-{index}",
            )
            for index in range(51)
        ]
    )
    db_session.commit()
    auth = login(client, "te1")

    first_page = client.get("/api/v1/notifications?page=1", headers=auth)
    second_page = client.get("/api/v1/notifications?page=2", headers=auth)

    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 50
    assert first_page.json()["total"] == 51
    assert len(second_page.json()["items"]) == 1


def test_ticket_notifications_follow_recipient_rules(
    client: TestClient,
    db_session: Session,
) -> None:
    submitter = add_user(db_session, username="te1")
    actor = add_user(db_session, username="admin1", role=UserRole.ADMIN)
    first_assignee = add_user(db_session, username="admin2", role=UserRole.ADMIN)
    submitter_auth = login(client, "te1")
    actor_auth = login(client, "admin1")
    ticket = client.post(
        "/api/v1/tickets",
        json={"ticket_type": "REQ", "title": "通知测试", "body": "正文"},
        headers=submitter_auth,
    ).json()

    accepted = client.post(
        f"/api/v1/tickets/{ticket['id']}/accept",
        json={
            "priority": "MEDIUM",
            "assignee_user_id": first_assignee.id,
            "planned_completion_at": (
                datetime.now(UTC) + timedelta(days=2)
            ).isoformat(),
        },
        headers=actor_auth,
    )
    reassigned = client.patch(
        f"/api/v1/tickets/{ticket['id']}/handling",
        json={
            "assignee_user_id": actor.id,
            "priority": "HIGH",
            "planned_completion_at": (
                datetime.now(UTC) + timedelta(days=3)
            ).isoformat(),
        },
        headers=actor_auth,
    )
    commented = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "管理员回复"},
        headers=actor_auth,
    )
    updated = client.patch(
        f"/api/v1/tickets/{ticket['id']}/handling",
        json={"priority": "LOW"},
        headers=actor_auth,
    )
    completed = client.post(
        f"/api/v1/tickets/{ticket['id']}/complete",
        headers=actor_auth,
    )
    rejected_ticket = client.post(
        "/api/v1/tickets",
        json={"ticket_type": "BUG", "title": "拒绝测试", "body": "正文"},
        headers=submitter_auth,
    ).json()
    rejected = client.post(
        f"/api/v1/tickets/{rejected_ticket['id']}/reject",
        json={"reason": "暂不处理"},
        headers=actor_auth,
    )

    assert accepted.status_code == 200
    assert reassigned.status_code == 200
    assert commented.status_code == 201
    assert updated.status_code == 200
    assert completed.status_code == 200
    assert rejected.status_code == 200
    notifications = db_session.scalars(
        select(Notification).order_by(Notification.created_at, Notification.id)
    ).all()
    assigned = [
        item
        for item in notifications
        if item.notification_type == NotificationType.TICKET_ASSIGNED.value
    ]
    reassignment = [
        item
        for item in notifications
        if item.notification_type == NotificationType.TICKET_REASSIGNED.value
    ]
    comments = [
        item
        for item in notifications
        if item.notification_type == NotificationType.TICKET_COMMENTED.value
    ]
    assert {item.recipient_user_id for item in assigned} == {
        submitter.id,
        first_assignee.id,
    }
    assert {item.recipient_user_id for item in reassignment} == {
        submitter.id,
        first_assignee.id,
    }
    assert len(reassignment) == 2
    assert [item.recipient_user_id for item in comments] == [submitter.id]
    for notification_type in (
        NotificationType.TICKET_UPDATED,
        NotificationType.TICKET_COMPLETED,
        NotificationType.TICKET_REJECTED,
    ):
        matching = [
            item
            for item in notifications
            if item.notification_type == notification_type.value
        ]
        assert [item.recipient_user_id for item in matching] == [submitter.id]
    assert "优先级" in reassignment[0].body
    assert all(item.recipient_user_id != actor.id for item in notifications)


def test_expiration_reminders_deduplicate_and_follow_latest_end_time(
    db_session: Session,
) -> None:
    user = add_user(db_session, username="te1")
    resource = Resource(
        resource_code="physical-1",
        resource_type=ResourceType.PHYSICAL.value,
        name="不会出现在提醒中的设备名称",
        primary_ip="172.168.131.75",
        ssh_username="root",
        ssh_password_ciphertext="encrypted",
    )
    db_session.add(resource)
    db_session.flush()
    current_time = datetime(2026, 7, 17, 1, 0, tzinfo=UTC)
    lease = ResourceLease(
        resource_id=resource.id,
        user_id=user.id,
        purpose="通知测试",
        expected_ends_at=datetime(2026, 7, 20, 4, 0, tzinfo=UTC),
    )
    db_session.add(lease)
    db_session.commit()

    first = create_expiration_reminders(db_session, current_time=current_time)
    second = create_expiration_reminders(db_session, current_time=current_time)
    lease.expected_ends_at = datetime(2026, 7, 21, 4, 0, tzinfo=UTC)
    third = create_expiration_reminders(
        db_session,
        current_time=current_time + timedelta(days=1),
    )
    db_session.commit()

    reminders = db_session.scalars(
        select(Notification).where(
            Notification.notification_type == NotificationType.LEASE_EXPIRING.value
        )
    ).all()
    assert first == []
    assert second == []
    assert third == []
    assert len(reminders) == 2
    assert all(item.feishu_status is None for item in reminders)
    assert reminders[0].target_url.startswith("/resources?resource_id=")
    assert "172.168.131.75" in reminders[0].body
    assert resource.name not in reminders[0].body


def test_ticket_change_rolls_back_when_notification_write_fails(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    add_user(db_session, username="te1")
    add_user(db_session, username="admin1", role=UserRole.ADMIN)
    assignee = add_user(db_session, username="admin2", role=UserRole.ADMIN)
    submitter_auth = login(client, "te1")
    actor_auth = login(client, "admin1")
    ticket = client.post(
        "/api/v1/tickets",
        json={"ticket_type": "REQ", "title": "事务测试", "body": "正文"},
        headers=submitter_auth,
    ).json()

    def fail_notification(*_args: object, **_kwargs: object) -> list[Notification]:
        raise RuntimeError("notification write failed")

    monkeypatch.setattr(ticket_commands, "notify_ticket_change", fail_notification)
    response = client.post(
        f"/api/v1/tickets/{ticket['id']}/accept",
        json={
            "priority": "MEDIUM",
            "assignee_user_id": assignee.id,
            "planned_completion_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
        headers=actor_auth,
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    stored = db_session.get(Ticket, ticket["id"])
    assert stored is not None
    assert stored.status == TicketStatus.PENDING.value


def test_notification_cleanup_and_beat_schedule(db_session: Session) -> None:
    user = add_user(db_session, username="te1")
    old = add_notification(db_session, recipient_user_id=user.id, key="old")
    old.created_at = datetime.now(UTC) - timedelta(days=91)
    recent = add_notification(db_session, recipient_user_id=user.id, key="recent")
    db_session.commit()
    old_id = old.id
    recent_id = recent.id

    deleted = cleanup_expired_notifications(db_session)
    db_session.commit()

    assert deleted == 1
    assert db_session.get(Notification, old_id) is None
    assert db_session.get(Notification, recent_id) is not None
    schedule = celery_app.conf.beat_schedule["daily-notification-maintenance"]
    assert schedule["task"] == "app.modules.notifications.tasks.daily_maintenance"
    assert celery_app.conf.beat_cron_starting_deadline == 60
    cron = schedule["schedule"]
    original_nowfun = cron.nowfun

    def _fixed_now() -> datetime:
        return datetime(2026, 7, 17, 12, tzinfo=ZoneInfo("Asia/Shanghai"))

    try:
        cron.nowfun = _fixed_now
        stale = cron.is_due(
            datetime(2026, 7, 16, 9, tzinfo=ZoneInfo("Asia/Shanghai"))
        )
    finally:
        cron.nowfun = original_nowfun
    assert stale.is_due is False


def test_feishu_enqueue_failure_is_recorded(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = add_user(db_session, username="te1")
    notification = Notification(
        recipient_user_id=user.id,
        notification_type=NotificationType.LEASE_EXPIRING.value,
        title="资源即将到期",
        body="物理机：172.168.131.75",
        deduplication_key="enqueue-failure",
        feishu_status=FeishuDeliveryStatus.PENDING.value,
    )
    db_session.add(notification)
    db_session.commit()
    monkeypatch.setattr(
        notification_tasks,
        "SessionLocal",
        lambda: nullcontext(db_session),
    )
    monkeypatch.setattr(
        notification_tasks,
        "run_daily_maintenance",
        lambda _db: [notification.id],
    )

    def fail_enqueue(_notification_id: str) -> None:
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(
        notification_tasks.deliver_feishu_notification_task,
        "delay",
        fail_enqueue,
    )

    notification_tasks.daily_notification_maintenance.run()

    db_session.refresh(notification)
    assert notification.feishu_status == FeishuDeliveryStatus.FAILED.value
    assert notification.feishu_error is not None
    assert "broker unavailable" in notification.feishu_error


def test_feishu_delivery_uses_open_id_and_records_failure(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = add_user(db_session, username="te1")
    db_session.add_all(
        [
            FeishuAppConfig(
                environment="development",
                app_id="app-id",
                app_secret="app-secret",
                is_enabled=True,
            ),
            UserIdentity(
                user_id=user.id,
                provider=ExternalIdentityProvider.FEISHU.value,
                open_id="open-id",
            ),
        ]
    )
    notification = Notification(
        recipient_user_id=user.id,
        notification_type=NotificationType.LEASE_EXPIRING.value,
        title="VM 将在 3 天后到期",
        body="VM：vm-1",
        target_type=NotificationTargetType.VIRTUAL_MACHINE.value,
        target_id="resource-id",
        target_url="/virtual-machines?vm_id=resource-id",
        deduplication_key="delivery-test",
        feishu_status=FeishuDeliveryStatus.PENDING.value,
    )
    db_session.add(notification)
    db_session.commit()

    sent: list[tuple[str, dict[str, object]]] = []

    class SuccessfulSender:
        def __init__(self, **_kwargs: str) -> None:
            pass

        @staticmethod
        def send_card_to_open_id(
            open_id: str,
            card: dict[str, object],
        ) -> None:
            sent.append((open_id, card))

    monkeypatch.setattr(delivery, "LarkMessageSender", SuccessfulSender)
    deliver_feishu_notification(db_session, notification_id=notification.id)
    db_session.refresh(notification)
    assert sent[0][0] == "open-id"
    assert notification.feishu_status == FeishuDeliveryStatus.SENT.value

    notification.feishu_status = FeishuDeliveryStatus.PENDING.value
    notification.feishu_sent_at = None
    db_session.commit()

    class FailingSender:
        def __init__(self, **_kwargs: str) -> None:
            pass

        @staticmethod
        def send_card_to_open_id(
            _open_id: str,
            _card: dict[str, object],
        ) -> None:
            raise RuntimeError("temporary failure")

    monkeypatch.setattr(delivery, "LarkMessageSender", FailingSender)
    with pytest.raises(RuntimeError, match="temporary failure"):
        deliver_feishu_notification(db_session, notification_id=notification.id)

    db_session.refresh(notification)
    assert notification.feishu_status == FeishuDeliveryStatus.PENDING.value
    assert notification.feishu_error is None


def test_feishu_delivery_is_failed_only_after_retries_are_exhausted(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = add_user(db_session, username="te1")
    notification = Notification(
        recipient_user_id=user.id,
        notification_type=NotificationType.LEASE_EXPIRING.value,
        title="VM 将在 3 天后到期",
        body="VM：vm-1",
        target_type=NotificationTargetType.VIRTUAL_MACHINE.value,
        target_id="resource-id",
        target_url="/virtual-machines?vm_id=resource-id",
        deduplication_key="retry-test",
        feishu_status=FeishuDeliveryStatus.PENDING.value,
    )
    db_session.add(notification)
    db_session.commit()

    def fail_delivery(_db: Session, *, notification_id: str) -> None:
        assert notification_id == notification.id
        raise RuntimeError("temporary failure")

    task = notification_tasks.deliver_feishu_notification_task
    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(notification_tasks, "deliver_feishu_notification", fail_delivery)
    monkeypatch.setattr(
        task,
        "retry",
        lambda **_kwargs: RuntimeError("retry scheduled"),
    )

    original_retries = task.request.retries
    try:
        task.request.retries = 0
        with pytest.raises(RuntimeError, match="retry scheduled"):
            task.run(notification.id)
        db_session.refresh(notification)
        assert notification.feishu_status == FeishuDeliveryStatus.PENDING.value
        assert notification.feishu_error is None

        task.request.retries = task.max_retries
        with pytest.raises(RuntimeError, match="temporary failure"):
            task.run(notification.id)
        db_session.refresh(notification)
        assert notification.feishu_status == FeishuDeliveryStatus.FAILED.value
        assert notification.feishu_error == "temporary failure"
    finally:
        task.request.retries = original_retries

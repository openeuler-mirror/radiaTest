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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.leases.models import LeaseEvent, ResourceLease
from app.modules.resources.models import OccupancyStatus, Resource
from app.modules.test_management.models import TestEnvNode, TestEnvSet, TestJob
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


def login_as(
    client: TestClient,
    db_session: Session,
    *,
    username: str,
    role: UserRole,
) -> str:
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


def auth_header(token: str, *, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def physical_resource_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "resource_code": "SN000000000001",
        "resource_type": "PHYSICAL",
        "name": "TaiShan 200",
        "primary_ip": "10.0.0.75",
        "mac_address": "aa:bb:cc:dd:ee:75",
        "arch": "aarch64",
        "os_version": "openEuler 24.03 (LTS-SP4)",
        "kernel_version": "6.6.0-test.aarch64",
        "ssh_username": "root",
        "ssh_password": "ssh-pass",
        "bmc_ip": "10.1.0.75",
        "bmc_username": "Administrator",
        "bmc_password": "bmc-pass",
        "cpu_model": "Kunpeng-920",
        "cpu_count": 2,
        "memory_count": 12,
        "memory_spec": "12 x 32GB DDR4 2933MT/s",
        "ssd_count": 2,
        "ssd_spec": "2 x 3841GB SSD",
        "hdd_count": 0,
        "board_sn": "BOARD0000000001",
    }
    payload.update(overrides)
    return payload


def create_resource(
    client: TestClient,
    token: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/resources",
        json=payload or physical_resource_payload(),
        headers=auth_header(token),
    )

    assert response.status_code == 201
    return response.json()


def lease_payload(days: int = 1) -> dict[str, object]:
    return {
        "purpose": "调试 openEuler",
        "expected_ends_at": (datetime.now(UTC) + timedelta(days=days)).isoformat(),
    }


def occupy_resource(
    client: TestClient,
    token: str,
    resource_id: str,
    *,
    key: str = "occupy-key",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/resources/{resource_id}/leases",
        json=payload or lease_payload(),
        headers=auth_header(token, key=key),
    )
    assert response.status_code == 201
    return response.json()


def mark_resource_testing(
    db: Session,
    *,
    resource_id: str,
    user_id: str,
) -> None:
    job = TestJob(
        creator_user_id=user_id,
        name="active-physical-test",
        status="running",
        framework="mugen",
        env_type="physical",
        dist="openEuler",
        os_version="24.03-LTS-SP4",
        image_round="round-1",
        arch="aarch64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_failed_env=False,
    )
    env_set = TestEnvSet(job=job, set_index=1, node_num=1, status="running")
    TestEnvNode(
        env_set=env_set,
        node_index=0,
        role="control",
        status="ready",
        resource_id=resource_id,
    )
    db.add(job)
    db.commit()


def test_te_can_occupy_view_credentials_and_release_own_resource(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_resource(client, admin_token)

    lease = occupy_resource(client, te_token, resource["id"])

    resources_response = client.get("/api/v1/resources", headers=auth_header(te_token))
    assert resources_response.status_code == 200
    listed = resources_response.json()["items"][0]
    assert listed["occupancy_status"] == "occupied"
    assert listed["current_lease_id"] == lease["id"]
    assert listed["current_lease_username"] == "te1"

    credentials_response = client.get(
        f"/api/v1/resources/{resource['id']}/credentials",
        headers=auth_header(te_token),
    )
    assert credentials_response.status_code == 200
    assert credentials_response.json() == {
        "ssh_username": "root",
        "ssh_password": "ssh-pass",
        "bmc_username": "Administrator",
        "bmc_password": "bmc-pass",
    }

    release_response = client.post(
        f"/api/v1/leases/{lease['id']}/release",
        json={"reason": "用完释放"},
        headers=auth_header(te_token, key="release-key"),
    )

    assert release_response.status_code == 200
    assert release_response.json()["released_by_user_id"] == release_response.json()["user_id"]
    db_session.refresh(db_session.get(Resource, resource["id"]))
    assert db_session.get(Resource, resource["id"]).occupancy_status == OccupancyStatus.IDLE.value

    denied_credentials = client.get(
        f"/api/v1/resources/{resource['id']}/credentials",
        headers=auth_header(te_token),
    )
    assert denied_credentials.status_code == 403


def test_release_rejects_physical_machine_under_test(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="adminbusy", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="tebusy", role=UserRole.TE)
    resource = create_resource(client, admin_token)
    lease = occupy_resource(client, te_token, resource["id"], key="busy-lease")
    user = db_session.scalar(select(User).where(User.username == "tebusy"))
    assert user is not None
    mark_resource_testing(db_session, resource_id=resource["id"], user_id=user.id)

    response = client.post(
        f"/api/v1/leases/{lease['id']}/release",
        json={"reason": "must-not-release"},
        headers=auth_header(te_token, key="busy-release"),
    )

    assert response.status_code == 409


def test_lease_owner_can_extend_until_seven_days_from_now(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_resource(client, admin_token)
    lease = occupy_resource(client, te_token, resource["id"])
    new_end = datetime.now(UTC) + timedelta(days=3)

    response = client.post(
        f"/api/v1/leases/{lease['id']}/extend",
        json={"expected_ends_at": new_end.isoformat()},
        headers=auth_header(te_token, key="extend-key"),
    )

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["expected_ends_at"]) > datetime.fromisoformat(
        lease["expected_ends_at"],
    )
    event = db_session.execute(
        select(LeaseEvent).where(LeaseEvent.lease_id == lease["id"]),
    ).scalars().all()[-1]
    assert event.event_type == "extend"


def test_lease_extension_allows_one_minute_deadline_tolerance(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_resource(client, admin_token)
    lease = occupy_resource(client, te_token, resource["id"])

    accepted = client.post(
        f"/api/v1/leases/{lease['id']}/extend",
        json={
            "expected_ends_at": (
                datetime.now(UTC) + timedelta(days=7, seconds=30)
            ).isoformat(),
        },
        headers=auth_header(te_token, key="extend-within-tolerance"),
    )
    rejected = client.post(
        f"/api/v1/leases/{lease['id']}/extend",
        json={
            "expected_ends_at": (
                datetime.now(UTC) + timedelta(days=7, minutes=2)
            ).isoformat(),
        },
        headers=auth_header(te_token, key="extend-outside-tolerance"),
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 403


def test_lease_extension_must_be_owned_and_within_seven_days(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    other_token = login_as(client, db_session, username="te2", role=UserRole.TE)
    resource = create_resource(client, admin_token)
    lease = occupy_resource(client, te_token, resource["id"])

    too_long = client.post(
        f"/api/v1/leases/{lease['id']}/extend",
        json={"expected_ends_at": (datetime.now(UTC) + timedelta(days=8)).isoformat()},
        headers=auth_header(te_token, key="extend-too-long"),
    )
    other_user = client.post(
        f"/api/v1/leases/{lease['id']}/extend",
        json={"expected_ends_at": (datetime.now(UTC) + timedelta(days=2)).isoformat()},
        headers=auth_header(other_token, key="extend-other"),
    )

    assert too_long.status_code == 403
    assert other_user.status_code == 403


def test_non_admin_lease_must_be_finite_within_fourteen_days(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_resource(client, admin_token)

    missing_end = client.post(
        f"/api/v1/resources/{resource['id']}/leases",
        json={"purpose": "无截止时间"},
        headers=auth_header(te_token, key="missing-end"),
    )
    too_long = client.post(
        f"/api/v1/resources/{resource['id']}/leases",
        json=lease_payload(days=15),
        headers=auth_header(te_token, key="too-long"),
    )

    assert missing_end.status_code == 403
    assert too_long.status_code == 403


def test_non_admin_lease_allows_one_minute_deadline_tolerance(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    within_tolerance = create_resource(client, admin_token)
    outside_tolerance = create_resource(
        client,
        admin_token,
        physical_resource_payload(
            resource_code="SN000000000002",
            primary_ip="10.0.0.76",
            mac_address="aa:bb:cc:dd:ee:76",
            bmc_ip="10.1.0.76",
        ),
    )

    accepted = client.post(
        f"/api/v1/resources/{within_tolerance['id']}/leases",
        json={
            "purpose": "边界容差",
            "expected_ends_at": (
                datetime.now(UTC) + timedelta(days=14, seconds=30)
            ).isoformat(),
        },
        headers=auth_header(te_token, key="within-tolerance"),
    )
    rejected = client.post(
        f"/api/v1/resources/{outside_tolerance['id']}/leases",
        json={
            "purpose": "超过容差",
            "expected_ends_at": (
                datetime.now(UTC) + timedelta(days=14, minutes=2)
            ).isoformat(),
        },
        headers=auth_header(te_token, key="outside-tolerance"),
    )

    assert accepted.status_code == 201
    assert rejected.status_code == 403


def test_only_admin_can_occupy_or_view_critical_resource_credentials(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_resource(
        client,
        admin_token,
        physical_resource_payload(is_critical=True),
    )

    te_occupy = client.post(
        f"/api/v1/resources/{resource['id']}/leases",
        json=lease_payload(),
        headers=auth_header(te_token, key="critical-te"),
    )
    admin_occupy = client.post(
        f"/api/v1/resources/{resource['id']}/leases",
        json={"purpose": "关键资源长期占用"},
        headers=auth_header(admin_token, key="critical-admin"),
    )
    credentials_response = client.get(
        f"/api/v1/resources/{resource['id']}/credentials",
        headers=auth_header(admin_token),
    )

    assert te_occupy.status_code == 403
    assert admin_occupy.status_code == 201
    assert admin_occupy.json()["expected_ends_at"] is None
    assert credentials_response.status_code == 200


def test_tse_can_force_release_te_lease_but_not_tse_lease(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    tse_token = login_as(client, db_session, username="tse", role=UserRole.TSE)
    te_resource = create_resource(client, admin_token)
    tse_resource = create_resource(
        client,
        admin_token,
        physical_resource_payload(
            resource_code="SN000000000002",
            primary_ip="10.0.0.76",
            bmc_ip="10.1.0.76",
        ),
    )
    te_lease = occupy_resource(client, te_token, te_resource["id"], key="te-occupy")
    tse_lease = occupy_resource(client, tse_token, tse_resource["id"], key="tse-occupy")

    force_te = client.post(
        f"/api/v1/leases/{te_lease['id']}/force-release",
        json={"reason": "调度回收"},
        headers=auth_header(tse_token, key="force-te"),
    )
    force_tse = client.post(
        f"/api/v1/leases/{tse_lease['id']}/force-release",
        json={"reason": "越权回收"},
        headers=auth_header(tse_token, key="force-tse"),
    )

    assert force_te.status_code == 200
    assert force_tse.status_code == 403


def test_idempotency_key_replays_same_response_and_rejects_changed_request(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_resource(client, admin_token)
    payload = lease_payload()

    first = client.post(
        f"/api/v1/resources/{resource['id']}/leases",
        json=payload,
        headers=auth_header(te_token, key="same-key"),
    )
    replay = client.post(
        f"/api/v1/resources/{resource['id']}/leases",
        json=payload,
        headers=auth_header(te_token, key="same-key"),
    )
    changed = client.post(
        f"/api/v1/resources/{resource['id']}/leases",
        json={**payload, "purpose": "不同用途"},
        headers=auth_header(te_token, key="same-key"),
    )

    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
    assert changed.status_code == 409


def test_resource_read_lazily_releases_expired_lease(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource_data = create_resource(client, admin_token)
    resource = db_session.get(Resource, resource_data["id"])
    user = db_session.execute(select(ResourceLease)).scalar_one_or_none()
    assert user is None

    te_user_id = client.get("/api/v1/users/me", headers=auth_header(te_token)).json()["id"]
    lease = ResourceLease(
        resource_id=resource_data["id"],
        user_id=te_user_id,
        purpose="过期测试",
        expected_ends_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(lease)
    db_session.flush()
    resource.current_lease_id = lease.id
    resource.occupancy_status = OccupancyStatus.OCCUPIED.value
    db_session.commit()

    response = client.get(
        f"/api/v1/resources/{resource_data['id']}",
        headers=auth_header(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["occupancy_status"] == "idle"
    assert response.json()["current_lease_id"] is None
    db_session.refresh(lease)
    assert lease.released_at is not None
    events = db_session.execute(select(LeaseEvent)).scalars().all()
    assert [event.event_type for event in events] == ["auto_release"]


def test_lazy_release_is_persisted_before_failed_occupy_attempt(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource_data = create_resource(
        client,
        admin_token,
        physical_resource_payload(is_critical=True),
    )
    resource = db_session.get(Resource, resource_data["id"])
    te_user_id = client.get("/api/v1/users/me", headers=auth_header(te_token)).json()["id"]
    lease = ResourceLease(
        resource_id=resource_data["id"],
        user_id=te_user_id,
        purpose="过期关键资源",
        expected_ends_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(lease)
    db_session.flush()
    resource.current_lease_id = lease.id
    resource.occupancy_status = OccupancyStatus.OCCUPIED.value
    db_session.commit()

    response = client.post(
        f"/api/v1/resources/{resource_data['id']}/leases",
        json=lease_payload(),
        headers=auth_header(te_token, key="failed-after-lazy-release"),
    )

    assert response.status_code == 403
    db_session.refresh(lease)
    db_session.refresh(resource)
    assert lease.released_at is not None
    assert resource.current_lease_id is None
    assert resource.occupancy_status == OccupancyStatus.IDLE.value


def test_database_rejects_two_active_leases_for_same_resource(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource_data = create_resource(client, admin_token)
    te_user_id = client.get("/api/v1/users/me", headers=auth_header(te_token)).json()["id"]
    lease_a = ResourceLease(
        resource_id=resource_data["id"],
        user_id=te_user_id,
        purpose="第一个租约",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
    )
    lease_b = ResourceLease(
        resource_id=resource_data["id"],
        user_id=te_user_id,
        purpose="第二个租约",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
    )

    db_session.add_all([lease_a, lease_b])

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def lease_import_csv(resource_code: str = "SN000000000001") -> str:
    return "\n".join(
        [
            "resource_code,primary_ip,lease_owner,occupancy_status,lease_type,purpose,expected_ends_at",
            f"{resource_code},10.0.0.75,admin,occupied,permanent,CI公共机器,",
        ]
    )


def test_admin_can_preview_and_import_permanent_leases_from_csv(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_resource(client, admin_token)
    payload = {
        "filename": "leases.csv",
        "content": lease_import_csv(resource["resource_code"]),
        "dry_run": True,
    }

    preview = client.post(
        "/api/v1/leases/imports",
        json=payload,
        headers=auth_header(admin_token),
    )

    assert preview.status_code == 200
    assert preview.json()["success_count"] == 1
    assert preview.json()["rows"][0]["status"] == "validated"
    assert db_session.execute(select(ResourceLease)).scalars().all() == []

    missing_key = client.post(
        "/api/v1/leases/imports",
        json={**payload, "dry_run": False},
        headers=auth_header(admin_token),
    )
    assert missing_key.status_code == 400

    imported = client.post(
        "/api/v1/leases/imports",
        json={**payload, "dry_run": False},
        headers=auth_header(admin_token, key="lease-import-1"),
    )

    assert imported.status_code == 200
    body = imported.json()
    assert body["success_count"] == 1
    assert body["error_count"] == 0
    assert body["rows"][0]["status"] == "created"

    lease = db_session.execute(select(ResourceLease)).scalar_one()
    db_session.refresh(db_session.get(Resource, resource["id"]))
    assert lease.expected_ends_at is None
    assert lease.purpose == "CI公共机器"
    assert db_session.get(Resource, resource["id"]).occupancy_status == "occupied"

    replay = client.post(
        "/api/v1/leases/imports",
        json={**payload, "dry_run": False},
        headers=auth_header(admin_token, key="lease-import-1"),
    )
    assert replay.status_code == 200
    assert replay.json() == body
    assert len(db_session.execute(select(ResourceLease)).scalars().all()) == 1

    events = db_session.execute(select(LeaseEvent)).scalars().all()
    assert [event.event_type for event in events] == ["occupy"]
    logs = (
        db_session.execute(
            select(AuditLog).where(AuditLog.action == "lease.import")
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].action == "lease.import"
    assert logs[0].detail["resource_codes"] == [resource["resource_code"]]


def test_lease_import_reports_row_errors(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)

    response = client.post(
        "/api/v1/leases/imports",
        json={
            "filename": "leases.csv",
            "content": lease_import_csv("MISSING-SN"),
            "dry_run": False,
        },
        headers=auth_header(admin_token, key="lease-import-missing-resource"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success_count"] == 0
    assert body["error_count"] == 1
    assert body["rows"][0]["status"] == "error"
    assert body["rows"][0]["errors"] == ["resource_code does not exist"]


def test_non_admin_cannot_import_leases(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="tse", role=UserRole.TSE)

    response = client.post(
        "/api/v1/leases/imports",
        json={
            "filename": "leases.csv",
            "content": lease_import_csv(),
            "dry_run": True,
        },
        headers=auth_header(token),
    )

    assert response.status_code == 403


def test_lease_events_follow_role_visibility_and_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    tse_token = login_as(client, db_session, username="tse", role=UserRole.TSE)
    te1_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    te2_token = login_as(client, db_session, username="te2", role=UserRole.TE)
    resource1 = create_resource(client, admin_token)
    resource2 = create_resource(
        client,
        admin_token,
        physical_resource_payload(
            resource_code="SN000000000002",
            primary_ip="10.0.0.76",
            bmc_ip="10.1.0.76",
        ),
    )
    lease1 = occupy_resource(client, te1_token, str(resource1["id"]), key="occupy-te1")
    lease2 = occupy_resource(client, te2_token, str(resource2["id"]), key="occupy-te2")

    own_response = client.get("/api/v1/lease-events", headers=auth_header(te1_token))
    all_response = client.get("/api/v1/lease-events", headers=auth_header(tse_token))
    filtered_response = client.get(
        "/api/v1/lease-events",
        params={
            "event_type": "occupy",
            "actor_username": "te1",
            "resource_code": resource1["resource_code"],
            "resource_type": "PHYSICAL",
            "primary_ip": "10.0.0.7",
        },
        headers=auth_header(admin_token),
    )
    ip_filtered_response = client.get(
        "/api/v1/lease-events",
        params={"primary_ip": "0.0.76"},
        headers=auth_header(admin_token),
    )
    type_filtered_response = client.get(
        "/api/v1/lease-events",
        params={"resource_type": "VIRTUAL"},
        headers=auth_header(admin_token),
    )

    assert own_response.status_code == 200
    assert [row["lease_id"] for row in own_response.json()["items"]] == [lease1["id"]]
    assert all_response.status_code == 200
    assert all_response.json()["total"] == 2
    assert filtered_response.status_code == 200
    filtered = filtered_response.json()["items"][0]
    assert filtered["resource_code"] == resource1["resource_code"]
    assert filtered["primary_ip"] == resource1["primary_ip"]
    assert filtered["resource_type"] == "PHYSICAL"
    assert filtered["actor_username"] == "te1"
    assert [row["lease_id"] for row in ip_filtered_response.json()["items"]] == [
        lease2["id"]
    ]
    assert type_filtered_response.json()["items"] == []

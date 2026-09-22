# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import csv
import io
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.resources.models import PhysicalResourceSpec, Resource
from app.modules.resources.service import natural_sort_key
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
    payload: dict[str, object],
) -> dict[str, object]:
    response = client.post(
        "/api/v1/resources",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()


def occupy_resource(
    client: TestClient,
    token: str,
    resource_id: str,
    *,
    key: str,
    purpose: str = "调试资源过滤",
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/resources/{resource_id}/leases",
        json={
            "purpose": purpose,
            "expected_ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": key,
        },
    )

    assert response.status_code == 201
    return response.json()


def mark_resource_testing(
    db: Session,
    *,
    resource_id: str,
    user_id: str,
) -> TestJob:
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
    return job


def test_admin_can_create_and_read_physical_resource(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)

    created = create_resource(client, token, physical_resource_payload())

    assert created["resource_code"] == "SN000000000001"
    assert created["resource_type"] == "PHYSICAL"
    assert created["primary_ip"] == "10.0.0.75"
    assert created["has_ssh_password"] is True
    assert created["has_bmc_password"] is True
    assert "ssh_password" not in created
    assert "bmc_password" not in created
    stored_resource = db_session.get(Resource, created["id"])
    stored_physical_spec = db_session.get(PhysicalResourceSpec, created["id"])

    assert stored_resource is not None
    assert stored_resource.ssh_password_ciphertext != "ssh-pass"
    assert stored_resource.ssh_password_ciphertext
    assert stored_physical_spec is not None
    assert stored_physical_spec.bmc_password_ciphertext != "bmc-pass"
    assert stored_physical_spec.bmc_password_ciphertext

    audit_log = db_session.scalar(select(AuditLog).where(AuditLog.action == "resource.create"))
    assert audit_log is not None
    assert audit_log.target_id == created["id"]
    assert audit_log.detail == {
        "resource_code": "SN000000000001",
        "resource_type": "PHYSICAL",
    }
    assert "ssh-pass" not in str(audit_log.detail)
    assert "bmc-pass" not in str(audit_log.detail)

    response = client.get(
        f"/api/v1/resources/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["cpu_model"] == "Kunpeng-920"


def test_resource_read_derives_active_physical_test_status(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="adminstatus", role=UserRole.ADMIN)
    resource = create_resource(client, token, physical_resource_payload())
    user = db_session.scalar(select(User).where(User.username == "adminstatus"))
    assert user is not None
    job = mark_resource_testing(
        db_session,
        resource_id=str(resource["id"]),
        user_id=user.id,
    )

    testing = client.get(
        f"/api/v1/resources/{resource['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert testing.status_code == 200
    assert testing.json()["test_status"] == "testing"
    assert testing.json()["current_test_job_id"] == job.id

    job.status = "succeeded"
    db_session.commit()
    idle = client.get(
        f"/api/v1/resources/{resource['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert idle.json()["test_status"] == "idle"
    assert idle.json()["current_test_job_id"] is None


def test_admin_can_create_install_image_with_round_iso_kernel(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    ISO 模式 install-image：带 round/iso_url/kernel_variant，不填 efi/repo；
    create 返回新字段 + list 含新字段。
    """
    monkeypatch.setattr(
        "app.modules.vms.image_discovery.discover_rc_install_images",
        lambda: [],
    )
    token = login_as(client, db_session, username="adminiso", role=UserRole.ADMIN)
    payload = {
        "os_version": "openEuler-26.09-DevStation",
        "arch": "aarch64",
        "round": "rc3_openeuler-2026-08-28",
        "iso_url": "http://121.36.84.172/dailybuild/openEuler-26.09-DevStation-aarch64-dvd.iso",
        "kernel_variant": "6.18",
    }
    response = client.post(
        "/api/v1/resources/install-images",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    created = response.json()
    assert created["round"] == "rc3_openeuler-2026-08-28"
    assert created["iso_url"] == payload["iso_url"]
    assert created["kernel_variant"] == "6.18"
    assert created["efi_url"] is None
    assert created["repo_url"] is None

    response = client.get(
        "/api/v1/resources/install-images",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    images = response.json()
    assert any(img["round"] == "rc3_openeuler-2026-08-28" for img in images)
    assert any(img["kernel_variant"] == "6.18" for img in images)


def test_te_cannot_create_resource(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)

    response = client.post(
        "/api/v1/resources",
        json=physical_resource_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_tse_cannot_create_or_update_non_active_resource(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    tse_token = login_as(client, db_session, username="tse", role=UserRole.TSE)

    create_maintenance = client.post(
        "/api/v1/resources",
        json=physical_resource_payload(management_status="maintenance"),
        headers={"Authorization": f"Bearer {tse_token}"},
    )
    resource = create_resource(client, admin_token, physical_resource_payload())
    patch_management_status = client.patch(
        f"/api/v1/resources/{resource['id']}",
        json={"management_status": "maintenance"},
        headers={"Authorization": f"Bearer {tse_token}"},
    )
    patch_occupancy_status = client.patch(
        f"/api/v1/resources/{resource['id']}",
        json={"occupancy_status": "occupied"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert create_maintenance.status_code == 403
    assert patch_management_status.status_code == 403
    assert patch_occupancy_status.status_code == 422


def test_admin_can_update_resource_tags_and_audit(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_resource(client, admin_token, physical_resource_payload())

    response = client.patch(
        f"/api/v1/resources/{resource['id']}",
        json={
            "bmc_password": "new-bmc-pass",
            "cpu_count": 128,
            "extra": {"rack_power": "pdu-01"},
            "is_critical": True,
            "ssh_password": "new-ssh-pass",
            "tags": ["vm-host", "ci"],
            "usage_scenario": "CI公共机器",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tags"] == ["vm-host", "ci"]
    assert body["usage_scenario"] == "CI公共机器"
    assert body["cpu_count"] == 128
    assert body["extra"] == {"rack_power": "pdu-01"}
    assert body["is_critical"] is True

    stored_resource = db_session.get(Resource, resource["id"])
    stored_physical_spec = db_session.get(PhysicalResourceSpec, resource["id"])
    assert stored_resource is not None
    assert stored_physical_spec is not None
    assert stored_resource.ssh_password_ciphertext != "new-ssh-pass"
    assert stored_physical_spec.bmc_password_ciphertext != "new-bmc-pass"

    logs = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "resource.update"))
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].target_id == resource["id"]
    assert logs[0].detail == {
        "fields": [
            "bmc_password",
            "cpu_count",
            "extra",
            "is_critical",
            "ssh_password",
            "tags",
            "usage_scenario",
        ],
        "resource_code": resource["resource_code"],
    }


def test_resource_update_rejects_physical_machine_under_test(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="adminbusy", role=UserRole.ADMIN)
    resource = create_resource(client, token, physical_resource_payload())
    user = db_session.scalar(select(User).where(User.username == "adminbusy"))
    assert user is not None
    mark_resource_testing(
        db_session,
        resource_id=str(resource["id"]),
        user_id=user.id,
    )

    response = client.patch(
        f"/api/v1/resources/{resource['id']}",
        json={"name": "must-not-change"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "field_name",
    ["primary_ip", "ssh_password", "bmc_ip", "bmc_username", "bmc_password"],
)
def test_admin_cannot_clear_required_physical_resource_fields(
    client: TestClient,
    db_session: Session,
    field_name: str,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_resource(client, admin_token, physical_resource_payload())

    response = client.patch(
        f"/api/v1/resources/{resource['id']}",
        json={field_name: None},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
    assert field_name in response.json()["error"]["message"]


def test_resource_list_supports_and_or_fuzzy_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    create_resource(
        client,
        token,
        physical_resource_payload(
            resource_code="SN000000000001",
            name="TaiShan 200",
            primary_ip="10.0.0.75",
            arch="aarch64",
            cpu_model="Kunpeng-920",
        ),
    )
    create_resource(
        client,
        token,
        physical_resource_payload(
            resource_code="SN000000000002",
            name="RH2288H V3",
            primary_ip="10.0.0.114",
            mac_address="aa:bb:cc:dd:ee:14",
            arch="x86_64",
            cpu_model="Intel Xeon E5-2680 v3",
            bmc_ip="10.1.0.114",
            board_sn="BOARD0000000002",
        ),
    )

    and_response = client.get(
        "/api/v1/resources?arch=x86&cpu_model=intel&match=and",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert and_response.status_code == 200
    assert and_response.json()["total"] == 1
    assert [resource["primary_ip"] for resource in and_response.json()["items"]] == ["10.0.0.114"]

    or_response = client.get(
        "/api/v1/resources?primary_ip=10.0.0.75&cpu_model=intel&match=or",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert or_response.status_code == 200
    assert or_response.json()["total"] == 2
    assert {resource["primary_ip"] for resource in or_response.json()["items"]} == {
        "10.0.0.75",
        "10.0.0.114",
    }


def test_natural_sort_key_compares_embedded_numbers() -> None:
    assert natural_sort_key("1.11.1") > natural_sort_key("1.3.10")
    assert natural_sort_key("2-2v110") > natural_sort_key("1-10v3")


def test_resource_list_uses_fixed_server_side_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    for index in range(1, 52):
        create_resource(
            client,
            token,
            physical_resource_payload(
                resource_code=f"SNPAGE{index:06d}",
                primary_ip=f"10.20.30.{index}",
                bmc_ip=f"10.21.30.{index}",
            ),
        )

    first_page = client.get(
        "/api/v1/resources?page=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_page = client.get(
        "/api/v1/resources?page=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first_page.status_code == 200
    assert first_page.json()["page"] == 1
    assert first_page.json()["page_size"] == 50
    assert first_page.json()["total"] == 51
    assert len(first_page.json()["items"]) == 50
    assert first_page.json()["items"][0]["primary_ip"] == "10.20.30.1"
    assert first_page.json()["items"][-1]["primary_ip"] == "10.20.30.50"
    assert second_page.status_code == 200
    assert second_page.json()["page"] == 2
    assert second_page.json()["total"] == 51
    assert [item["primary_ip"] for item in second_page.json()["items"]] == ["10.20.30.51"]


def test_resource_list_sorts_naturally_by_primary_ip_and_filters_lease_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource_9 = create_resource(
        client,
        admin_token,
        physical_resource_payload(
            resource_code="SN000000000009",
            primary_ip="172.168.131.9",
            bmc_ip="170.70.30.9",
            usage_scenario="大数据调试",
        ),
    )
    resource_10 = create_resource(
        client,
        admin_token,
        physical_resource_payload(
            resource_code="SN000000000010",
            primary_ip="172.168.131.10",
            bmc_ip="170.70.30.10",
            usage_scenario="CI公共机器",
        ),
    )
    create_resource(
        client,
        admin_token,
        physical_resource_payload(
            resource_code="SN000000000114",
            primary_ip="172.168.131.114",
            bmc_ip="170.70.31.14",
            usage_scenario="内核调试",
        ),
    )
    occupy_resource(
        client,
        te_token,
        resource_10["id"],
        key="occupy-filtered-resource",
        purpose="临时内核验证",
    )

    list_response = client.get(
        "/api/v1/resources",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    occupied_response = client.get(
        "/api/v1/resources?occupancy_status=occupied",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    owner_response = client.get(
        "/api/v1/resources?current_lease_username=te",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    scenario_response = client.get(
        "/api/v1/resources?usage_scenario=大数据",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    scenario_miss_response = client.get(
        "/api/v1/resources?usage_scenario=临时内核验证",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    lease_purpose_response = client.get(
        "/api/v1/resources?current_lease_purpose=临时内核验证",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 3
    assert [resource["primary_ip"] for resource in list_response.json()["items"]] == [
        "172.168.131.9",
        "172.168.131.10",
        "172.168.131.114",
    ]
    assert occupied_response.status_code == 200
    assert [resource["primary_ip"] for resource in occupied_response.json()["items"]] == [
        "172.168.131.10"
    ]
    assert owner_response.status_code == 200
    assert [resource["primary_ip"] for resource in owner_response.json()["items"]] == [
        "172.168.131.10"
    ]
    assert scenario_response.status_code == 200
    assert [resource["primary_ip"] for resource in scenario_response.json()["items"]] == [
        resource_9["primary_ip"]
    ]
    assert scenario_miss_response.status_code == 200
    assert scenario_miss_response.json()["items"] == []
    assert lease_purpose_response.status_code == 200
    assert [resource["primary_ip"] for resource in lease_purpose_response.json()["items"]] == [
        "172.168.131.10"
    ]
    assert lease_purpose_response.json()["items"][0]["usage_scenario"] == "CI公共机器"
    assert lease_purpose_response.json()["items"][0]["current_lease_purpose"] == "临时内核验证"


def test_physical_resource_requires_bmc_credentials(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)

    response = client.post(
        "/api/v1/resources",
        json=physical_resource_payload(bmc_ip=None),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def import_csv_content(resource_code: str = "SNCSV000000001") -> str:
    return "\n".join(
        [
            (
                "resource_code,resource_type,name,primary_ip,ssh_username,ssh_password,"
                "bmc_ip,bmc_username,bmc_password,arch,usage_scenario,legacy_note"
            ),
            (
                f"{resource_code},PHYSICAL,,10.0.0.80,root,ssh-pass,"
                "10.1.0.80,Administrator,bmc-pass,aarch64,CI公共机器,old-note"
            ),
        ]
    )


def parse_export_csv(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.lstrip("\ufeff"))))


def test_admin_can_export_resources_with_credentials_by_default_and_audit(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    create_response = client.post(
        "/api/v1/resources",
        json=physical_resource_payload(
            resource_code="SNEXPORT000001",
            primary_ip="10.0.0.91",
            ssh_password="ssh-secret",
            bmc_password="bmc-secret",
            cpu_model="Kunpeng-920",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/resources/exports?resource_type=PHYSICAL&cpu_model=Kunpeng",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    rows = parse_export_csv(response.text)
    assert len(rows) == 1
    assert rows[0]["resource_code"] == "SNEXPORT000001"
    assert rows[0]["primary_ip"] == "10.0.0.91"
    assert rows[0]["ssh_username"] == "root"
    assert rows[0]["ssh_password"] == "ssh-secret"
    assert rows[0]["bmc_password"] == "bmc-secret"
    fieldnames = list(rows[0])
    assert fieldnames.index("ssh_password") == fieldnames.index("ssh_username") + 1
    assert fieldnames.index("bmc_password") == fieldnames.index("bmc_username") + 1
    logs = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "resource.export"))
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].detail["row_count"] == 1
    assert "ssh-secret" not in str(logs[0].detail)
    assert "bmc-secret" not in str(logs[0].detail)


def test_non_admin_cannot_export_resources(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)

    response = client.get(
        "/api/v1/resources/exports",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_preview_and_import_resources_from_csv(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    payload = {
        "filename": "resources.csv",
        "content": import_csv_content(),
        "dry_run": True,
    }

    preview = client.post(
        "/api/v1/resources/imports",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert preview.status_code == 200
    assert preview.json()["success_count"] == 1
    assert preview.json()["rows"][0]["status"] == "validated"
    assert db_session.execute(select(Resource)).scalars().all() == []

    missing_key = client.post(
        "/api/v1/resources/imports",
        json={**payload, "dry_run": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert missing_key.status_code == 400

    imported = client.post(
        "/api/v1/resources/imports",
        json={**payload, "dry_run": False},
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "resource-import-1",
        },
    )

    assert imported.status_code == 200
    body = imported.json()
    assert body["success_count"] == 1
    assert body["error_count"] == 0
    assert body["rows"][0]["status"] == "created"
    assert "ssh-pass" not in str(body)
    assert "bmc-pass" not in str(body)

    resource = db_session.execute(select(Resource)).scalar_one()
    physical_spec = db_session.get(PhysicalResourceSpec, resource.id)
    assert resource.resource_code == "SNCSV000000001"
    assert resource.name is None
    assert resource.extra == {"legacy_note": "old-note"}
    assert resource.ssh_password_ciphertext != "ssh-pass"
    assert physical_spec is not None
    assert physical_spec.bmc_password_ciphertext != "bmc-pass"

    replay = client.post(
        "/api/v1/resources/imports",
        json={**payload, "dry_run": False},
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "resource-import-1",
        },
    )
    assert replay.status_code == 200
    assert replay.json() == body
    assert len(db_session.execute(select(Resource)).scalars().all()) == 1

    logs = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "resource.import"))
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].action == "resource.import"
    assert "ssh-pass" not in str(logs[0].detail)
    assert "bmc-pass" not in str(logs[0].detail)


def test_import_reports_existing_resource_code(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    create_resource(client, token, physical_resource_payload(resource_code="SNCSV000000001"))

    response = client.post(
        "/api/v1/resources/imports",
        json={
            "filename": "resources.csv",
            "content": import_csv_content(),
            "dry_run": False,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "resource-import-duplicate",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success_count"] == 0
    assert body["error_count"] == 1
    assert body["rows"][0]["status"] == "error"
    assert body["rows"][0]["errors"] == ["resource_code already exists"]


def test_non_admin_cannot_import_resources(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="tse", role=UserRole.TSE)

    response = client.post(
        "/api/v1/resources/imports",
        json={
            "filename": "resources.csv",
            "content": import_csv_content(),
            "dry_run": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_install_physical_resource_schedules_task(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_resource(client, token, physical_resource_payload())

    image = client.post(
        "/api/v1/resources/install-images",
        json={
            "os_version": "openEuler-24.03-LTS",
            "arch": "aarch64",
            "efi_url": "http://h/efi/grubaa64.efi",
            "repo_url": "http://h/repo/aarch64",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert image.status_code == 200
    image_id = image.json()["id"]

    fake_task = SimpleNamespace(id="pxe-task-1")
    pxe_module = MagicMock()
    pxe_module.delay.return_value = fake_task
    monkeypatch.setattr("app.modules.vms.pxe_install.run_pxe_install_task", pxe_module)

    response = client.post(
        f"/api/v1/resources/{resource['id']}/install",
        json={"image_id": image_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "scheduled", "task_id": "pxe-task-1"}
    delay_args = pxe_module.delay.call_args.args
    assert delay_args[:2] == (resource["id"], image_id)
    assert len(delay_args) == 3
    assert delay_args[1] == image_id


def test_install_physical_resource_rejects_machine_under_test(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = login_as(client, db_session, username="admininstallbusy", role=UserRole.ADMIN)
    resource = create_resource(client, token, physical_resource_payload())
    user = db_session.scalar(select(User).where(User.username == "admininstallbusy"))
    assert user is not None
    mark_resource_testing(
        db_session,
        resource_id=str(resource["id"]),
        user_id=user.id,
    )
    image = client.post(
        "/api/v1/resources/install-images",
        json={
            "os_version": "openEuler-24.03-LTS",
            "arch": "aarch64",
            "efi_url": "http://h/efi/grubaa64.efi",
            "repo_url": "http://h/repo/aarch64",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    task = MagicMock()
    task.delay.return_value = SimpleNamespace(id="must-not-schedule")
    monkeypatch.setattr("app.modules.vms.pxe_install.run_pxe_install_task", task)

    response = client.post(
        f"/api/v1/resources/{resource['id']}/install",
        json={"image_id": image.json()["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    task.delay.assert_not_called()


def test_admin_can_probe_and_refresh_hardware(
    monkeypatch, client: TestClient, db_session: Session
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_resource(client, token, physical_resource_payload())
    rid = resource["id"]

    monkeypatch.setattr(
        "app.modules.resources.hardware_probe.probe_physical_hardware",
        lambda **kw: {
            "arch": "aarch64",
            "cpu_count": 96,
            "board_sn": "SN1",
            "os_version": "openEuler 24.03",
        },
    )
    response = client.post(
        f"/api/v1/resources/{rid}/probe",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "cpu_count" in body["fields_updated"]
    assert "arch" in body["fields_updated"]
    stored = db_session.get(Resource, rid)
    assert stored.arch == "aarch64"
    assert stored.physical_spec is not None
    assert stored.physical_spec.cpu_count == 96
    assert stored.physical_spec.board_sn == "SN1"

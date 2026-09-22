# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import subprocess
import sys
from collections.abc import Generator
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.credentials import decrypt_secret
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.idempotency.models import IdempotencyRecord
from app.modules.leases import service as lease_service
from app.modules.leases.models import LeaseEvent, ResourceLease
from app.modules.resources.models import OccupancyStatus, Resource, ResourceType
from app.modules.tasks.models import TaskEvent
from app.modules.users.models import UserRole
from app.modules.users.service import create_user
from app.modules.vms import host_runner
from app.modules.vms import service as vm_service
from app.modules.vms.service import (
    VMDestroyOptions,
    VMResourceCreateSpec,
    VMRollbackContext,
)
from app.modules.vms.execution_state import (
    get_vm_destroy_execution,
    mark_vm_destroy_started,
)
from app.modules.vms.host_contract import VMHostCreateResult, VMHostPowerResult
from app.modules.vms.image_discovery import VMImage
from app.modules.vms.iso_storage import ISOStorage, get_iso_storage
from app.modules.vms.models import VMInstallType, VMRequest, VMRequestStatus
from app.modules.vms.schemas import VMRequestCreate


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


@pytest.fixture()
def vm_image() -> VMImage:
    return VMImage(
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        url=(
            "http://172.168.131.94:9400/repo_list/mugen.mirror/iteration/"
            "openEuler/openEuler-24.03-LTS-SP4/round-9/aarch64/"
            "openEuler-24.03-LTS-SP4-aarch64.qcow2"
        ),
    )


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


def test_authenticated_user_can_upload_iso(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.vms.iso_storage.shutil.disk_usage",
        lambda _path: SimpleNamespace(
            total=100 * 1024**3,
            used=10 * 1024**3,
            free=90 * 1024**3,
        ),
    )

    def _iso_storage_override() -> ISOStorage:
        return ISOStorage(tmp_path)

    client.app.dependency_overrides[get_iso_storage] = _iso_storage_override
    token = login_as(client, db_session, username="isouser", role=UserRole.TE)

    response = client.post(
        "/api/v1/vm-isos",
        params={"filename": "openEuler.iso"},
        content=b"test-iso",
        headers={
            **auth_header(token),
            "Content-Type": "application/octet-stream",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["size_bytes"] == 8
    assert body["url"] == f"/vm-iso/{body['sha256']}.iso"
    assert (tmp_path / f"{body['sha256']}.iso").read_bytes() == b"test-iso"
    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "vm.iso.upload"))
    assert audit is not None
    assert audit.detail == {
        "filename": "openEuler.iso",
        "sha256": body["sha256"],
        "size_bytes": 8,
        "url": body["url"],
    }


def test_iso_upload_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vm-isos",
        params={"filename": "openEuler.iso"},
        content=b"test-iso",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 401


def vm_request_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "dist": "openEuler",
        "os_version": "openEuler-24.03-LTS-SP4",
        "image_round": "round-9",
        "arch": "aarch64",
        "vcpu_count": 2,
        "memory_mb": 4096,
        "data_disk_count": 1,
        "purpose": "调试 openEuler",
        "expected_ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    payload.update(overrides)
    return payload


def virtual_resource_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "resource_code": "3f31376e-f9b4-4a6d-9f9c-7a4f03edb45d",
        "resource_type": ResourceType.VIRTUAL.value,
        "name": "openEuler-24.03-LTS-SP4-round-9-aarch64-test",
        "primary_ip": "172.168.131.201",
        "arch": "aarch64",
        "os_version": "openEuler-24.03-LTS-SP4",
        "ssh_username": "root",
        "ssh_password": "openEuler12#$",
        "vm_name": "openEuler-24.03-LTS-SP4-round-9-aarch64-test",
        "vnc_port": 5901,
        "vnc_websocket_port": 5701,
        "vcpu_count": 2,
        "memory_mb": 4096,
        "disk_gb": 50,
    }
    payload.update(overrides)
    return payload


def physical_host_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "resource_code": "HOST000000000001",
        "resource_type": ResourceType.PHYSICAL.value,
        "name": "VM host",
        "primary_ip": "172.168.131.75",
        "arch": "aarch64",
        "ssh_username": "root",
        "ssh_password": "ssh-pass",
        "bmc_ip": "170.70.30.75",
        "bmc_username": "Administrator",
        "bmc_password": "bmc-pass",
        "tags": ["vm-host"],
    }
    payload.update(overrides)
    return payload


def create_vm_script() -> str:
    return (
        Path(__file__).parents[1] / "app" / "modules" / "vms" / "host_scripts" / "create-vm.sh"
    ).read_text(encoding="utf-8")


def inspect_vm_script_path() -> Path:
    return (
        Path(__file__).parents[1] / "app" / "modules" / "vms" / "host_scripts" / "inspect-vm.sh"
    )


def test_inspect_vm_script_syntax() -> None:
    subprocess.run(["/bin/bash", "-n", str(inspect_vm_script_path())], check=True)


def power_vm_script() -> str:
    return (
        Path(__file__).parents[1] / "app" / "modules" / "vms" / "host_scripts" / "power-vm.sh"
    ).read_text(encoding="utf-8")


def test_create_vm_script_does_not_emit_empty_data_disk_source() -> None:
    script = create_vm_script()

    assert "${DATA_DISK_PATHS[@]:-}" not in script


def test_create_vm_script_uses_virt_install_with_cpu_topology() -> None:
    script = create_vm_script()

    assert "virt_install_args=(" in script
    assert "vcpu_topology=" in script
    assert "sockets=1,cores=${vcpu_count},threads=1" in script
    assert 'if [[ "$arch" == "aarch64" ]]; then' in script
    assert 'virt_install_args+=(--controller "type=pci,model=pcie-root-port,index=50")' in script
    assert "--video virtio" in script
    assert "virtio-gpu" not in script
    assert '--graphics "vnc,listen=0.0.0.0"' in script
    assert '--graphics "vnc,listen=0.0.0.0,websocket=-1"' not in script
    assert "enable_vnc_websocket_xml" in script
    assert 'graphics.set("websocket", "-1")' in script
    assert 'set_lifecycle("on_reboot", "restart", "on_poweroff")' in script
    assert 'if install_type == "manual":' in script
    assert 'os_element.append(ET.Element("boot", {"dev": "hd"}))' in script
    assert 'os_element.append(ET.Element("boot", {"dev": "cdrom"}))' in script
    assert "print_xml_args=(--print-xml 1)" in script
    assert 'event_command virt-install "${virt_install_args[@]}" "${print_xml_args[@]}"' in script
    assert 'virt-install "${virt_install_args[@]}" "${print_xml_args[@]}"' in script
    assert (
        'enable_vnc_websocket_xml "$install_type" <"$VIRT_INSTALL_XML_PATH" '
        '>"$DOMAIN_XML_PATH" 2>"$VIRT_INSTALL_ERR_PATH"' in script
    )
    assert (
        'enable_vnc_websocket_xml <"$VIRT_INSTALL_XML_PATH" >"$DOMAIN_XML_PATH" 2>&1' not in script
    )
    assert "collect_failure_diagnostics" in script
    assert 'collect_command_diagnostic virsh dumpxml "$vm_name"' in script
    assert 'event_command virsh define "$DOMAIN_XML_PATH"' in script
    assert 'virsh define "$DOMAIN_XML_PATH"' in script
    assert '--cdrom "$cache_path"' in script
    assert '--boot "hd,cdrom"' in script
    assert '--boot "cdrom,hd"' not in script
    assert "manual_install_ready" in script
    assert "<domain type='kvm'>" not in script
    assert 'virsh define "$xml_path"' not in script


def test_create_vm_script_reads_dhcp_leases_from_stdin() -> None:
    script = create_vm_script()

    assert 'python3 - "$mac_address" "$leases"' not in script
    assert "python3 -c " in script
    assert '"$mac_address" <<<"$leases"' in script
    assert "text = sys.stdin.read()" in script


def test_create_vm_script_cleans_old_unreferenced_cache_files() -> None:
    script = create_vm_script()

    assert "CACHE_RETENTION_DAYS=30" in script
    assert "cleanup_old_cache_files" in script
    assert 'find "$CACHE_DIR"' in script
    assert '-mtime +"$CACHE_RETENTION_DAYS"' in script
    assert "cache_file_is_referenced" in script
    assert 'grep -Fq -- "$path"' in script


def test_create_vm_script_preflights_download_and_cleans_partial_cache() -> None:
    script = create_vm_script()

    assert "check_image_download_capacity" in script
    assert "image_content_length_bytes" in script
    assert 'curl --fail --silent --show-error --location --head "$image_url"' in script
    assert 'json_error capacity_insufficient "insufficient disk for image download"' in script
    assert 'rm -f "${cache_path}.part"' in script
    assert "trap 'cleanup_and_error interrupted \"create-vm interrupted\"' HUP INT TERM" in script


def test_power_vm_script_uses_virsh_power_commands() -> None:
    script = power_vm_script()

    assert "action must be state, start, shutdown or reboot" in script
    assert 'virsh domstate "$vm_name"' in script
    assert 'json_error vm_power_failed "$command_output"' in script
    assert "run_power_command start" in script
    assert "run_power_command shutdown" in script
    assert "run_power_command reboot" in script


def test_parse_latest_dhcp_lease_ip_uses_last_matching_lease() -> None:
    leases = """
lease 172.168.131.210 {
  hardware ethernet 52:54:00:12:34:56;
}
lease 172.168.131.211 {
  hardware ethernet 52:54:00:aa:bb:cc;
}
lease 172.168.131.212 {
  hardware ethernet 52:54:00:12:34:56;
}
"""

    assert vm_service.parse_latest_dhcp_lease_ip(leases, "52:54:00:12:34:56") == ("172.168.131.212")
    assert vm_service.parse_latest_dhcp_lease_ip(leases, "52:54:00:00:00:00") is None


def create_resource(
    client: TestClient,
    token: str,
    payload: dict[str, object],
) -> dict[str, object]:
    response = client.post(
        "/api/v1/resources",
        json=payload,
        headers=auth_header(token),
    )

    assert response.status_code == 201
    return response.json()


def create_virtual_resource(
    client: TestClient,
    token: str,
    **overrides: object,
) -> dict[str, object]:
    return create_resource(client, token, virtual_resource_payload(**overrides))


def test_vm_list_uses_natural_ip_order_and_fixed_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    for host_number in range(51, 0, -1):
        create_virtual_resource(
            client,
            admin_token,
            resource_code=f"vm-pagination-{host_number}",
            primary_ip=f"172.168.131.{host_number}",
        )

    first = client.get(
        "/api/v1/vms",
        params={"all": True, "page": 1},
        headers=auth_header(admin_token),
    )
    second = client.get(
        "/api/v1/vms",
        params={"all": True, "page": 2},
        headers=auth_header(admin_token),
    )

    assert first.status_code == 200
    assert first.json()["total"] == 51
    assert first.json()["page_size"] == 50
    assert [item["primary_ip"] for item in first.json()["items"][:2]] == [
        "172.168.131.1",
        "172.168.131.2",
    ]
    assert first.json()["items"][-1]["primary_ip"] == "172.168.131.50"
    assert [item["primary_ip"] for item in second.json()["items"]] == ["172.168.131.51"]


def test_vm_list_search_filters_by_any_field(
    client: TestClient,
    db_session: Session,
) -> None:
    """
    Search matches name, primary_ip, os_version, arch, resource_code,
    management_status — case-insensitive, across pages.
    """

    create_virtual_resource(
        client,
        admin_token,
        resource_code="vm-search-alpha",
        primary_ip="172.168.131.100",
        name="web-server-01",
        os_version="openEuler-22.03-LTS-SP4",
        arch="x86_64",
    )
    create_virtual_resource(
        client,
        admin_token,
        resource_code="vm-search-beta",
        primary_ip="172.168.131.200",
        name="db-server-02",
        os_version="openEuler-24.03-LTS-SP3",
        arch="aarch64",
    )

    # Search by name fragment
    r = client.get(
        "/api/v1/vms",
        params={"all": True, "search": "web-server"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "web-server-01"

    # Search by IP fragment
    r = client.get(
        "/api/v1/vms", params={"all": True, "search": "131.200"}, headers=auth_header(admin_token)
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["primary_ip"] == "172.168.131.200"

    # Search by os_version fragment (case-insensitive)
    r = client.get(
        "/api/v1/vms", params={"all": True, "search": "24.03"}, headers=auth_header(admin_token)
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["os_version"] == "openEuler-24.03-LTS-SP3"

    # Search by arch
    r = client.get(
        "/api/v1/vms", params={"all": True, "search": "aarch64"}, headers=auth_header(admin_token)
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["arch"] == "aarch64"

    # Search by resource_code
    r = client.get(
        "/api/v1/vms",
        params={"all": True, "search": "vm-search-beta"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["resource_code"] == "vm-search-beta"

    # Empty search returns all
    r = client.get(
        "/api/v1/vms", params={"all": True, "search": ""}, headers=auth_header(admin_token)
    )
    assert r.status_code == 200
    assert r.json()["total"] >= 2

    # No match
    r = client.get(
        "/api/v1/vms",
        params={"all": True, "search": "nonexistent-xyz"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_admin_can_update_virtual_resource_ssh_password(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_virtual_resource(client, admin_token)

    response = client.patch(
        f"/api/v1/resources/{resource['id']}",
        json={"ssh_password": "new-vm-pass"},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["has_ssh_password"] is True
    assert "ssh_password" not in body

    stored_resource = db_session.get(Resource, resource["id"])
    assert stored_resource is not None
    assert stored_resource.ssh_password_ciphertext != "new-vm-pass"
    assert decrypt_secret(stored_resource.ssh_password_ciphertext) == "new-vm-pass"

    logs = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "resource.update"))
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].target_id == resource["id"]
    assert logs[0].detail == {
        "fields": ["ssh_password"],
        "resource_code": resource["resource_code"],
    }


def occupy_resource(
    client: TestClient,
    token: str,
    resource_id: str,
    *,
    key: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/resources/{resource_id}/leases",
        json={
            "purpose": "调试 VM",
            "expected_ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
        headers=auth_header(token, key=key),
    )

    assert response.status_code == 201
    return response.json()


def stub_vm_queue(monkeypatch: pytest.MonkeyPatch, vm_image: VMImage) -> list[str]:
    queued_request_ids: list[str] = []

    monkeypatch.setattr(vm_service, "find_image", lambda **_: vm_image)
    monkeypatch.setattr(
        vm_service,
        "enqueue_vm_create",
        lambda request: queued_request_ids.append(request.id) or "task-1",
    )
    return queued_request_ids


def test_te_can_submit_vm_request(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    vm_image: VMImage,
) -> None:
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    queued_request_ids = stub_vm_queue(monkeypatch, vm_image)

    response = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(),
        headers=auth_header(te_token, key="vm-request-1"),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["install_type"] == "auto"
    assert body["data_disk_count"] == 1
    assert body["data_disk_size_gb"] == 50
    assert queued_request_ids == [body["id"]]

    stored = db_session.scalar(select(VMRequest).where(VMRequest.id == body["id"]))
    assert stored is not None
    assert stored.task_id == "task-1"
    assert stored.image_url == vm_image.url

    events = list(
        db_session.execute(
            select(TaskEvent).where(TaskEvent.subject_type == "vm_request")
        ).scalars()
    )
    assert [(event.phase, event.celery_task_id, event.subject_id) for event in events] == [
        ("queued", "task-1", body["id"])
    ]

    event_response = client.get(
        f"/api/v1/vm-requests/{body['id']}/events",
        headers=auth_header(te_token),
    )
    assert event_response.status_code == 200
    assert [event["phase"] for event in event_response.json()] == ["queued"]


def test_vm_request_with_64k_suffix_strips_for_image_lookup_but_preserves_on_request(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    vm_image: VMImage,
) -> None:
    """os_version=...-64k → find_image 用 base 版查镜像，request 保留 -64k 触发后处理。"""
    find_calls: list[dict] = []

    def fake_find_image(**kwargs):  # noqa: ANN001
        find_calls.append(kwargs)
        return vm_image

    monkeypatch.setattr(vm_service, "find_image", fake_find_image)
    monkeypatch.setattr(vm_service, "enqueue_vm_create", lambda request: "task-64k")

    te_token = login_as(client, db_session, username="te64kimg", role=UserRole.TE)
    response = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(os_version="openEuler-24.03-LTS-SP4-64k"),
        headers=auth_header(te_token, key="vm-req-64k"),
    )

    assert response.status_code == 202
    assert find_calls, "find_image should be called for auto install"
    assert find_calls[0]["os_version"] == "openEuler-24.03-LTS-SP4", find_calls[0]
    stored = db_session.scalar(select(VMRequest).where(VMRequest.id == response.json()["id"]))
    assert stored is not None
    assert stored.os_version == "openEuler-24.03-LTS-SP4-64k"


def test_vm_request_rejects_unsupported_64k_version(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    vm_image: VMImage,
) -> None:
    queued = stub_vm_queue(monkeypatch, vm_image)
    token = login_as(client, db_session, username="te64kbad", role=UserRole.TE)

    response = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(os_version="openEuler-24.03-LTS-SP3-64k"),
        headers=auth_header(token, key="vm-req-unsupported-64k"),
    )

    assert response.status_code == 422
    assert "当前仅支持" in response.json()["error"]["message"]
    assert queued == []


def test_vm_batch_rejects_64k_for_unsupported_architecture(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    vm_image: VMImage,
) -> None:
    queued = stub_vm_queue(monkeypatch, vm_image)
    token = login_as(client, db_session, username="te64kbatch", role=UserRole.TE)

    payload = vm_request_payload(os_version="openEuler-24.03-LTS-SP4-64k")
    payload.pop("arch")
    payload["specs"] = [{"arch": "x86_64", "count": 1}]
    response = client.post(
        "/api/v1/vm-requests/batch",
        json=payload,
        headers=auth_header(token, key="vm-batch-unsupported-64k"),
    )

    assert response.status_code == 422
    assert "aarch64" in response.json()["error"]["message"]
    assert queued == []


def test_vm_request_refresh_marks_stale_creating_request_failed(
    client: TestClient,
    db_session: Session,
) -> None:
    requester = create_user(
        db_session,
        username="te1",
        password="test-pass",
        role=UserRole.TE,
        display_name="te1",
    )
    user_login = client.post(
        "/api/v1/auth/login",
        json={"username": "te1", "password": "test-pass"},
    )
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]
    old_time = datetime.now(UTC) - timedelta(minutes=90)
    stale_request = VMRequest(
        requester_user_id=requester.id,
        status=VMRequestStatus.CREATING.value,
        purpose="调试 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        image_url="http://example.test/openEuler.qcow2",
        vcpu_count=2,
        memory_mb=4096,
        disk_gb=0,
        data_disk_count=0,
        data_disk_size_gb=50,
        task_id="stale-vm-task",
        host_attempts=[],
    )
    db_session.add(stale_request)
    db_session.flush()
    db_session.add(
        TaskEvent(
            task_type="vm_create",
            subject_type="vm_request",
            subject_id=stale_request.id,
            celery_task_id=stale_request.task_id,
            phase="started",
            message="worker 已领取 VM 创建任务",
            created_at=old_time,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/vm-requests",
        headers=auth_header(user_token),
    )
    user_events_response = client.get(
        f"/api/v1/vm-requests/{stale_request.id}/events",
        headers=auth_header(user_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == stale_request.id
    assert body["items"][0]["status"] == "failed"
    assert body["items"][0]["error_code"] == "stale_creating"
    assert user_events_response.status_code == 200

    events = list(
        db_session.execute(
            select(TaskEvent)
            .where(TaskEvent.subject_id == stale_request.id)
            .order_by(TaskEvent.created_at)
        ).scalars()
    )
    assert [event.phase for event in events] == ["started", "failed"]
    assert events[-1].error_code == "stale_creating"


def test_expired_vm_lease_is_not_logged_released_before_destroy(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_virtual_resource(client, admin_token)
    lease_data = occupy_resource(client, te_token, str(resource["id"]), key="occupy-vm")
    lease = db_session.get(ResourceLease, lease_data["id"])
    assert lease is not None
    lease.expected_ends_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    queued: list[dict[str, object]] = []
    monkeypatch.setattr(
        vm_service,
        "enqueue_vm_destroy",
        lambda **kwargs: queued.append(kwargs) or "destroy-task-1",
    )

    assert lease_service.release_expired_leases(db_session) == 1
    db_session.commit()

    db_session.refresh(lease)
    stored_resource = db_session.get(Resource, resource["id"])
    assert lease.released_at is None
    assert stored_resource is not None
    assert stored_resource.occupancy_status == OccupancyStatus.EXPIRED.value
    assert queued[0]["lease_id"] == lease.id
    assert (
        db_session.scalars(select(LeaseEvent).where(LeaseEvent.event_type == "auto_release")).all()
        == []
    )


def test_manual_iso_vm_request_uses_url_without_image_discovery(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    queued_request_ids: list[str] = []

    def fail_find_image(**_kwargs: object) -> VMImage:
        pytest.fail("manual ISO requests must not call image discovery")

    monkeypatch.setattr(vm_service, "find_image", fail_find_image)
    monkeypatch.setattr(
        vm_service,
        "enqueue_vm_create",
        lambda request: queued_request_ids.append(request.id) or "task-1",
    )

    response = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(
            install_type="manual",
            image_url="http://repo.example.test/openEuler.iso",
            image_round="",
        ),
        headers=auth_header(te_token, key="manual-iso-request"),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["install_type"] == "manual"
    assert body["image_url"] == "http://repo.example.test/openEuler.iso"
    assert body["image_round"] == ""
    assert queued_request_ids == [body["id"]]

    stored = db_session.scalar(select(VMRequest).where(VMRequest.id == body["id"]))
    assert stored is not None
    assert stored.install_type == VMInstallType.MANUAL.value
    assert stored.image_url == "http://repo.example.test/openEuler.iso"


def test_manual_iso_vm_request_rejects_non_http_url(
    client: TestClient,
    db_session: Session,
) -> None:
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)

    response = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(
            install_type="manual",
            image_url="file:///tmp/openEuler.iso",
            image_round="",
        ),
        headers=auth_header(te_token, key="manual-iso-bad-url"),
    )

    assert response.status_code == 422


def test_submit_vm_request_persists_queue_task_id(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    vm_image: VMImage,
) -> None:
    actor = create_user(
        db_session,
        username="te1",
        password="test-pass",
        role=UserRole.TE,
        display_name="te1",
    )
    db_session.commit()

    monkeypatch.setattr(vm_service, "find_image", lambda **_: vm_image)
    monkeypatch.setattr(vm_service, "enqueue_vm_create", lambda _request: "task-committed")

    request = vm_service.submit_vm_request(
        db_session,
        actor=actor,
        payload=VMRequestCreate.model_validate(vm_request_payload()),
    )

    db_session.expire_all()
    stored = db_session.get(VMRequest, request.id)
    assert stored is not None
    assert stored.task_id == "task-committed"


def test_manual_iso_cache_filename_uses_iso_extension_and_url_hash() -> None:
    request = VMRequest(
        requester_user_id="user-1",
        install_type=VMInstallType.MANUAL.value,
        purpose="安装 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="",
        arch="aarch64",
        image_url="http://repo.example.test/openEuler.iso",
        vcpu_count=2,
        memory_mb=4096,
        data_disk_count=0,
        data_disk_size_gb=50,
    )

    assert vm_service.cache_filename(request) == (
        f"manual-iso-{vm_service.short_url_hash(request.image_url)}.iso"
    )
    vm_name = vm_service.make_vm_name(request, "vm-uuid")
    assert "--" not in vm_name
    assert "-aarch64-" in vm_name
    assert vm_name.endswith("-vm-uuid")


def test_vm_name_timestamp_uses_configured_timezone(monkeypatch) -> None:
    monkeypatch.setattr(
        vm_service,
        "now_utc",
        lambda: datetime(2026, 7, 13, 7, 49, 30, tzinfo=UTC),
    )

    assert vm_service.vm_name_timestamp() == "20260713T154930"


# ---------- host_create_lock: per-host VM creation serialization ----------


def test_host_create_lock_immediate_acquire(monkeypatch, tmp_path) -> None:
    """First caller acquires the lock without waiting."""
    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    with hl.host_create_lock("10.0.0.1") as waited:
        assert waited is False


def test_host_create_lock_second_caller_waits(tmp_path, monkeypatch) -> None:
    """With max_slots=1, second concurrent caller must wait."""

    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    monkeypatch.setattr(
        "app.core.config.get_settings",
        lambda: type("S", (), {"vm_max_concurrent_per_host": 1})(),
    )
    results: list[bool] = []
    lock_acquired = threading.Event()
    second_can_start = threading.Event()

    def first() -> None:
        with hl.host_create_lock("10.0.0.2") as waited:
            results.append(waited)
            lock_acquired.set()
            second_can_start.wait(timeout=5)

    def second() -> None:
        lock_acquired.wait(timeout=5)
        with hl.host_create_lock("10.0.0.2") as waited:
            results.append(waited)

    t1 = threading.Thread(target=first)
    t2 = threading.Thread(target=second)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    second_can_start.set()
    t2.join(timeout=10)

    assert len(results) == 2
    assert results.count(False) == 1
    assert results.count(True) == 1


def test_host_create_lock_multi_slot_parallel(tmp_path, monkeypatch) -> None:
    """With max_slots=4, 4 concurrent callers all acquire immediately."""

    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    monkeypatch.setattr(
        "app.core.config.get_settings",
        lambda: type("S", (), {"vm_max_concurrent_per_host": 4})(),
    )
    results: list[bool] = []
    barrier = threading.Barrier(4)

    def worker() -> None:
        barrier.wait()
        with hl.host_create_lock("10.0.0.3") as waited:
            results.append(waited)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(results) == 4
    assert all(r is False for r in results), results


def test_host_create_lock_different_hosts_parallel(monkeypatch, tmp_path) -> None:
    """Locks for different hosts don't block each other."""

    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    results: list[bool] = []
    barrier = threading.Barrier(2)

    def worker(host: str) -> None:
        barrier.wait()
        with hl.host_create_lock(host) as waited:
            results.append(waited)

    t1 = threading.Thread(target=worker, args=("10.0.0.3",))
    t2 = threading.Thread(target=worker, args=("10.0.0.4",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert len(results) == 2
    # Both acquired immediately — no cross-host blocking.
    assert results == [False, False]


def test_try_host_lock_immediate_acquire(monkeypatch, tmp_path) -> None:
    """Non-blocking try succeeds when no one holds the lock."""
    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    fh = hl.try_host_lock("10.0.0.10")
    assert fh is not None
    hl.release_host_lock(fh)


def test_try_host_lock_returns_none_when_all_slots_busy(tmp_path, monkeypatch) -> None:
    """With max_slots=1, non-blocking try returns None when slot is held."""

    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    monkeypatch.setattr(
        "app.core.config.get_settings",
        lambda: type("S", (), {"vm_max_concurrent_per_host": 1})(),
    )
    acquired = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with hl.host_create_lock("10.0.0.11") as _:
            acquired.set()
            release.wait(timeout=5)

    t = threading.Thread(target=holder)
    t.start()
    acquired.wait(timeout=5)

    fh = hl.try_host_lock("10.0.0.11")
    assert fh is None

    release.set()
    t.join(timeout=5)


def test_try_host_lock_different_hosts_parallel(monkeypatch, tmp_path) -> None:
    """Non-blocking try on different host succeeds even if another host is locked."""
    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    with hl.host_create_lock("10.0.0.12") as _:
        fh = hl.try_host_lock("10.0.0.13")
        assert fh is not None  # different host, no contention
        hl.release_host_lock(fh)


def test_host_create_lock_released_after_context(monkeypatch, tmp_path) -> None:
    """Lock is released when context exits, allowing next caller."""
    import app.modules.vms.host_lock as hl

    monkeypatch.setattr(hl, "_LOCK_DIR", tmp_path)
    with hl.host_create_lock("10.0.0.5") as _:
        pass
    # Lock should be released, next acquire should be immediate.
    with hl.host_create_lock("10.0.0.5") as waited:
        assert waited is False


def test_manual_iso_resource_uses_default_ssh_credentials(db_session: Session) -> None:
    request = VMRequest(
        requester_user_id="user-1",
        install_type=VMInstallType.MANUAL.value,
        purpose="安装 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="",
        arch="aarch64",
        image_url="http://repo.example.test/openEuler.iso",
        vcpu_count=2,
        memory_mb=4096,
        data_disk_count=0,
        data_disk_size_gb=50,
    )
    host = Resource(
        id="host-1",
        resource_code="HOST000000000001",
        resource_type=ResourceType.PHYSICAL.value,
        primary_ip="172.168.131.75",
        ssh_username="root",
        ssh_password_ciphertext="encrypted",
    )
    result = VMHostCreateResult(
        status="success",
        vm_uuid="3f31376e-f9b4-4a6d-9f9c-7a4f03edb45d",
        vm_name="openEuler-24.03-LTS-SP4-aarch64-test",
        primary_ip=None,
        mac_address="52:54:00:12:34:56",
        vnc_port=5901,
        vnc_websocket_port=5701,
        disk_gb=50,
        system_disk_path="/var/lib/libvirt/images/kronos/instances/vm.qcow2",
        data_disk_paths=[],
    )

    resource = vm_service.create_resource_from_vm_result(
        db_session,
        draft=VMResourceCreateSpec(
            request=request,
            host=host,
            vm_uuid=result.vm_uuid,
            vm_name=result.vm_name,
            result=result,
        ),
    )

    assert resource.primary_ip is None
    assert resource.ssh_username == "root"
    assert decrypt_secret(resource.ssh_password_ciphertext) == "openEuler12#$"
    assert resource.virtual_spec is not None
    assert resource.virtual_spec.disk_gb == 50
    assert resource.virtual_spec.vnc_websocket_port == 5701


def test_create_payload_does_not_send_vm_ssh_credentials_to_host() -> None:
    request = VMRequest(
        requester_user_id="user-1",
        purpose="调试 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        image_url="http://repo/openEuler.qcow2",
        vcpu_count=2,
        memory_mb=4096,
        data_disk_count=0,
        data_disk_size_gb=50,
    )
    host = Resource(
        id="host-1",
        resource_code="HOST000000000001",
        resource_type=ResourceType.PHYSICAL.value,
        primary_ip="172.168.131.75",
        ssh_username="root",
        ssh_password_ciphertext="encrypted",
    )

    payload = vm_service.build_create_payload(
        request,
        host,
        vm_uuid="3f31376e-f9b4-4a6d-9f9c-7a4f03edb45d",
        vm_name="openEuler-24.03-LTS-SP4-round-9-aarch64-test",
    )

    assert "ssh_username" not in payload.model_dump()
    assert "ssh_password" not in payload.model_dump()
    assert "disk_gb" not in payload.model_dump()
    assert payload.arch == "aarch64"


def test_process_vm_request_commits_host_stage_events_immediately(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = create_user(
        db_session,
        username="te1",
        password="test-pass",
        role=UserRole.TE,
        display_name="te1",
    )
    host = Resource(
        resource_code="HOST000000000001",
        resource_type=ResourceType.PHYSICAL.value,
        name="VM host",
        primary_ip="172.168.131.75",
        arch="aarch64",
        management_status="active",
        ssh_username="root",
        ssh_password_ciphertext="encrypted",
        tags=["vm-host"],
    )
    request = VMRequest(
        requester_user_id=actor.id,
        status=VMRequestStatus.PENDING.value,
        purpose="调试 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        image_url="http://repo/openEuler.qcow2",
        vcpu_count=2,
        memory_mb=4096,
        disk_gb=0,
        data_disk_count=0,
        data_disk_size_gb=50,
        task_id="task-1",
        host_attempts=[],
    )
    db_session.add_all([actor, host, request])
    db_session.commit()
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))

    commit_count = 0
    original_commit = db_session.commit

    def counting_commit() -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(db_session, "commit", counting_commit)

    def fake_run_host_script(**kwargs: object) -> object:
        if kwargs.get("script_name") == "inspect-vm.sh":
            return _fake_inspect_success()
        event_sink = kwargs["options"].event_sink
        before_event_commit_count = commit_count
        event_sink("check_capacity", "检查宿主机实时容量")
        assert commit_count == before_event_commit_count + 1
        return VMHostCreateResult(
            status="success",
            vm_uuid="3f31376e-f9b4-4a6d-9f9c-7a4f03edb45d",
            vm_name="openEuler-24.03-LTS-SP4-round-9-aarch64-test",
            primary_ip="172.168.131.201",
            mac_address="52:54:00:12:34:56",
            vnc_port=5901,
            vnc_websocket_port=5701,
            disk_gb=50,
            system_disk_path="/var/lib/libvirt/images/kronos/instances/vm.qcow2",
            data_disk_paths=[],
        )

    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)

    vm_service.process_vm_request(request.id)

    events = list(
        db_session.execute(
            select(TaskEvent)
            .where(TaskEvent.subject_id == request.id)
            .order_by(TaskEvent.created_at)
        ).scalars()
    )
    assert [event.phase for event in events] == [
        "started",
        "host_selected",
        "host_connecting",
        "check_capacity",
        "succeeded",
    ]


def _setup_64k_vm_request(db_session: Session, os_version: str) -> tuple:
    """Shared setup：actor + vm-host + -64k VMRequest，提交后返回 (actor, host, request)。"""
    actor = create_user(
        db_session,
        username="te64k",
        password="test-pass",
        role=UserRole.TE,
        display_name="te64k",
    )
    host = Resource(
        resource_code="HOST000000000064",
        resource_type=ResourceType.PHYSICAL.value,
        name="VM host 64k",
        primary_ip="172.168.131.64",
        arch="aarch64",
        management_status="active",
        ssh_username="root",
        ssh_password_ciphertext="encrypted",
        tags=["vm-host"],
    )
    request = VMRequest(
        requester_user_id=actor.id,
        status=VMRequestStatus.PENDING.value,
        purpose="64k 内核测试",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version=os_version,
        image_round="round-9",
        arch="aarch64",
        image_url="http://repo/openEuler.qcow2",
        vcpu_count=2,
        memory_mb=4096,
        disk_gb=0,
        data_disk_count=0,
        data_disk_size_gb=50,
        task_id="task-64k",
        host_attempts=[],
    )
    db_session.add_all([actor, host, request])
    db_session.commit()
    return actor, host, request


def _fake_inspect_success() -> dict[str, object]:
    return {
        "status": "success",
        "domain_exists": True,
        "power_state": "running",
        "system_disk_exists": True,
        "data_disks_existing": [],
    }


def _fake_create_vm_host_script(**kwargs: object) -> object:
    if kwargs.get("script_name") == "inspect-vm.sh":
        return _fake_inspect_success()
    return VMHostCreateResult(
        status="success",
        vm_uuid="64k-vm-uuid",
        vm_name="openEuler-64k-test",
        primary_ip="172.168.131.201",
        mac_address="52:54:00:64:6b:01",
        vnc_port=5901,
        vnc_websocket_port=5701,
        disk_gb=50,
        system_disk_path="/var/lib/libvirt/images/kronos/instances/vm-64k.qcow2",
        data_disk_paths=[],
    )


def test_process_vm_request_fails_attempt_when_create_not_confirmed(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """create-vm.sh 回传成功但回读宿主未发现 domain → 本宿主 attempt 失败，不登记不建租约。"""
    actor, host, request = _setup_64k_vm_request(db_session, "openEuler-24.03-LTS-SP4-64k")
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    destroy_calls: list[str] = []

    def fake_run_host_script(**kwargs: object) -> object:
        if kwargs.get("script_name") == "inspect-vm.sh":
            return {
                "status": "success",
                "domain_exists": False,
                "power_state": None,
                "system_disk_exists": False,
                "data_disks_existing": [],
            }
        if kwargs.get("script_name") == "destroy-vm.sh":
            destroy_calls.append("destroy")
            return {"status": "success"}
        return _fake_create_vm_host_script(**kwargs)

    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)

    vm_service.process_vm_request(request.id)

    db_session.refresh(request)
    assert request.status != VMRequestStatus.SUCCEEDED.value
    assert request.resource_id is None
    assert request.host_attempts
    last_attempt = request.host_attempts[-1]
    assert last_attempt["host_resource_id"] == host.id
    assert last_attempt["status"] == "failed"
    assert last_attempt["error_code"] == "vm_not_confirmed_after_create"
    # 回读确认不存在时无需回滚清理(宿主上没有该 VM)
    assert destroy_calls == []
    assert (
        db_session.execute(select(func.count()).select_from(ResourceLease)).scalar_one() == 0
    )


def test_process_vm_request_calls_apply_kernel_64k_for_64k_os_version(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """os_version 含 -64k → create_lease 后、SUCCEEDED 前调 apply_kernel_64k。"""
    actor, host, request = _setup_64k_vm_request(db_session, "openEuler-24.03-LTS-SP4-64k")
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", _fake_create_vm_host_script)

    apply_calls: list[dict] = []

    def fake_apply(db, *, request, resource, actor, allow_round_fallback=True):  # noqa: ANN001
        apply_calls.append(
            {
                "request_id": request.id,
                "resource_id": resource.id,
                "host_ip": (resource.primary_ip or ""),
            }
        )

    monkeypatch.setattr(vm_service, "apply_kernel_64k", fake_apply)

    vm_service.process_vm_request(request.id)

    assert len(apply_calls) == 1
    assert apply_calls[0]["request_id"] == request.id
    assert apply_calls[0]["host_ip"] == "172.168.131.201"
    db_session.refresh(request)
    assert request.status == VMRequestStatus.SUCCEEDED.value
    events = db_session.execute(
        select(TaskEvent)
        .where(TaskEvent.subject_id == request.id)
        .order_by(TaskEvent.created_at)
    ).scalars()
    phases = [e.phase for e in events]
    assert phases[-1] == "succeeded"


def test_process_vm_request_rolls_back_vm_when_kernel_64k_not_found(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_kernel_64k raise Kernel64kNotFoundError → 调 _rollback_just_created_vm + 不标成功。"""
    from app.modules.vms.service import Kernel64kNotFoundError

    actor, host, request = _setup_64k_vm_request(db_session, "openEuler-24.03-LTS-SP4-64k")
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", _fake_create_vm_host_script)

    def raise_apply(db, *, request, resource, actor, allow_round_fallback=True):  # noqa: ANN001
        raise Kernel64kNotFoundError("no kernel-64k")

    monkeypatch.setattr(vm_service, "apply_kernel_64k", raise_apply)

    rollback_calls: list[dict] = []

    def fake_rollback(db, *, draft):  # noqa: ANN001
        rollback_calls.append(
            {
                "request_id": draft.request.id,
                "resource_id": draft.resource.id,
                "host_id": draft.host.id,
            }
        )

    monkeypatch.setattr(vm_service, "_rollback_just_created_vm", fake_rollback)

    vm_service.process_vm_request(request.id)

    assert len(rollback_calls) == 1
    assert rollback_calls[0]["host_id"] == host.id
    db_session.refresh(request)
    assert request.status != VMRequestStatus.SUCCEEDED.value
    events = db_session.execute(
        select(TaskEvent)
        .where(TaskEvent.subject_id == request.id)
        .order_by(TaskEvent.created_at)
    ).scalars()
    phases = [e.phase for e in events]
    assert "succeeded" not in phases


def test_process_vm_request_rolls_back_vm_on_unexpected_64k_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """64k 远程准备抛出非领域异常时也必须回滚已创建的 VM。"""
    _actor, host, request = _setup_64k_vm_request(
        db_session,
        "openEuler-24.03-LTS-SP4-64k",
    )
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", _fake_create_vm_host_script)
    monkeypatch.setattr(
        vm_service,
        "apply_kernel_64k",
        MagicMock(side_effect=RuntimeError("ssh dependency missing")),
    )
    rollback = MagicMock()
    monkeypatch.setattr(vm_service, "_rollback_just_created_vm", rollback)

    vm_service.process_vm_request(request.id)

    rollback.assert_called_once()
    assert rollback.call_args.kwargs["draft"].host.id == host.id
    error = rollback.call_args.kwargs["draft"].error
    assert isinstance(error, RuntimeError)


def test_process_vm_request_returns_not_transferred_without_rollback(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """流水线最新轮无 64k 时保留基础 VM，并结构化返回未转测。"""
    from app.modules.vms.service import Kernel64kNotTransferredError

    _actor, _host, request = _setup_64k_vm_request(db_session, "openEuler-24.03-LTS-SP4-64k")
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", _fake_create_vm_host_script)

    def raise_not_transferred(*args, **kwargs):  # noqa: ANN002, ANN003
        raise Kernel64kNotTransferredError("latest round has no kernel-64k")

    monkeypatch.setattr(vm_service, "apply_kernel_64k", raise_not_transferred)
    rollback = MagicMock()
    monkeypatch.setattr(vm_service, "_rollback_just_created_vm", rollback)

    result = vm_service.process_vm_request(
        request.id,
        allow_kernel_64k_round_fallback=False,
    )

    assert result is False
    assert request.status == VMRequestStatus.SUCCEEDED.value
    assert request.resource_id is not None
    rollback.assert_not_called()
    events = db_session.execute(
        select(TaskEvent)
        .where(TaskEvent.subject_id == request.id)
        .order_by(TaskEvent.created_at)
    ).scalars()
    phases = [e.phase for e in events]
    assert phases[-1] == "succeeded"


def test_process_vm_request_calls_apply_custom_kernel_when_variant_set(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """request.kernel_variant 非空 → 调 apply_custom_kernel，不调 apply_kernel_64k。"""
    actor, host, request = _setup_64k_vm_request(
        db_session, "openEuler-26.09-DevStation"
    )
    request.kernel_variant = "26.09-with-kernel-6.18"
    db_session.commit()
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", _fake_create_vm_host_script)

    custom_calls: list[str] = []

    def fake_custom(db, *, request, resource, actor):  # noqa: ANN001
        custom_calls.append(request.id)

    monkeypatch.setattr(vm_service, "apply_custom_kernel", fake_custom)

    kernel64k_calls: list[str] = []

    def fake_64k(db, *, request, resource, actor):  # noqa: ANN001
        kernel64k_calls.append(request.id)

    monkeypatch.setattr(vm_service, "apply_kernel_64k", fake_64k)

    vm_service.process_vm_request(request.id)

    assert len(custom_calls) == 1
    assert kernel64k_calls == [], "有 kernel_variant 不应调 apply_kernel_64k"
    db_session.refresh(request)
    assert request.status == VMRequestStatus.SUCCEEDED.value


def test_non_admin_vm_request_must_be_within_fourteen_days(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    vm_image: VMImage,
) -> None:
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    stub_vm_queue(monkeypatch, vm_image)

    missing_end = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(expected_ends_at=None),
        headers=auth_header(te_token, key="missing-end"),
    )
    too_long = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(
            expected_ends_at=(datetime.now(UTC) + timedelta(days=15)).isoformat(),
        ),
        headers=auth_header(te_token, key="too-long"),
    )

    assert missing_end.status_code == 403
    assert too_long.status_code == 403


def test_non_admin_vm_request_allows_one_minute_deadline_tolerance(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    vm_image: VMImage,
) -> None:
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    stub_vm_queue(monkeypatch, vm_image)

    accepted = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(
            expected_ends_at=(datetime.now(UTC) + timedelta(days=14, seconds=30)).isoformat(),
        ),
        headers=auth_header(te_token, key="vm-within-tolerance"),
    )
    rejected = client.post(
        "/api/v1/vm-requests",
        json=vm_request_payload(
            expected_ends_at=(datetime.now(UTC) + timedelta(days=14, minutes=2)).isoformat(),
        ),
        headers=auth_header(te_token, key="vm-outside-tolerance"),
    )

    assert accepted.status_code == 202
    assert rejected.status_code == 403


def test_vm_release_queues_destroy_task(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_virtual_resource(client, admin_token)
    lease = occupy_resource(client, te_token, str(resource["id"]), key="occupy-vm")
    queued_destroy: list[dict[str, object]] = []

    def fake_enqueue_destroy(**kwargs: object) -> str:
        queued_destroy.append(kwargs)
        return "destroy-task-1"

    monkeypatch.setattr(vm_service, "enqueue_vm_destroy", fake_enqueue_destroy)

    response = client.post(
        f"/api/v1/vms/{resource['id']}/release",
        json={"reason": "用完释放"},
        headers=auth_header(te_token, key="release-vm"),
    )

    assert response.status_code == 200
    assert response.json() == {"resource_id": resource["id"], "status": "queued"}
    assert queued_destroy == [
        {
            "resource_id": resource["id"],
            "lease_id": lease["id"],
            "actor_user_id": lease["user_id"],
            "reason": "用完释放",
            "force": False,
        }
    ]
    refreshed = client.get(
        f"/api/v1/resources/{resource['id']}",
        headers=auth_header(te_token),
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["current_lease_user_role"] == "TE"

    duplicate = client.post(
        f"/api/v1/vms/{resource['id']}/release",
        json={"reason": "再次释放"},
        headers=auth_header(te_token, key="release-vm-again"),
    )

    assert duplicate.status_code == 409
    assert len(queued_destroy) == 1
    assert (
        db_session.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == "release-vm-again")
        )
        is None
    )


def test_resource_detail_clears_stale_vm_destroy_lock_for_retry(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource_data = create_virtual_resource(client, admin_token)
    occupy_resource(client, te_token, str(resource_data["id"]), key="occupy-stale-vm")
    resource = db_session.get(Resource, str(resource_data["id"]))
    assert resource is not None
    old_time = datetime.now(UTC) - timedelta(minutes=80)
    mark_vm_destroy_started(
        resource,
        task_id="stale-destroy-task",
        started_at=old_time,
    )
    db_session.add(
        TaskEvent(
            task_type="vm_destroy",
            subject_type="resource",
            subject_id=resource.id,
            celery_task_id="stale-destroy-task",
            phase="destroy_started",
            message="worker 已领取 VM 销毁任务",
            created_at=old_time,
        )
    )
    db_session.commit()
    monkeypatch.setattr(vm_service, "enqueue_vm_destroy", lambda **_: "retry-destroy-task")

    detail = client.get(
        f"/api/v1/resources/{resource.id}",
        headers=auth_header(te_token),
    )
    retry = client.post(
        f"/api/v1/vms/{resource.id}/release",
        json={"reason": "重试释放"},
        headers=auth_header(te_token, key="retry-stale-destroy"),
    )

    db_session.refresh(resource)
    assert detail.status_code == 200
    assert retry.status_code == 200
    assert get_vm_destroy_execution(resource) is not None
    assert get_vm_destroy_execution(resource).task_id == "retry-destroy-task"


def test_release_vm_batch(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """批量释放：自己 VM→destroyed，他人→failed，ADMIN force→destroyed。"""
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te1_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    te2_token = login_as(client, db_session, username="te2", role=UserRole.TE)
    vm1 = create_virtual_resource(client, admin_token, resource_code="vm-b1")
    vm2 = create_virtual_resource(client, admin_token, resource_code="vm-b2")
    vm3 = create_virtual_resource(client, admin_token, resource_code="vm-b3")
    occupy_resource(client, te1_token, str(vm1["id"]), key="occ-1")
    occupy_resource(client, te1_token, str(vm2["id"]), key="occ-2")
    occupy_resource(client, te2_token, str(vm3["id"]), key="occ-3")

    monkeypatch.setattr(vm_service, "enqueue_vm_destroy", lambda **kw: "destroy-task")

    resp = client.post(
        "/api/v1/vms/batch-release",
        json={"resource_ids": [vm1["id"], vm2["id"], vm3["id"]], "reason": "批量释放"},
        headers=auth_header(te1_token, key="batch-release-1"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["destroyed"]) == {vm1["id"], vm2["id"]}
    assert body["failed"] == [vm3["id"]]

    resp2 = client.post(
        "/api/v1/vms/batch-release",
        json={"resource_ids": [vm3["id"]], "reason": "admin force"},
        headers=auth_header(admin_token, key="batch-release-2"),
    )
    assert resp2.status_code == 200
    assert resp2.json()["destroyed"] == [vm3["id"]]


def _make_resource_64k(rid: str = "r1", ip: str = "192.0.2.10") -> SimpleNamespace:
    """64k 测试用的 VM resource（带 virtual_spec 供 rollback 取 host/disk 信息）。"""
    return SimpleNamespace(
        id=rid,
        primary_ip=ip,
        os_version="openEuler-24.03-LTS-SP4",
        kernel_version=None,
        ssh_username="root",
        ssh_password_ciphertext=None,
        deleted_at=None,
        current_lease_id=None,
        occupancy_status=OccupancyStatus.IDLE.value,
        virtual_spec=SimpleNamespace(
            host_resource_id="h1",
            vm_name="vm-64k",
            system_disk_path="/data/disks/vm-64k.qcow2",
            data_disk_paths=[],
        ),
    )


def _make_request_64k(
    reqid: str = "req1",
    os_version: str = "openEuler-24.03-LTS-SP4-64k",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=reqid,
        os_version=os_version,
        requester_user_id="u1",
        task_id="t1",
        status="creating",
        error_code=None,
        error_message=None,
    )


def _fake_write_ok(*, target, path, content, timeout_seconds=30, **kwargs):  # noqa: ANN001
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def _install_ssh_fake(rounds_with_kernel: set[str]) -> tuple:
    """SSH fake：repoquery 命中给定 round 时返回非空 stdout，install/reboot 返回 0。

    返回 (fake, ssh_commands) 以便断言。
    """
    ssh_commands: list[str] = []
    echo_count = 0

    def fake_ssh(*, command, **kw):  # noqa: ANN001
        nonlocal echo_count
        ssh_commands.append(command)
        if "dnf repoquery" in command:
            present = any(r in command for r in rounds_with_kernel)
            return SimpleNamespace(
                returncode=0,
                stdout="kernel-64k.aarch64\n" if present else "",
                stderr="",
            )
        if command == "echo ok":
            echo_count += 1
            return SimpleNamespace(
                returncode=1 if echo_count == 1 else 0,
                stdout="" if echo_count == 1 else "ok\n",
                stderr="",
            )
        if command == "getconf PAGESIZE":
            return SimpleNamespace(returncode=0, stdout="65536\n", stderr="")
        if command == "uname -r":
            return SimpleNamespace(
                returncode=0,
                stdout="6.6.0-64k.aarch64\n",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return fake_ssh, ssh_commands


def test_apply_kernel_64k_when_os_version_has_64k_suffix(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """os_version 含 -64k → 写 update repo + repoquery 命中 + dnf install + reboot + 日志。"""
    from app.modules.vms.service import apply_kernel_64k

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20250101"],
    )
    write_calls: list[dict] = []

    def fake_write(*, target, path, content, **kw):  # noqa: ANN001
        write_calls.append({"path": path, "content": content})
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", fake_write)
    fake_ssh, ssh_commands = _install_ssh_fake({"update_20250101"})
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_64k()
    request = _make_request_64k()
    actor = SimpleNamespace(id="u1")

    apply_kernel_64k(db_session, request=request, resource=resource, actor=actor)

    assert write_calls, "should write per-round update repo file"
    assert "update_20250101" in write_calls[0]["content"]
    assert any("dnf repoquery" in c and "kernel-64k" in c for c in ssh_commands), ssh_commands
    assert any("dnf install" in c and "kernel-64k" in c for c in ssh_commands), ssh_commands
    assert any("grub2-set-default" in c for c in ssh_commands), ssh_commands
    assert any("reboot" in c for c in ssh_commands), ssh_commands
    assert "getconf PAGESIZE" in ssh_commands
    assert resource.os_version == "openEuler-24.03-LTS-SP4-64k"
    assert resource.kernel_version == "6.6.0-64k.aarch64"
    events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req1",
                TaskEvent.phase == "kernel_64k_installed",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert "update_20250101" in events[0].message
    check_events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req1",
                TaskEvent.phase == "kernel_64k_repo_check",
            )
        )
        .scalars()
        .all()
    )
    assert len(check_events) == 1
    assert "2025-01-01" in check_events[0].message
    assert "找到" in check_events[0].message


def test_apply_kernel_64k_skips_when_no_64k_suffix(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """os_version 不含 -64k → 不触发 64k 后处理（不枚举 round、不 SSH）。"""
    from app.modules.vms.service import apply_kernel_64k

    ssh_commands: list[str] = []
    list_calls: list = []

    def fake_ssh(*, host, username, password, command, **kw):  # noqa: ANN001
        ssh_commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    def fake_list_update_dirs(*, repo_base_url, version):  # noqa: ANN001
        list_calls.append(version)
        return ["update_20250101"]

    monkeypatch.setattr("app.modules.pipelines.repodata.list_update_dirs", fake_list_update_dirs)

    resource = _make_resource_64k(rid="r2", ip="192.0.2.11")
    request = _make_request_64k(reqid="req2", os_version="openEuler-24.03-LTS-SP4")
    actor = SimpleNamespace(id="u1")

    apply_kernel_64k(db_session, request=request, resource=resource, actor=actor)

    assert ssh_commands == []
    assert list_calls == [], "no -64k suffix should not enumerate update rounds"


def test_apply_kernel_64k_falls_back_to_older_round_when_latest_lacks_kernel_64k(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """最新轮无 kernel-64k → 回退上一轮 → 命中 → 装 + 日志记录命中的 round。"""
    from app.modules.vms.service import apply_kernel_64k

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20250108", "update_20250101"],
    )
    monkeypatch.setattr(
        "app.modules.test_management.remote.write_remote_file",
        _fake_write_ok,
    )
    fake_ssh, ssh_commands = _install_ssh_fake({"update_20250101"})
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_64k()
    request = _make_request_64k()
    actor = SimpleNamespace(id="u1")

    apply_kernel_64k(db_session, request=request, resource=resource, actor=actor)

    # 仅对 update_20250101 做了 install（update_20250108 repoquery 为空，不 install）
    install_cmds = [c for c in ssh_commands if "dnf install" in c and "kernel-64k" in c]
    assert len(install_cmds) == 1, ssh_commands
    assert resource.kernel_version == "6.6.0-64k.aarch64"
    events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req1",
                TaskEvent.phase == "kernel_64k_installed",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert "update_20250101" in events[0].message
    # 最新轮 update_20250108 无 64k → 记"未找到"；回退到 update_20250101 才装。
    check_events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req1",
                TaskEvent.phase == "kernel_64k_repo_check",
            )
        )
        .scalars()
        .all()
    )
    assert len(check_events) == 1
    assert "2025-01-08" in check_events[0].message
    assert "未找到" in check_events[0].message


def test_apply_kernel_64k_pipeline_does_not_fall_back_to_older_round(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """update 流水线最新轮无 64k 时返回未转测，不使用旧轮内核。"""
    from app.modules.vms.service import Kernel64kNotTransferredError, apply_kernel_64k

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20250108", "update_20250101"],
    )
    monkeypatch.setattr(
        "app.modules.test_management.remote.write_remote_file",
        _fake_write_ok,
    )
    fake_ssh, ssh_commands = _install_ssh_fake({"update_20250101"})
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    with pytest.raises(Kernel64kNotTransferredError):
        apply_kernel_64k(
            db_session,
            request=_make_request_64k(),
            resource=_make_resource_64k(),
            actor=SimpleNamespace(id="u1"),
            allow_round_fallback=False,
        )

    queries = [command for command in ssh_commands if "dnf repoquery" in command]
    assert len(queries) == 1
    assert "update_20250108" in queries[0]
    assert not any("dnf install" in command for command in ssh_commands)


def test_apply_kernel_64k_fails_when_booted_page_size_is_not_64k(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """安装并重启后实际页大小不是 65536，不能把资源标成 64k。"""
    from app.modules.vms.service import Kernel64kInstallError, apply_kernel_64k

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20250101"],
    )
    monkeypatch.setattr(
        "app.modules.test_management.remote.write_remote_file",
        _fake_write_ok,
    )
    base_fake, _commands = _install_ssh_fake({"update_20250101"})

    def fake_ssh(**kwargs):  # noqa: ANN003
        if kwargs["command"] == "getconf PAGESIZE":
            return SimpleNamespace(returncode=0, stdout="4096\n", stderr="")
        return base_fake(**kwargs)

    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)
    resource = _make_resource_64k()

    with pytest.raises(Kernel64kInstallError):
        apply_kernel_64k(
            db_session,
            request=_make_request_64k(),
            resource=resource,
            actor=SimpleNamespace(id="u1"),
        )

    assert resource.os_version == "openEuler-24.03-LTS-SP4"
    mismatch = db_session.execute(
        select(TaskEvent).where(
            TaskEvent.subject_id == "req1",
            TaskEvent.error_code == "kernel_64k_page_size_mismatch",
        )
    ).scalar_one()
    assert mismatch.level == "error"


def test_apply_kernel_64k_requires_ssh_to_go_down_after_reboot(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SSH 从未下线时不能把已有的 64k 运行状态误判为本次安装成功。"""
    from app.modules.vms.service import Kernel64kInstallError, apply_kernel_64k

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20250101"],
    )
    monkeypatch.setattr(
        "app.modules.test_management.remote.write_remote_file",
        _fake_write_ok,
    )

    def fake_ssh(*, command, **kwargs):  # noqa: ANN003
        if "dnf repoquery" in command:
            return SimpleNamespace(returncode=0, stdout="kernel-64k.aarch64\n", stderr="")
        if command == "echo ok":
            return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
        if command == "getconf PAGESIZE":
            return SimpleNamespace(returncode=0, stdout="65536\n", stderr="")
        if command == "uname -r":
            return SimpleNamespace(returncode=0, stdout="6.6.0-64k.aarch64\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    tick = [0.0]
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)
    monkeypatch.setattr(
        "time.monotonic",
        lambda: (tick.__setitem__(0, tick[0] + 10.0), tick[0])[1],
    )
    monkeypatch.setattr("time.sleep", lambda *_: None)

    with pytest.raises(Kernel64kInstallError, match="SSH did not go down"):
        apply_kernel_64k(
            db_session,
            request=_make_request_64k(),
            resource=_make_resource_64k(),
            actor=SimpleNamespace(id="u1"),
        )


def test_validate_kernel_64k_target_only_allows_sp4_aarch64() -> None:
    from app.modules.vms.service import (
        UnsupportedKernel64kVersionError,
        validate_kernel_64k_target,
    )

    validate_kernel_64k_target(
        os_version="openEuler-24.03-LTS-SP4-64k",
        arch="aarch64",
    )
    with pytest.raises(UnsupportedKernel64kVersionError):
        validate_kernel_64k_target(
            os_version="openEuler-24.03-LTS-SP3-64k",
            arch="aarch64",
        )
    with pytest.raises(UnsupportedKernel64kVersionError):
        validate_kernel_64k_target(
            os_version="openEuler-24.03-LTS-SP4-64k",
            arch="x86_64",
        )


def test_apply_kernel_64k_rolls_back_when_all_rounds_lack_kernel_64k(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5 轮全无 kernel-64k → 记 kernel_64k_not_found 事件 + 调 rollback + raise。"""
    from app.modules.vms.service import Kernel64kNotFoundError, apply_kernel_64k

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: [f"update_20250{i:02d}" for i in range(1, 6)],
    )
    monkeypatch.setattr(
        "app.modules.test_management.remote.write_remote_file",
        _fake_write_ok,
    )
    fake_ssh, _ = _install_ssh_fake(set())
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_64k()
    request = _make_request_64k()
    actor = SimpleNamespace(id="u1")

    with pytest.raises(Kernel64kNotFoundError):
        apply_kernel_64k(db_session, request=request, resource=resource, actor=actor)

    not_found = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req1",
                TaskEvent.phase == "kernel_64k_not_found",
            )
        )
        .scalars()
        .all()
    )
    assert len(not_found) == 1


def test_rollback_just_created_vm_destroys_and_fails_request(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rollback：跑 destroy-vm.sh + 释放租约 + 软删 resource + fail_request。"""
    from app.modules.vms.host_contract import VMHostDestroyPayload
    from app.modules.vms.service import Kernel64kNotFoundError, _rollback_just_created_vm

    host_script_calls: list[dict] = []
    release_calls: list[dict] = []

    def fake_host_script(**kw):  # noqa: ANN001
        host_script_calls.append(kw)
        return SimpleNamespace()

    def fake_release(db, *, command):  # noqa: ANN001
        release_calls.append({"lease_id": getattr(command.lease, "id", "?")})
        return command.lease

    lease = SimpleNamespace(id="l1", resource_id="r3", user_id="u1", released_at=None)

    monkeypatch.setattr("app.modules.vms.service.run_host_script", fake_host_script)
    monkeypatch.setattr("app.modules.vms.service.release_lease", fake_release)
    monkeypatch.setattr(
        "app.modules.vms.service.get_resource_active_lease",
        lambda db, resource: lease,
    )

    resource = SimpleNamespace(
        id="r3",
        primary_ip="192.0.2.13",
        deleted_at=None,
        current_lease_id="l1",
        occupancy_status=OccupancyStatus.IDLE.value,
        virtual_spec=SimpleNamespace(
            host_resource_id="h1",
            vm_name="vm-rollback",
            system_disk_path="/data/disks/vm-rollback.qcow2",
            data_disk_paths=[],
        ),
    )
    request = SimpleNamespace(
        id="req3",
        status="creating",
        error_code=None,
        error_message=None,
        task_id="t3",
    )
    host = SimpleNamespace(id="h1", primary_ip="192.168.131.1")
    actor = SimpleNamespace(id="u1")

    _rollback_just_created_vm(
        db_session,
        draft=VMRollbackContext(
            request=request,
            resource=resource,
            actor=actor,
            host=host,
            error=Kernel64kNotFoundError(
                "no kernel-64k in any update round for openEuler-24.03-LTS-SP4"
            ),
        ),
    )

    assert host_script_calls and host_script_calls[0]["script_name"] == "destroy-vm.sh"
    payload = host_script_calls[0]["payload"]
    assert isinstance(payload, VMHostDestroyPayload)
    assert payload.vm_name == "vm-rollback"
    assert payload.system_disk_path == "/data/disks/vm-rollback.qcow2"
    assert release_calls, "should release the active lease"
    assert resource.deleted_at is not None
    assert resource.current_lease_id is None
    assert resource.occupancy_status == OccupancyStatus.IDLE.value
    assert request.status == VMRequestStatus.FAILED.value
    assert request.error_code == "kernel_64k_not_found"
    assert "no kernel-64k" in (request.error_message or "")


def test_apply_kernel_64k_to_physical_installs_and_logs(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """物理机 -64k：install_kernel_64k_via_ssh 装成功 + _record_event 记 resource 事件。"""
    from app.modules.vms.pxe_install import TASK_TYPE_PXE_INSTALL, apply_kernel_64k_to_physical

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20250101"],
    )
    monkeypatch.setattr(
        "app.modules.test_management.remote.write_remote_file",
        _fake_write_ok,
    )
    fake_ssh, ssh_commands = _install_ssh_fake({"update_20250101"})
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_64k(rid="rp1", ip="192.0.2.20")
    apply_kernel_64k_to_physical(
        db_session,
        resource=resource,
        os_version="openEuler-24.03-LTS-SP4-64k",
        subject_id="rp1",
    )

    assert any("dnf install" in c and "kernel-64k" in c for c in ssh_commands), ssh_commands
    assert resource.kernel_version == "6.6.0-64k.aarch64"
    start_events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "resource",
                TaskEvent.subject_id == "rp1",
                TaskEvent.phase == "kernel_64k_install_start",
            )
        )
        .scalars()
        .all()
    )
    assert len(start_events) == 1
    events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "resource",
                TaskEvent.subject_id == "rp1",
                TaskEvent.phase == "kernel_64k_installed",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].task_type == TASK_TYPE_PXE_INSTALL
    assert "update_20250101" in events[0].message


def test_apply_kernel_64k_to_physical_marks_latest_round_not_transferred(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """物理流水线只检查最新轮，无 64k 时返回未转测。"""
    from app.modules.vms.pxe_install import apply_kernel_64k_to_physical
    from app.modules.vms.service import Kernel64kNotTransferredError

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: [f"update_20250{i:02d}" for i in range(1, 6)],
    )
    monkeypatch.setattr(
        "app.modules.test_management.remote.write_remote_file",
        _fake_write_ok,
    )
    fake_ssh, _ = _install_ssh_fake(set())
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_64k(rid="rp2", ip="192.0.2.21")
    with pytest.raises(Kernel64kNotTransferredError):
        apply_kernel_64k_to_physical(
            db_session,
            resource=resource,
            os_version="openEuler-24.03-LTS-SP4-64k",
            subject_id="rp2",
        )

    not_found = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "resource",
                TaskEvent.subject_id == "rp2",
                TaskEvent.phase == "kernel_64k_not_transferred",
            )
        )
        .scalars()
        .all()
    )
    assert len(not_found) == 1
    assert not_found[0].level == "warning"
    assert not_found[0].error_code is None


def _make_resource_latest(rid: str = "rl1", ip: str = "192.0.2.30") -> SimpleNamespace:
    """latest-kernel 测试用的物理机 resource（无 virtual_spec）。"""
    return SimpleNamespace(
        id=rid,
        primary_ip=ip,
        kernel_version=None,
        ssh_username="root",
        ssh_password_ciphertext=None,
    )


def test_install_latest_kernel_writes_repo_installs_reboots_reads_uname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """装最新 update kernel：写最新轮 repo + dnf install kernel + reboot + uname + 记 installed。"""
    from app.modules.vms.service import install_latest_kernel_via_ssh

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20260101"],
    )
    writes: list[tuple[str, str]] = []

    def fake_write(*, target, path, content, timeout_seconds=30, **kwargs):  # noqa: ANN001
        writes.append((path, content))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", fake_write)

    cmds: list[str] = []
    echo_n = {"n": 0}

    def fake_ssh(*, host, username, password, command, **kw):  # noqa: ANN001
        cmds.append(command)
        if command == "uname -r":
            return SimpleNamespace(returncode=0, stdout="5.10.0-foo.x86_64\n", stderr="")
        if command == "echo ok":
            echo_n["n"] += 1
            # phase1（等下线）首探非零；phase2（等回来）次探零——零 sleep 跳出两段等待。
            return SimpleNamespace(returncode=(1 if echo_n["n"] == 1 else 0), stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_latest()
    events: list[tuple] = []

    def rec(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        events.append((phase, message, level, error_code))

    install_latest_kernel_via_ssh(os_version="24.03-LTS-SP4", resource=resource, record_event=rec)

    assert writes, "should write latest-round update repo file"
    assert "update_20260101" in writes[0][1]
    assert any("dnf install" in c and "kernel" in c and "64k" not in c for c in cmds), cmds
    assert any(c == "reboot" for c in cmds), cmds
    assert any(c == "uname -r" for c in cmds), cmds
    assert resource.kernel_version == "5.10.0-foo.x86_64"
    assert events and events[-1][0] == "kernel_latest_installed"
    assert "update_20260101" in events[-1][1]


def test_install_latest_kernel_records_failed_and_raises_when_dnf_install_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dnf install 失败 → 记 failed + raise；不继续 reboot/uname。"""
    from app.modules.vms.service import (
        LatestKernelInstallError,
        install_latest_kernel_via_ssh,
    )

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20260101"],
    )
    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", _fake_write_ok)
    cmds: list[str] = []

    def fake_ssh(*, host, username, password, command, **kw):  # noqa: ANN001
        cmds.append(command)
        if "dnf install -y kernel" in command:
            return SimpleNamespace(returncode=1, stdout="", stderr="boom no package")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_latest()
    events: list[tuple] = []

    def rec(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        events.append((phase, message, level, error_code))

    with pytest.raises(LatestKernelInstallError):
        install_latest_kernel_via_ssh(
            os_version="24.03-LTS-SP4", resource=resource, record_event=rec
        )

    # 未继续 reboot / uname
    assert not any(c == "reboot" for c in cmds), cmds
    assert not any(c == "uname -r" for c in cmds), cmds
    # 记失败事件 + error_code
    failed = [e for e in events if e[0] == "kernel_latest_install_failed"]
    assert len(failed) == 1
    assert failed[0][2] == "error"
    assert failed[0][3] == "kernel_latest_dnf_install_failed"
    assert resource.kernel_version is None


def test_install_latest_kernel_raises_when_no_update_rounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """无 update 轮次 → 记 kernel_latest_no_rounds + raise；不 SSH。"""
    from app.modules.vms.service import (
        LatestKernelInstallError,
        install_latest_kernel_via_ssh,
    )

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: [],
    )

    resource = _make_resource_latest()
    events: list[tuple] = []

    def rec(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        events.append((phase, message, level, error_code))

    with pytest.raises(LatestKernelInstallError):
        install_latest_kernel_via_ssh(
            os_version="24.03-LTS-SP3", resource=resource, record_event=rec
        )

    failed = [e for e in events if e[0] == "kernel_latest_install_failed"]
    assert len(failed) == 1
    assert failed[0][3] == "kernel_latest_no_rounds"
    assert resource.kernel_version is None


def test_install_latest_kernel_raises_when_ssh_not_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reboot 后 SSH 不回（echo ok 永远非 0）→ phase2 轮询到 deadline → 记 ssh_not_back + raise。"""
    from app.modules.vms.service import (
        LatestKernelInstallError,
        install_latest_kernel_via_ssh,
    )

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20260101"],
    )
    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", _fake_write_ok)
    cmds: list[str] = []

    def fake_ssh(*, host, username, password, command, **kw):  # noqa: ANN001
        cmds.append(command)
        # dnf install / reboot 成功；echo ok 永远非 0（SSH 不回）
        rc = 0 if "dnf install -y kernel" in command or command == "reboot" else 1
        return SimpleNamespace(returncode=rc, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)
    # 推进时间让 phase2 的 up_deadline 到达；sleep 不真睡
    tick = [0.0]
    monkeypatch.setattr("time.monotonic", lambda: (tick.__setitem__(0, tick[0] + 10.0), tick[0])[1])
    monkeypatch.setattr("time.sleep", lambda *_: None)

    resource = _make_resource_latest()
    events: list[tuple] = []

    def rec(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        events.append((phase, message, level, error_code))

    with pytest.raises(LatestKernelInstallError):
        install_latest_kernel_via_ssh(
            os_version="24.03-LTS-SP3", resource=resource, record_event=rec
        )

    failed = [e for e in events if e[0] == "kernel_latest_install_failed"]
    assert len(failed) == 1
    assert failed[0][3] == "kernel_latest_ssh_not_back"
    # phase2 确实轮询了（不止一次 echo ok）+ uname 未执行
    assert sum(1 for c in cmds if c == "echo ok") > 1, cmds
    assert not any(c == "uname -r" for c in cmds), cmds
    assert resource.kernel_version is None


def test_install_latest_kernel_raises_when_uname_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SSH 回来但 uname -r 非零 → 记 uname_failed + raise；kernel_version 不设。"""
    from app.modules.vms.service import (
        LatestKernelInstallError,
        install_latest_kernel_via_ssh,
    )

    monkeypatch.setattr(
        "app.modules.pipelines.repodata.list_update_dirs",
        lambda *, repo_base_url, version: ["update_20260101"],
    )
    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", _fake_write_ok)
    echo_n = {"n": 0}

    def fake_ssh(*, host, username, password, command, **kw):  # noqa: ANN001
        if command == "uname -r":
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if command == "echo ok":
            echo_n["n"] += 1
            return SimpleNamespace(returncode=(1 if echo_n["n"] == 1 else 0), stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)

    resource = _make_resource_latest()
    events: list[tuple] = []

    def rec(phase, message, *, level="info", error_code=None):  # noqa: ANN001
        events.append((phase, message, level, error_code))

    with pytest.raises(LatestKernelInstallError):
        install_latest_kernel_via_ssh(
            os_version="24.03-LTS-SP3", resource=resource, record_event=rec
        )

    failed = [e for e in events if e[0] == "kernel_latest_install_failed"]
    assert len(failed) == 1
    assert failed[0][3] == "kernel_latest_uname_failed"
    assert resource.kernel_version is None


def test_vm_owner_can_refresh_ip_from_dhcp_lease(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_virtual_resource(
        client,
        admin_token,
        mac_address="52:54:00:12:34:56",
        primary_ip="172.168.131.201",
    )
    occupy_resource(client, te_token, str(resource["id"]), key="occupy-vm-refresh")
    monkeypatch.setattr(
        vm_service,
        "fetch_dhcp_leases",
        lambda _url: (
            """
lease 172.168.131.201 {
  hardware ethernet 52:54:00:12:34:56;
}
lease 172.168.131.220 {
  hardware ethernet 52:54:00:12:34:56;
}
"""
        ),
    )

    response = client.post(
        f"/api/v1/vms/{resource['id']}/refresh-ip",
        headers=auth_header(te_token),
    )

    assert response.status_code == 200
    assert response.json()["primary_ip"] == "172.168.131.220"

    stored = db_session.get(Resource, resource["id"])
    assert stored is not None
    assert stored.primary_ip == "172.168.131.220"

    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "vm.refresh_ip"))
    assert audit is not None
    assert audit.target_id == resource["id"]
    assert audit.detail["old_primary_ip"] == "172.168.131.201"
    assert audit.detail["new_primary_ip"] == "172.168.131.220"


def test_non_owner_cannot_refresh_vm_ip(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    owner_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    other_token = login_as(client, db_session, username="te2", role=UserRole.TE)
    resource = create_virtual_resource(
        client,
        admin_token,
        mac_address="52:54:00:12:34:56",
    )
    occupy_resource(client, owner_token, str(resource["id"]), key="occupy-vm-owner")
    monkeypatch.setattr(
        vm_service,
        "fetch_dhcp_leases",
        lambda _url: pytest.fail("forbidden refresh must not fetch DHCP leases"),
    )

    response = client.post(
        f"/api/v1/vms/{resource['id']}/refresh-ip",
        headers=auth_header(other_token),
    )

    assert response.status_code == 403


def test_vm_owner_can_read_console_config(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    owner_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_virtual_resource(
        client,
        admin_token,
        host_resource_id=host["id"],
        vnc_port=5901,
        vnc_websocket_port=5701,
    )
    occupy_resource(client, owner_token, str(resource["id"]), key="occupy-vm-console")

    response = client.get(
        f"/api/v1/vms/{resource['id']}/console",
        headers=auth_header(owner_token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "resource_id": resource["id"],
        "vm_name": resource["vm_name"],
        "url": "ws://172.168.131.75:5701/",
        "port": 5901,
        "websocket_port": 5701,
        "password": None,
    }


def test_non_owner_cannot_read_console_config(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    owner_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    other_token = login_as(client, db_session, username="te2", role=UserRole.TE)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_virtual_resource(
        client,
        admin_token,
        host_resource_id=host["id"],
    )
    occupy_resource(client, owner_token, str(resource["id"]), key="occupy-vm-console")

    response = client.get(
        f"/api/v1/vms/{resource['id']}/console",
        headers=auth_header(other_token),
    )

    assert response.status_code == 403


def test_vm_console_config_requires_websocket_port(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_virtual_resource(
        client,
        admin_token,
        host_resource_id=host["id"],
        vnc_websocket_port=None,
    )

    response = client.get(
        f"/api/v1/vms/{resource['id']}/console",
        headers=auth_header(admin_token),
    )

    assert response.status_code == 409


def test_vm_owner_can_read_power_state(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    owner_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_virtual_resource(client, admin_token, host_resource_id=host["id"])
    occupy_resource(client, owner_token, str(resource["id"]), key="occupy-vm-power")
    calls: list[dict[str, object]] = []

    def fake_run_host_script(**kwargs: object) -> VMHostPowerResult:
        calls.append(kwargs)
        return VMHostPowerResult(status="success", power_state="running")

    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)

    response = client.get(
        f"/api/v1/vms/{resource['id']}/power",
        headers=auth_header(owner_token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "resource_id": resource["id"],
        "vm_name": resource["vm_name"],
        "power_state": "running",
    }
    assert len(calls) == 1
    assert calls[0]["host_ip"] == host["primary_ip"]
    assert calls[0]["script_name"] == "power-vm.sh"
    payload = calls[0]["payload"]
    assert payload.vm_name == resource["vm_name"]
    assert payload.action == "state"


def test_destroyed_vm_power_and_events_remain_readable(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_virtual_resource(client, admin_token)
    resource_row = db_session.get(Resource, resource["id"])
    resource_row.deleted_at = datetime.now(UTC)
    event = TaskEvent(
        task_type="vm_destroy",
        subject_type="resource",
        subject_id=resource_row.id,
        phase="destroy_succeeded",
        message="VM 销毁成功",
    )
    db_session.add(event)
    db_session.commit()

    power_response = client.get(
        f"/api/v1/vms/{resource['id']}/power",
        headers=auth_header(admin_token),
    )
    events_response = client.get(
        f"/api/v1/vms/{resource['id']}/events",
        headers=auth_header(admin_token),
    )

    assert power_response.status_code == 200
    assert power_response.json()["power_state"] == "destroyed"
    assert events_response.status_code == 200
    assert [row["phase"] for row in events_response.json()] == ["destroy_succeeded"]


def test_vm_owner_can_reboot_vm_and_audit_operation(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    owner_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_virtual_resource(client, admin_token, host_resource_id=host["id"])
    occupy_resource(client, owner_token, str(resource["id"]), key="occupy-vm-reboot")
    calls: list[dict[str, object]] = []

    def fake_run_host_script(**kwargs: object) -> VMHostPowerResult:
        calls.append(kwargs)
        return VMHostPowerResult(status="success", power_state="running")

    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)

    response = client.post(
        f"/api/v1/vms/{resource['id']}/power",
        json={"action": "reboot"},
        headers=auth_header(owner_token, key="reboot-vm"),
    )
    replay = client.post(
        f"/api/v1/vms/{resource['id']}/power",
        json={"action": "reboot"},
        headers=auth_header(owner_token, key="reboot-vm"),
    )

    assert response.status_code == 200
    assert response.json()["power_state"] == "running"
    assert replay.status_code == 200
    assert replay.json() == response.json()
    assert len(calls) == 1
    payload = calls[0]["payload"]
    assert payload.action == "reboot"

    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "vm.power.reboot"))
    assert audit is not None
    assert audit.target_id == resource["id"]
    assert audit.detail["vm_name"] == resource["vm_name"]
    assert audit.detail["host_ip"] == host["primary_ip"]
    assert audit.detail["power_state"] == "running"


def test_non_owner_cannot_operate_vm_power(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    owner_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    other_token = login_as(client, db_session, username="te2", role=UserRole.TE)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_virtual_resource(client, admin_token, host_resource_id=host["id"])
    occupy_resource(client, owner_token, str(resource["id"]), key="occupy-vm-power-owner")
    monkeypatch.setattr(
        vm_service,
        "run_host_script",
        lambda **_kwargs: pytest.fail("forbidden power operation must not reach host"),
    )

    response = client.post(
        f"/api/v1/vms/{resource['id']}/power",
        json={"action": "shutdown"},
        headers=auth_header(other_token, key="forbidden-vm-power"),
    )

    assert response.status_code == 403


def test_vm_power_requires_valid_idempotency_key(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)

    missing = client.post(
        "/api/v1/vms/missing/power",
        json={"action": "reboot"},
        headers=auth_header(token),
    )
    too_long = client.post(
        "/api/v1/vms/missing/power",
        json={"action": "reboot"},
        headers=auth_header(token, key="x" * 256),
    )

    assert missing.status_code == 400
    assert too_long.status_code == 400
    assert missing.json()["error"]["code"] == "bad_request"
    assert too_long.json()["error"]["code"] == "bad_request"


def test_vm_power_conflict_releases_idempotency_key(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_virtual_resource(client, token)

    response = client.post(
        f"/api/v1/vms/{resource['id']}/power",
        json={"action": "reboot"},
        headers=auth_header(token, key="power-without-lease"),
    )

    assert response.status_code == 409
    assert (
        db_session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.idempotency_key == "power-without-lease"
            )
        )
        is None
    )


def test_refresh_vm_ip_keeps_existing_ip_when_dhcp_lease_is_missing(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    resource = create_virtual_resource(
        client,
        admin_token,
        mac_address="52:54:00:12:34:56",
        primary_ip="172.168.131.201",
    )
    monkeypatch.setattr(
        vm_service,
        "fetch_dhcp_leases",
        lambda _url: "lease 172.168.131.220 { hardware ethernet 52:54:00:aa:bb:cc; }",
    )

    response = client.post(
        f"/api/v1/vms/{resource['id']}/refresh-ip",
        headers=auth_header(admin_token),
    )

    assert response.status_code == 404
    stored = db_session.get(Resource, resource["id"])
    assert stored is not None
    assert stored.primary_ip == "172.168.131.201"


def test_generic_lease_release_rejects_virtual_resource(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    resource = create_virtual_resource(client, admin_token)
    lease = occupy_resource(client, te_token, str(resource["id"]), key="occupy-vm")

    own_release = client.post(
        f"/api/v1/leases/{lease['id']}/release",
        json={"reason": "用完释放"},
        headers=auth_header(te_token, key="generic-vm-release"),
    )
    force_release = client.post(
        f"/api/v1/leases/{lease['id']}/force-release",
        json={"reason": "强制回收"},
        headers=auth_header(admin_token, key="generic-vm-force-release"),
    )

    assert own_release.status_code == 403
    assert force_release.status_code == 403
    assert own_release.json()["error"]["message"] == "虚拟机租约必须通过虚拟机释放功能处理"
    stored_lease = db_session.get(ResourceLease, lease["id"])
    stored_resource = db_session.get(Resource, resource["id"])
    assert stored_lease is not None
    assert stored_lease.released_at is None
    assert stored_resource is not None
    assert stored_resource.occupancy_status == OccupancyStatus.OCCUPIED.value


def test_vm_destroy_uses_authorized_lease_id(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_resource(
        client,
        admin_token,
        virtual_resource_payload(
            host_resource_id=host["id"],
            system_disk_path="/var/lib/libvirt/images/kronos/instances/vm.qcow2",
        ),
    )
    lease = occupy_resource(client, te_token, str(resource["id"]), key="occupy-vm")
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        vm_service,
        "run_host_script",
        lambda **kwargs: calls.append(kwargs) or {"status": "success"},
    )

    vm_service.process_vm_destroy(
        str(resource["id"]),
        "stale-lease-id",
        options=VMDestroyOptions(
            actor_user_id=str(lease["user_id"]),
            reason="用完释放",
            force=False,
        ),
    )

    stored_lease = db_session.get(ResourceLease, lease["id"])
    stored_resource = db_session.get(Resource, resource["id"])
    assert calls == []
    assert stored_lease is not None
    assert stored_lease.released_at is None
    assert stored_resource is not None
    assert stored_resource.deleted_at is None

    vm_service.process_vm_destroy(
        str(resource["id"]),
        str(lease["id"]),
        options=VMDestroyOptions(
            actor_user_id=str(lease["user_id"]),
            reason="用完释放",
            force=False,
        ),
    )

    db_session.refresh(stored_lease)
    db_session.refresh(stored_resource)
    assert len(calls) == 1
    assert stored_lease.released_at is not None
    assert stored_resource.deleted_at is not None
    assert stored_resource.current_lease_id is None
    assert stored_resource.occupancy_status == OccupancyStatus.IDLE.value


def _destroy_test_setup(
    client: TestClient,
    db_session: Session,
    key: str,
) -> tuple[str, str, str]:
    """销毁测试公共脚手架：admin 建宿主+VM，TE 占用，返回 (resource_id, lease_id, user_id)。"""
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    te_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    host = create_resource(client, admin_token, physical_host_payload())
    resource = create_resource(
        client,
        admin_token,
        virtual_resource_payload(
            host_resource_id=host["id"],
            system_disk_path="/var/lib/libvirt/images/kronos/instances/vm.qcow2",
        ),
    )
    lease = occupy_resource(client, te_token, str(resource["id"]), key=key)
    return str(resource["id"]), str(lease["id"]), str(lease["user_id"])


def test_vm_destroy_retries_connection_failure(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """host_connection_failed 属瞬时故障(批量并发 SSH 超 sshd MaxStartups)，重试自愈。"""
    resource_id, lease_id, user_id = _destroy_test_setup(
        client, db_session, "occupy-destroy-retry"
    )
    calls: list[str] = []

    def fake_run_host_script(**kwargs: object) -> object:
        script_name = str(kwargs.get("script_name"))
        calls.append(script_name)
        if len(calls) == 1:
            raise host_runner.HostScriptError(
                "host_connection_failed",
                "kex_exchange_identification: read: Connection reset by peer",
            )
        return {"status": "success"}

    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)
    monkeypatch.setattr(vm_service.time, "sleep", lambda _s: None)

    vm_service.process_vm_destroy(
        resource_id,
        lease_id,
        options=VMDestroyOptions(actor_user_id=user_id, reason="用完释放", force=False),
    )

    assert calls == ["destroy-vm.sh", "destroy-vm.sh"]
    stored_lease = db_session.get(ResourceLease, lease_id)
    stored_resource = db_session.get(Resource, resource_id)
    assert stored_lease is not None
    assert stored_lease.released_at is not None
    assert stored_resource is not None
    assert stored_resource.deleted_at is not None
    retry_event = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.task_type == "vm_destroy",
                TaskEvent.phase == "destroy_retrying",
            )
        )
        .scalars()
        .first()
    )
    assert retry_event is not None


def test_vm_destroy_connection_failure_exhausted_records_host_facts(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """重试耗尽后回读宿主：VM 仍在时按失败处理，事件需携带宿主实际状态供详情页展示。"""
    resource_id, lease_id, user_id = _destroy_test_setup(
        client, db_session, "occupy-destroy-exhausted"
    )
    inspect_calls: list[int] = []

    def fake_run_host_script(**kwargs: object) -> object:
        if kwargs.get("script_name") == "inspect-vm.sh":
            inspect_calls.append(1)
            return {
                "status": "success",
                "domain_exists": True,
                "power_state": "running",
                "system_disk_exists": True,
                "data_disks_existing": [],
            }
        raise host_runner.HostScriptError("host_connection_failed", "connection reset")

    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)
    monkeypatch.setattr(vm_service.time, "sleep", lambda _s: None)

    vm_service.process_vm_destroy(
        resource_id,
        lease_id,
        options=VMDestroyOptions(actor_user_id=user_id, reason="用完释放", force=False),
    )

    assert len(inspect_calls) == 1
    stored_lease = db_session.get(ResourceLease, lease_id)
    stored_resource = db_session.get(Resource, resource_id)
    assert stored_lease is not None
    assert stored_lease.released_at is None
    assert stored_resource is not None
    assert stored_resource.deleted_at is None
    failure_event = (
        db_session.execute(
            select(TaskEvent)
            .where(
                TaskEvent.task_type == "vm_destroy",
                TaskEvent.phase == "host_script_failed",
            )
            .order_by(TaskEvent.created_at.desc(), TaskEvent.id.desc())
        )
        .scalars()
        .first()
    )
    assert failure_event is not None
    assert failure_event.error_code == "host_connection_failed"
    assert "running" in failure_event.message


def test_vm_destroy_converges_when_host_confirms_missing(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """脚本失败但回读确认 VM 与磁盘已不存在（半执行/外部清理），按宿主事实落账收敛而非记失败。"""
    resource_id, lease_id, user_id = _destroy_test_setup(
        client, db_session, "occupy-destroy-converge"
    )

    def fake_run_host_script(**kwargs: object) -> object:
        if kwargs.get("script_name") == "inspect-vm.sh":
            return {
                "status": "success",
                "domain_exists": False,
                "power_state": None,
                "system_disk_exists": False,
                "data_disks_existing": [],
            }
        raise host_runner.HostScriptError("vm_destroy_failed", "failed to undefine VM")

    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)

    vm_service.process_vm_destroy(
        resource_id,
        lease_id,
        options=VMDestroyOptions(actor_user_id=user_id, reason="用完释放", force=False),
    )

    stored_lease = db_session.get(ResourceLease, lease_id)
    stored_resource = db_session.get(Resource, resource_id)
    assert stored_lease is not None
    assert stored_lease.released_at is not None
    assert stored_resource is not None
    assert stored_resource.deleted_at is not None
    succeeded_event = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.task_type == "vm_destroy",
                TaskEvent.phase == "destroy_succeeded",
            )
        )
        .scalars()
        .first()
    )
    assert succeeded_event is not None
    assert "宿主" in succeeded_event.message


def test_vm_request_claim_is_single_owner(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = VMRequest(
        requester_user_id="user-id",
        status=VMRequestStatus.PENDING.value,
        purpose="调试 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        image_url="http://example.test/openEuler.qcow2",
        vcpu_count=2,
        memory_mb=4096,
        disk_gb=0,
        data_disk_count=0,
        data_disk_size_gb=50,
        host_attempts=[],
    )
    db_session.add(request)
    db_session.commit()

    original_commit = db_session.commit
    monkeypatch.setattr(
        db_session,
        "commit",
        lambda: pytest.fail("claim must be committed with the started event"),
    )
    first_claim = vm_service.claim_pending_vm_request(db_session, request.id)
    monkeypatch.setattr(db_session, "commit", original_commit)
    original_commit()
    second_claim = vm_service.claim_pending_vm_request(db_session, request.id)

    assert first_claim is not None
    assert first_claim.status == VMRequestStatus.CREATING.value
    assert second_claim is None


def test_cancel_vm_request_does_not_overwrite_creating_transition(
    db_session: Session,
) -> None:
    actor = create_user(
        db_session,
        username="vmrequester",
        password="test-pass",
        role=UserRole.TE,
        display_name="vmrequester",
    )
    request = VMRequest(
        requester_user_id=actor.id,
        status=VMRequestStatus.PENDING.value,
        purpose="调试 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        image_url="http://example.test/openEuler.qcow2",
        vcpu_count=2,
        memory_mb=4096,
        disk_gb=0,
        data_disk_count=0,
        data_disk_size_gb=50,
        host_attempts=[],
    )
    db_session.add(request)
    db_session.commit()

    db_session.execute(
        update(VMRequest)
        .where(VMRequest.id == request.id)
        .values(status=VMRequestStatus.CREATING.value)
        .execution_options(synchronize_session=False)
    )
    assert request.status == VMRequestStatus.PENDING.value

    with pytest.raises(vm_service.VMConflictError):
        vm_service.cancel_vm_request(db_session, request=request, actor=actor)

    db_session.expire(request)
    assert request.status == VMRequestStatus.CREATING.value
    assert request.cancelled_at is None
    assert request.completed_at is None


def test_process_vm_request_records_failure_events_when_no_host(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = create_user(
        db_session,
        username="te1",
        password="test-pass",
        role=UserRole.TE,
        display_name="te1",
    )
    request = VMRequest(
        requester_user_id=actor.id,
        status=VMRequestStatus.PENDING.value,
        purpose="调试 openEuler",
        expected_ends_at=datetime.now(UTC) + timedelta(days=1),
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        image_url="http://example.test/openEuler.qcow2",
        vcpu_count=2,
        memory_mb=4096,
        disk_gb=0,
        data_disk_count=0,
        data_disk_size_gb=50,
        task_id="task-1",
        host_attempts=[],
    )
    db_session.add(request)
    db_session.commit()
    monkeypatch.setattr(vm_service, "SessionLocal", lambda: nullcontext(db_session))

    vm_service.process_vm_request(request.id)

    stored = db_session.get(VMRequest, request.id)
    assert stored is not None
    assert stored.status == VMRequestStatus.FAILED.value
    assert stored.error_code == "capacity_insufficient"

    events = list(
        db_session.execute(
            select(TaskEvent)
            .where(TaskEvent.subject_id == request.id)
            .order_by(TaskEvent.created_at)
        ).scalars()
    )
    assert [(event.phase, event.level, event.error_code) for event in events] == [
        ("started", "info", None),
        ("failed", "error", "capacity_insufficient"),
    ]


def test_host_script_error_json_preserves_error_code(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_run(*_args: object, **_kwargs: object) -> CompletedProcess[str]:
        stdout = '{"status":"error","error_code":"capacity_insufficient","error_message":"no cpu"}'
        return CompletedProcess(
            args=["ssh"],
            returncode=1,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(host_runner, "_run_host_process", fake_run)

    with pytest.raises(host_runner.HostScriptError) as exc_info:
        host_runner.run_host_script(
            host_ip="172.168.131.75",
            script_name="create-vm.sh",
            payload={"vm_name": "vm-test"},
        )

    assert exc_info.value.code == "capacity_insufficient"
    assert str(exc_info.value) == "no cpu"


def test_host_script_parses_json_result_from_noisy_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def fake_run(*_args: object, **_kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(
            args=["ssh"],
            returncode=0,
            stdout=(
                "Authorized users only. All activities may be monitored and reported.\n"
                '{"status":"success","power_state":"running"}\n'
            ),
            stderr="",
        )

    monkeypatch.setattr(host_runner, "_run_host_process", fake_run)

    result = host_runner.run_host_script(
        host_ip="172.168.131.75",
        script_name="power-vm.sh",
        payload={"vm_name": "vm-test", "action": "state"},
        result_model=VMHostPowerResult,
    )

    assert result.power_state == "running"


def test_host_script_error_json_includes_stderr_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def fake_run(*_args: object, **_kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(
            args=["ssh"],
            returncode=1,
            stdout=(
                '{"status":"error",'
                '"error_code":"vm_create_failed",'
                '"error_message":"failed to define VM"}'
            ),
            stderr=(
                "Warning: Permanently added '172.168.131.92' (ED25519) "
                "to the list of known hosts.\n"
                "Authorized users only. All activities may be monitored and reported.\n"
                "KRONOS_EVENT\tdefine_vm\t定义 libvirt domain\n"
                "error: Failed to define domain from /tmp/tmp.xml\n"
                "error: unsupported configuration: unknown OS type hvm\n"
                "KRONOS_EVENT\trollback\t清理已创建的 VM 和磁盘\n"
            ),
        )

    monkeypatch.setattr(host_runner, "_run_host_process", fake_run)

    with pytest.raises(host_runner.HostScriptError) as exc_info:
        host_runner.run_host_script(
            host_ip="172.168.131.75",
            script_name="create-vm.sh",
            payload={"vm_name": "vm-test"},
        )

    message = str(exc_info.value)
    assert exc_info.value.code == "vm_create_failed"
    assert "failed to define VM" in message
    assert "unsupported configuration" in message
    assert "Permanently added" not in message
    assert "Authorized users only" not in message
    assert "KRONOS_EVENT" not in message
    assert "清理已创建的 VM 和磁盘" not in message


def test_host_script_records_stage_events(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_run(command: list[str], *_args: object, **kwargs: object) -> CompletedProcess[str]:
        assert "ConnectTimeout=10" in command
        event_sink = kwargs["event_sink"]
        assert callable(event_sink)
        event_sink("check_capacity", "检查宿主机实时容量")
        return CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"status":"success"}',
            stderr="noise\n",
        )

    events: list[tuple[str, str]] = []
    monkeypatch.setattr(host_runner, "_run_host_process", fake_run)

    host_runner.run_host_script(
        host_ip="172.168.131.75",
        script_name="create-vm.sh",
        payload={"vm_name": "vm-test"},
        event_sink=lambda phase, message: events.append((phase, message)),
    )

    assert events == [("check_capacity", "检查宿主机实时容量")]


def test_host_script_streams_stage_events_before_process_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_popen = host_runner.subprocess.Popen

    def fake_popen(_command: list[str], **kwargs: object) -> subprocess.Popen[str]:
        return real_popen(
            [
                sys.executable,
                "-c",
                (
                    "import sys, time\n"
                    "print('KRONOS_EVENT\\tcheck_capacity\\t检查宿主机实时容量', "
                    "file=sys.stderr, flush=True)\n"
                    "sys.stdin.read()\n"
                    "time.sleep(0.3)\n"
                    'print(\'{"status":"success"}\', flush=True)\n'
                ),
            ],
            **kwargs,
        )

    events: list[tuple[str, str]] = []
    event_seen = threading.Event()
    result: dict[str, object] = {}

    def event_sink(phase: str, message: str) -> None:
        events.append((phase, message))
        event_seen.set()

    def run_script() -> None:
        result["value"] = host_runner.run_host_script(
            host_ip="172.168.131.75",
            script_name="create-vm.sh",
            payload={"vm_name": "vm-test"},
            event_sink=event_sink,
        )

    monkeypatch.setattr(host_runner.subprocess, "Popen", fake_popen)

    thread = threading.Thread(target=run_script)
    thread.start()
    assert event_seen.wait(timeout=1)
    assert thread.is_alive()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert result["value"] == {"status": "success"}
    assert events == [("check_capacity", "检查宿主机实时容量")]


def test_host_script_uses_configured_ssh_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_command: list[str] = []

    def fake_run(command: list[str], *_args: object, **_kwargs: object) -> CompletedProcess[str]:
        captured_command.extend(command)
        return CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"status":"success"}',
            stderr="",
        )

    monkeypatch.setattr(host_runner, "_run_host_process", fake_run)
    monkeypatch.setattr(
        host_runner,
        "get_settings",
        lambda: SimpleNamespace(
            vm_host_script_timeout_seconds=900,
            vm_host_ssh_key_path="/etc/kronos/ssh/id_rsa",
        ),
    )

    host_runner.run_host_script(
        host_ip="172.168.131.75",
        script_name="create-vm.sh",
        payload={"vm_name": "vm-test"},
    )

    assert captured_command == [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-i",
        "/etc/kronos/ssh/id_rsa",
        "-o",
        "IdentitiesOnly=yes",
        "root@172.168.131.75",
        captured_command[-1],
    ]


def test_host_script_requires_ssh_key_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        host_runner,
        "get_settings",
        lambda: SimpleNamespace(
            vm_host_script_timeout_seconds=900,
            vm_host_ssh_key_path=None,
        ),
    )

    with pytest.raises(host_runner.HostScriptError) as exc_info:
        host_runner.run_host_script(
            host_ip="172.168.131.75",
            script_name="create-vm.sh",
            payload={"vm_name": "vm-test"},
        )

    assert exc_info.value.code == "vm_host_ssh_key_missing"
    assert str(exc_info.value) == "VM host SSH key path is not configured"


def test_host_script_missing_worker_command_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def fake_run(*_args: object, **_kwargs: object) -> CompletedProcess[str]:
        raise FileNotFoundError(2, "No such file or directory", "ssh")

    monkeypatch.setattr(host_runner, "_run_host_process", fake_run)

    with pytest.raises(host_runner.HostScriptError) as exc_info:
        host_runner.run_host_script(
            host_ip="172.168.131.75",
            script_name="create-vm.sh",
            payload={"vm_name": "vm-test"},
        )

    assert exc_info.value.code == "worker_dependency_missing"
    assert str(exc_info.value) == "worker command is missing: ssh"


def test_host_script_result_model_validates_success_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def fake_run(*_args: object, **_kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(
            args=["ssh"],
            returncode=0,
            stdout='{"status":"success"}',
            stderr="",
        )

    monkeypatch.setattr(host_runner, "_run_host_process", fake_run)

    with pytest.raises(host_runner.HostScriptError) as exc_info:
        host_runner.run_host_script(
            host_ip="172.168.131.75",
            script_name="create-vm.sh",
            payload={"vm_name": "vm-test"},
            result_model=VMHostCreateResult,
        )

    assert exc_info.value.code == "invalid_host_response"


# --- 自定义换内核（变体/URL）测试 -------------------------------------------


def _make_request_custom(
    reqid: str = "req-cust",
    *,
    kernel_variant: str | None = "26.09-with-kernel-6.18",
    kernel_rpm_url: str | None = None,
) -> SimpleNamespace:
    """换内核测试用的 VMRequest（带 kernel_variant / kernel_rpm_url）。"""
    return SimpleNamespace(
        id=reqid,
        os_version="openEuler-26.09-DevStation",
        dist="openEuler",
        image_round="rc3_openeuler-2026-08-28-04-39-54",
        arch="aarch64",
        kernel_variant=kernel_variant,
        kernel_rpm_url=kernel_rpm_url,
        requester_user_id="u1",
        task_id="t1",
    )


def _custom_ssh_fake(
    repoquery_stdout: str,
    uname_stdout: str,
) -> tuple:
    """换内核 SSH fake：repoquery 返回精确 NVR，uname 返回版本串，其余返回 0。

    返回 (fake, commands) 以便断言命令序列。
    """
    commands: list[str] = []

    def fake_ssh(*, host, username, password, command, **kw):  # noqa: ANN001
        commands.append(command)
        if "dnf repoquery" in command:
            return SimpleNamespace(returncode=0, stdout=repoquery_stdout, stderr="")
        if command == "uname -r":
            return SimpleNamespace(returncode=0, stdout=uname_stdout, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return fake_ssh, commands


def _fast_forward_reboot_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """快进 reboot 等待循环（time.monotonic 每次 +10s，sleep no-op），避免 120s 真实等待。"""
    tick = [0.0]
    monkeypatch.setattr(
        "time.monotonic", lambda: (tick.__setitem__(0, tick[0] + 10.0), tick[0])[1]
    )
    monkeypatch.setattr("time.sleep", lambda *_: None)


def test_apply_custom_kernel_variant_success(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    变体路径：推断 dailybuild repo + 写 [local-kernel] repo + repoquery 找精确 NVR
    + dnf install kernel-<NVR> + reboot + uname 匹配 → kernel_version 写真实值 + 事件。
    """
    from app.modules.vms.service import apply_custom_kernel

    # 固定 dailybuild root，使 baseurl 断言不依赖运行环境配置（get_settings 为单例）。
    monkeypatch.setattr(
        get_settings(), "vm_dailybuild_repo_root", "http://121.36.84.172/dailybuild"
    )

    write_calls: list[dict] = []

    def fake_write(*, host, username, password, path, content, **kw):  # noqa: ANN001
        write_calls.append({"path": path, "content": content})
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", fake_write)
    fake_ssh, commands = _custom_ssh_fake(
        repoquery_stdout="kernel-6.18.40-0.0.0.14.oe2609.aarch64\n",
        uname_stdout="6.18.40-0.0.0.14.oe2609.aarch64\n",
    )
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)
    _fast_forward_reboot_wait(monkeypatch)

    resource = _make_resource_64k()
    request = _make_request_custom()
    actor = SimpleNamespace(id="u1")

    apply_custom_kernel(db_session, request=request, resource=resource, actor=actor)

    # 1. repo 文件写了 [local-kernel]，baseurl 含推断的 dailybuild 路径
    assert write_calls, "should write [local-kernel] repo file"
    repo_content = write_calls[0]["content"]
    assert "[local-kernel]" in repo_content, repo_content
    expected_baseurl = (
        "http://121.36.84.172/dailybuild/EBS-openEuler-26.09-DevStation/"
        "rc3_openeuler-2026-08-28-04-39-54/26.09-with-kernel-6.18/everything/aarch64/"
    )
    assert expected_baseurl in repo_content, repo_content
    # 2. repoquery 找精确 NVR（含版本前缀 6.18）
    assert any("dnf repoquery" in c and "6.18" in c for c in commands), commands
    # 3. dnf install 精确 NVR（不含 arch 后缀）
    assert any(
        "dnf install" in c and "kernel-6.18.40-0.0.0.14.oe2609" in c for c in commands
    ), commands
    # 4. reboot
    assert any("reboot" in c for c in commands), commands
    # 5. uname -r 判定新内核生效
    assert any(c == "uname -r" for c in commands), commands
    # 6. kernel_version 写真实 uname 值
    assert resource.kernel_version == "6.18.40-0.0.0.14.oe2609.aarch64"
    # 7. kernel_custom_installed 事件（含来源变体 + uname 结果）
    events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req-cust",
                TaskEvent.phase == "kernel_custom_installed",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert "6.18.40-0.0.0.14.oe2609.aarch64" in events[0].message
    assert "26.09-with-kernel-6.18" in events[0].message


def test_apply_custom_kernel_url_success(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    URL 路径：从 RPM URL 推断同目录 repo baseurl + 从文件名解析 NVR + 写 repo +
    dnf install kernel-<NVR> + reboot + uname 匹配 → kernel_version + 事件（含 URL）。
    """

    url = (
        "http://121.36.84.172/dailybuild/EBS-openEuler-26.09-DevStation/"
        "rc3_openeuler-2026-08-28-04-39-54/26.09-with-kernel-6.18/everything/aarch64/"
        "Packages/kernel-6.18.40-0.0.0.14.oe2609.aarch64.rpm"
    )
    write_calls: list[dict] = []

    def fake_write(*, host, username, password, path, content, **kw):  # noqa: ANN001
        write_calls.append({"path": path, "content": content})
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", fake_write)
    # URL 路径 NVR 从文件名解析，不 repoquery
    fake_ssh, commands = _custom_ssh_fake(
        repoquery_stdout="",
        uname_stdout="6.18.40-0.0.0.14.oe2609.aarch64\n",
    )
    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)
    _fast_forward_reboot_wait(monkeypatch)

    resource = _make_resource_64k()
    request = _make_request_custom(kernel_variant=None, kernel_rpm_url=url)
    actor = SimpleNamespace(id="u1")

    apply_custom_kernel(db_session, request=request, resource=resource, actor=actor)

    # repo baseurl = URL 去掉 /Packages/kernel-*.rpm
    expected_baseurl = url.rsplit("/Packages/", 1)[0] + "/"
    assert write_calls, "should write [local-kernel] repo file"
    repo_content = write_calls[0]["content"]
    assert "[local-kernel]" in repo_content, repo_content
    assert expected_baseurl in repo_content, repo_content
    # URL 路径不 repoquery（NVR 从文件名解析）
    assert not any("dnf repoquery" in c for c in commands), commands
    # dnf install 精确 NVR
    assert any(
        "dnf install" in c and "kernel-6.18.40-0.0.0.14.oe2609" in c for c in commands
    ), commands
    assert any("reboot" in c for c in commands), commands
    assert any(c == "uname -r" for c in commands), commands
    assert resource.kernel_version == "6.18.40-0.0.0.14.oe2609.aarch64"
    events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req-cust",
                TaskEvent.phase == "kernel_custom_installed",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert url in events[0].message


def test_apply_custom_kernel_install_failed_raises(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dnf install 失败 → raise CustomKernelError(install_failed) + 事件，不 reboot。"""
    from app.modules.vms.service import CustomKernelError, apply_custom_kernel

    def fake_write(**kw):  # noqa: ANN001
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.write_remote_file", fake_write)
    commands: list[str] = []

    def fake_ssh(*, host, username, password, command, **kw):  # noqa: ANN001
        commands.append(command)
        if "dnf repoquery" in command:
            return SimpleNamespace(
                returncode=0, stdout="kernel-6.18.40-0.0.0.14.oe2609.aarch64\n", stderr=""
            )
        if "dnf install" in command:
            return SimpleNamespace(returncode=1, stdout="", stderr="boom no package")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.modules.test_management.remote.run_ssh_command", fake_ssh)
    _fast_forward_reboot_wait(monkeypatch)

    resource = _make_resource_64k()
    request = _make_request_custom()
    actor = SimpleNamespace(id="u1")

    with pytest.raises(CustomKernelError) as exc_info:
        apply_custom_kernel(db_session, request=request, resource=resource, actor=actor)
    assert exc_info.value.code == "kernel_custom_install_failed"
    assert resource.kernel_version is None
    # install 失败不应继续 reboot
    assert not any("reboot" in c for c in commands), commands
    events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "vm_request",
                TaskEvent.subject_id == "req-cust",
                TaskEvent.phase == "kernel_custom_install_failed",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1


def test_vm_request_create_validates_kernel_rpm_url() -> None:
    """kernel_rpm_url 必须是 None 或 http/https 且以 .rpm 结尾；kernel_variant 长度 ≤128。"""
    from pydantic import ValidationError

    base = dict(
        dist="openEuler",
        os_version="openEuler-26.09-DevStation",
        arch="aarch64",
        purpose="test",
        image_round="rc3",
        vcpu_count=2,
        memory_mb=4096,
    )
    # None 允许（不换内核）
    ok = VMRequestCreate(kernel_rpm_url=None, kernel_variant=None, **base)
    assert ok.kernel_rpm_url is None
    assert ok.kernel_variant is None
    # 合法 http + .rpm
    ok2 = VMRequestCreate(
        kernel_rpm_url="http://x/Packages/kernel-6.18.40.aarch64.rpm", **base
    )
    assert ok2.kernel_rpm_url is not None
    # 非 http/https → 拒绝
    with pytest.raises(ValidationError):
        VMRequestCreate(kernel_rpm_url="ftp://x/kernel.rpm", **base)
    # 不以 .rpm 结尾 → 拒绝
    with pytest.raises(ValidationError):
        VMRequestCreate(kernel_rpm_url="http://x/kernel.txt", **base)
    # kernel_variant 超长 → 拒绝
    with pytest.raises(ValidationError):
        VMRequestCreate(kernel_variant="x" * 129, **base)


def test_list_kernel_variants_parses_dailybuild_round_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """list_kernel_variants 解析 dailybuild 轮次目录 HTML，返回 *-with-kernel-* 变体 + 版本前缀。"""
    import io

    from app.modules.vms.image_discovery import list_kernel_variants

    html = (
        b'<a href="26.09-with-kernel-6.18/">26.09-with-kernel-6.18/</a>'
        b'<a href="26.09-with-kernel-6.6/">26.09-with-kernel-6.6/</a>'
        b'<a href="other-dir/">other-dir/</a>'
        b'<a href="../">../</a>'
    )
    monkeypatch.setattr(
        "app.modules.vms.image_discovery.urlopen",
        lambda url, timeout=10: io.BytesIO(html),
    )

    variants = list_kernel_variants(
        os_version="openEuler-26.09-DevStation", round="rc3_x", arch="aarch64"
    )

    assert [v.variant for v in variants] == [
        "26.09-with-kernel-6.18",
        "26.09-with-kernel-6.6",
    ]
    assert variants[0].kernel_version_prefix == "6.18"
    assert variants[1].kernel_version_prefix == "6.6"


def test_precheck_custom_kernel_variant_repo_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """变体路径 repo 不可达 → raise PrecheckCustomKernelError(repo_unreachable)。"""
    from app.modules.vms.image_discovery import (
        PrecheckCustomKernelError,
        precheck_custom_kernel,
    )

    def fake_urlopen(url, timeout=10):  # noqa: ANN001
        raise OSError("unreachable")

    monkeypatch.setattr("app.modules.vms.image_discovery.urlopen", fake_urlopen)

    payload = VMRequestCreate(
        dist="openEuler",
        os_version="openEuler-26.09-DevStation",
        arch="aarch64",
        image_round="rc3",
        purpose="t",
        vcpu_count=2,
        memory_mb=4096,
        kernel_variant="26.09-with-kernel-6.18",
    )
    with pytest.raises(PrecheckCustomKernelError) as exc_info:
        precheck_custom_kernel(payload)
    assert exc_info.value.code == "repo_unreachable"


def test_precheck_custom_kernel_variant_kernel_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """变体路径 repo 可达但 primary 无 kernel-<前缀>.* → raise kernel_not_found。"""
    import io

    import zstandard

    from app.modules.vms.image_discovery import (
        PrecheckCustomKernelError,
        precheck_custom_kernel,
    )

    primary_xml = b'<package><name>kernel</name><version ver="5.10.0" rel="x"/></package>'
    primary_zst = zstandard.ZstdCompressor().compress(primary_xml)
    repomd = (
        b'<?xml version="1.0"?><repomd><data type="primary">'
        b'<location href="repodata/abc-primary.xml.zst"/></data></repomd>'
    )

    def fake_urlopen(url, timeout=10):  # noqa: ANN001
        if url.endswith("repomd.xml"):
            return io.BytesIO(repomd)
        return io.BytesIO(primary_zst)

    monkeypatch.setattr("app.modules.vms.image_discovery.urlopen", fake_urlopen)

    payload = VMRequestCreate(
        dist="openEuler",
        os_version="openEuler-26.09-DevStation",
        arch="aarch64",
        image_round="rc3",
        purpose="t",
        vcpu_count=2,
        memory_mb=4096,
        kernel_variant="26.09-with-kernel-6.18",
    )
    with pytest.raises(PrecheckCustomKernelError) as exc_info:
        precheck_custom_kernel(payload)
    assert exc_info.value.code == "kernel_not_found"


def test_precheck_custom_kernel_variant_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """变体路径 repo 可达且 primary 有 kernel-6.18.* → 不 raise。"""
    import io

    import zstandard

    from app.modules.vms.image_discovery import precheck_custom_kernel

    primary_xml = (
        b'<package><name>kernel</name><arch>aarch64</arch>'
        b'<version epoch="0" ver="6.18.40" rel="0.0.0.14.oe2609"/></package>'
    )
    primary_zst = zstandard.ZstdCompressor().compress(primary_xml)
    repomd = (
        b'<?xml version="1.0"?><repomd><data type="primary">'
        b'<location href="repodata/abc-primary.xml.zst"/></data></repomd>'
    )

    def fake_urlopen(url, timeout=10):  # noqa: ANN001
        if url.endswith("repomd.xml"):
            return io.BytesIO(repomd)
        return io.BytesIO(primary_zst)

    monkeypatch.setattr("app.modules.vms.image_discovery.urlopen", fake_urlopen)

    payload = VMRequestCreate(
        dist="openEuler",
        os_version="openEuler-26.09-DevStation",
        arch="aarch64",
        image_round="rc3",
        purpose="t",
        vcpu_count=2,
        memory_mb=4096,
        kernel_variant="26.09-with-kernel-6.18",
    )
    precheck_custom_kernel(payload)  # 不 raise


def test_precheck_custom_kernel_handles_streaming_zst_without_content_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实 dailybuild 的 primary.xml.zst 流式压缩（无 content size），decompressobj 仍能解。"""
    import io

    import zstandard

    from app.modules.vms.image_discovery import precheck_custom_kernel

    primary_xml = (
        b'<package><name>kernel</name><arch>aarch64</arch>'
        b'<version epoch="0" ver="6.18.40" rel="0.0.0.14.oe2609"/></package>'
    )
    primary_zst = zstandard.ZstdCompressor(write_content_size=False).compress(
        primary_xml
    )
    repomd = (
        b'<?xml version="1.0"?><repomd><data type="primary">'
        b'<location href="repodata/abc-primary.xml.zst"/></data></repomd>'
    )

    def fake_urlopen(url, timeout=10):  # noqa: ANN001
        if url.endswith("repomd.xml"):
            return io.BytesIO(repomd)
        return io.BytesIO(primary_zst)

    monkeypatch.setattr("app.modules.vms.image_discovery.urlopen", fake_urlopen)

    payload = VMRequestCreate(
        dist="openEuler",
        os_version="openEuler-26.09-DevStation",
        arch="aarch64",
        image_round="rc3",
        purpose="t",
        vcpu_count=2,
        memory_mb=4096,
        kernel_variant="26.09-with-kernel-6.18",
    )
    precheck_custom_kernel(payload)  # 不 raise

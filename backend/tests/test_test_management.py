# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import threading
import time
from collections.abc import Generator
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from billiard.exceptions import SoftTimeLimitExceeded
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.resources.models import Resource, ResourceType
from app.modules.tasks import recovery as task_recovery
from app.modules.tasks.models import TaskEvent
from app.modules.test_management import execution as test_execution
from app.modules.test_management import models as test_management_models
from app.modules.test_management import remote as test_management_remote
from app.modules.test_management import router as test_management_router
from app.modules.test_management import service as test_management_service
from app.modules.test_management import tasks as test_management_tasks
from app.modules.test_management.envs import vm as vm_env
from app.modules.test_management.errors import TestJobExecutionError as JobExecutionError
from app.modules.test_management.frameworks import mugen_runner
from app.modules.test_management.frameworks.mugen import parse_suite_documents
from app.modules.test_management.remote import RemoteCommandError, RemoteCommandResult
from app.modules.test_management.schemas import MugenCaseSyncRequest
from app.modules.test_management.service import sync_mugen_cases
from app.modules.users.models import UserRole
from app.modules.users.service import create_user
from app.modules.vms.image_discovery import ImageDiscoveryError, VMImage


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


def seed_mugen_cases(db_session: Session) -> None:
    sync_mugen_cases(
        db_session,
        MugenCaseSyncRequest(
            commit_sha="abc123",
            suites={
                "suite-a": {
                    "machine type": "vm",
                    "machine num": 1,
                    "cases": [
                        {"name": "case-a1"},
                        {"name": "case-a2"},
                    ],
                },
                "suite-b": {
                    "cases": [
                        {
                            "name": "case-b1",
                            "machine type": "vm",
                            "machine num": 2,
                            "add network interface": True,
                        },
                    ],
                },
            },
        ),
    )
    db_session.commit()


def test_vm_env_rejects_soft_deleted_resource(db_session: Session) -> None:
    resource = Resource(
        resource_code="deleted-vm",
        resource_type=ResourceType.VIRTUAL.value,
        primary_ip="172.168.131.200",
        ssh_username="root",
        ssh_password_ciphertext="ciphertext",
        deleted_at=datetime.now(UTC),
    )
    db_session.add(resource)
    db_session.commit()
    node = test_management_models.TestEnvNode(
        env_set_id="env-set",
        node_index=1,
        role="control",
        resource_id=resource.id,
    )

    with pytest.raises(JobExecutionError, match="unavailable"):
        vm_env.node_resource(db_session, node)


def seed_pending_test_job(
    db_session: Session,
    *,
    creator_user_id: str,
    created_at: datetime | None = None,
) -> test_management_models.TestJob:
    job = test_management_models.TestJob(
        creator_user_id=creator_user_id,
        name="execution test",
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        created_at=created_at or test_management_models.utc_now(),
    )
    job.env_sets.append(test_management_models.TestEnvSet(set_index=1, node_num=1))
    db_session.add(job)
    db_session.commit()
    return job


def stub_test_job_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_queue_test_job(db: Session, job: test_management_models.TestJob):
        job.task_id = "test-task-id"
        db.flush()
        return job

    monkeypatch.setattr(
        "app.modules.test_management.router.queue_test_job",
        fake_queue_test_job,
    )


def stub_vm_images(monkeypatch: pytest.MonkeyPatch) -> None:
    images = [
        VMImage(
            dist="openEuler",
            os_version="openEuler-24.03-LTS-SP4",
            image_round="round-9",
            arch="aarch64",
            url="https://example.invalid/openEuler.qcow2",
        )
    ]
    monkeypatch.setattr(
        "app.modules.test_management.service.discover_images",
        lambda **_: images,
    )
    monkeypatch.setattr(
        "app.modules.test_management.templates.discover_images",
        lambda **_: images,
    )


def template_payload(name: str = "smoke.template") -> dict[str, object]:
    return {
        "name": name,
        "framework": "mugen",
        "env_type": "vm",
        "dist": "openEuler",
        "os_version": "openEuler-24.03-LTS-SP4",
        "image_round": "round-9",
        "arch": "aarch64",
        "env_set_num": 2,
        "keep_failed_env": True,
        "pre_env_script": "echo prepare",
        "post_env_script": "echo cleanup",
        "cases": [{"suite_name": "suite-a"}],
    }


def test_mugen_suite_parser_normalizes_resource_constraints() -> None:
    cases = parse_suite_documents(
        {
            "suite-net": {
                "machine type": "kvm",
                "machine num": "2",
                "add disk": "true",
                "cases": [
                    {"name": "case-one"},
                    {
                        "name": "case-two",
                        "machine num": "1",
                        "add network interface": "yes",
                    },
                ],
            }
        }
    )

    assert [(case.case_name, case.env_type, case.node_num) for case in cases] == [
        ("case-one", "vm", 2),
        ("case-two", "vm", 1),
    ]
    assert cases[0].add_disk_num == 1
    assert cases[1].add_nic_num == 1


def test_user_can_list_mugen_cases(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    seed_mugen_cases(db_session)

    response = client.get(
        "/api/v1/test-cases?suite=suite-a&case=a2&env_type=vm",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [case["case_name"] for case in body["items"]] == ["case-a2"]


def test_user_can_list_non_vm_mugen_cases(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    sync_mugen_cases(
        db_session,
        MugenCaseSyncRequest(
            commit_sha="abc123",
            suites={
                "suite-physical": {
                    "machine type": "physical",
                    "cases": [{"name": "case-physical"}],
                },
                "suite-unknown": {
                    "machine type": "container",
                    "cases": [{"name": "case-unknown"}],
                },
            },
        ),
    )
    db_session.commit()

    response = client.get(
        "/api/v1/test-cases?env_type=physical",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert [
        (case["case_name"], case["env_type"]) for case in response.json()["items"]
    ] == [("case-physical", "physical")]

    all_response = client.get(
        "/api/v1/test-cases",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert all_response.status_code == 200
    assert {case["env_type"] for case in all_response.json()["items"]} == {
        "physical",
        "unknown",
    }


def test_create_test_job_expands_suite_bundles_to_env_sets(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_test_job_queue(monkeypatch)
    stub_vm_images(monkeypatch)
    token = login_as(client, db_session, username="tse1", role=UserRole.TSE)
    seed_mugen_cases(db_session)

    response = client.post(
        "/api/v1/test-jobs",
        json={
            "name": "mugen smoke",
            "framework": "mugen",
            "env_type": "vm",
            "dist": "openEuler",
            "os_version": "openEuler-24.03-LTS-SP4",
            "image_round": "round-9",
            "arch": "aarch64",
            "env_set_num": 4,
            "keep_failed_env": True,
            "pre_env_script": " echo prepare ",
            "post_env_script": " echo cleanup ",
            "cases": [
                {"suite_name": "suite-a"},
                {"suite_name": "suite-b", "case_names": ["case-b1"]},
            ],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "create-test-job",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["mugen_commit_sha"] == "abc123"
    assert body["task_id"] == "test-task-id"
    assert body["env_set_num"] == 2
    assert body["pre_env_script"] == "echo prepare"
    assert body["post_env_script"] == "echo cleanup"
    assert [(env["set_index"], env["node_num"]) for env in body["env_sets"]] == [
        (1, 1),
        (2, 2),
    ]
    assert [node["role"] for node in body["env_sets"][1]["nodes"]] == ["control", "peer"]
    assert sorted(run["case_name"] for run in body["case_runs"]) == [
        "case-a1",
        "case-a2",
        "case-b1",
    ]

    stored_env_sets = list(db_session.execute(select(test_management_models.TestEnvSet)).scalars())
    stored_nodes = list(db_session.execute(select(test_management_models.TestEnvNode)).scalars())
    stored_runs = list(db_session.execute(select(test_management_models.TestCaseRun)).scalars())
    assert len(stored_env_sets) == 2
    assert len(stored_nodes) == 3
    assert len(stored_runs) == 3


def test_create_test_job_rejects_physical_cases(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    sync_mugen_cases(
        db_session,
        MugenCaseSyncRequest(
            commit_sha="abc123",
            suites={
                "suite-physical": {
                    "cases": [{"name": "case-p1", "machine type": "physical"}],
                }
            },
        ),
    )
    db_session.commit()

    response = client.post(
        "/api/v1/test-jobs",
        json={
            "name": "physical case",
            "os_version": "openEuler-24.03-LTS-SP4",
            "image_round": "round-9",
            "arch": "aarch64",
            "cases": [{"suite_name": "suite-physical"}],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "reject-physical",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "请求参数错误"


def test_create_test_job_rejects_image_missing_from_index(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    seed_mugen_cases(db_session)
    monkeypatch.setattr(
        "app.modules.test_management.service.discover_images",
        lambda **_: [],
    )

    response = client.post(
        "/api/v1/test-jobs",
        json={
            "name": "missing image",
            "os_version": "openEuler-24.03-LTS-SP4",
            "image_round": "round-9",
            "arch": "aarch64",
            "cases": [{"suite_name": "suite-a"}],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "reject-missing-image",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "所选镜像不在当前镜像索引中"


def test_create_test_job_force_refreshes_image_index(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    seed_mugen_cases(db_session)
    calls: list[dict[str, object]] = []

    def discover(**kwargs: object) -> list[VMImage]:
        calls.append(kwargs)
        return [
            VMImage(
                dist="openEuler",
                os_version="openEuler-24.03-LTS-SP4",
                image_round="round-9",
                arch="aarch64",
                url="https://example.invalid/openEuler.qcow2",
            )
        ]

    monkeypatch.setattr(
        "app.modules.test_management.service.discover_images",
        discover,
    )
    stub_test_job_queue(monkeypatch)

    response = client.post(
        "/api/v1/test-jobs",
        json={
            "name": "fresh image index",
            "os_version": "openEuler-24.03-LTS-SP4",
            "image_round": "round-9",
            "arch": "aarch64",
            "cases": [{"suite_name": "suite-a"}],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "fresh-image-index",
        },
    )

    assert response.status_code == 201
    assert calls == [{"dist": "openEuler", "force_refresh": True}]


def test_create_test_job_rejects_node_num_greater_than_two(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    sync_mugen_cases(
        db_session,
        MugenCaseSyncRequest(
            commit_sha="abc123",
            suites={
                "suite-large": {
                    "cases": [{"name": "case-large", "machine num": 3}],
                }
            },
        ),
    )
    db_session.commit()

    response = client.post(
        "/api/v1/test-jobs",
        json={
            "name": "large case",
            "os_version": "openEuler-24.03-LTS-SP4",
            "image_round": "round-9",
            "arch": "aarch64",
            "cases": [{"suite_name": "suite-large"}],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "reject-large",
        },
    )

    assert response.status_code == 400
    assert "需要超过 2 个节点" in response.json()["error"]["message"]


def test_create_test_job_rejects_empty_mugen_index(
    client: TestClient,
    db_session: Session,
) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)

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
            "Idempotency-Key": "reject-empty",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Mugen 用例索引为空"


def test_user_can_create_and_read_shared_test_job_template(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_vm_images(monkeypatch)
    creator_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    viewer_token = login_as(client, db_session, username="tse1", role=UserRole.TSE)
    seed_mugen_cases(db_session)

    response = client.post(
        "/api/v1/test-job-templates",
        json=template_payload(),
        headers={"Authorization": f"Bearer {creator_token}"},
    )

    assert response.status_code == 201
    created = response.json()
    assert isinstance(created["id"], int)
    assert created["is_available"] is True
    assert created["can_manage"] is True
    assert created["cases"] == [
        {"suite_name": "suite-a", "case_names": ["case-a1", "case-a2"]}
    ]

    list_response = client.get(
        "/api/v1/test-job-templates",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["name"] == "smoke.template"
    assert list_response.json()["items"][0]["can_manage"] is False

    audit = db_session.execute(
        select(AuditLog).where(AuditLog.action == "test_job_template.create")
    ).scalar_one()
    assert audit.detail == {"template_id": created["id"], "name": "smoke.template"}
    assert "script" not in str(audit.detail).lower()


def test_template_name_is_case_insensitively_unique(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_vm_images(monkeypatch)
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    seed_mugen_cases(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/api/v1/test-job-templates",
        json=template_payload("Smoke.Template"),
        headers=headers,
    )
    duplicate = client.post(
        "/api/v1/test-job-templates",
        json=template_payload("smoke.template"),
        headers=headers,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_only_creator_or_admin_can_update_and_delete_template(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_vm_images(monkeypatch)
    creator_token = login_as(client, db_session, username="te1", role=UserRole.TE)
    other_token = login_as(client, db_session, username="te2", role=UserRole.TE)
    admin_token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    seed_mugen_cases(db_session)
    created = client.post(
        "/api/v1/test-job-templates",
        json=template_payload(),
        headers={"Authorization": f"Bearer {creator_token}"},
    ).json()
    path = f"/api/v1/test-job-templates/{created['id']}"

    forbidden = client.patch(
        path,
        json={"env_set_num": 3},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    updated = client.patch(
        path,
        json={"env_set_num": 3, "pre_env_script": None},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert forbidden.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["env_set_num"] == 3
    assert updated.json()["pre_env_script"] is None
    assert updated.json()["creator_username"] == "te1"

    deleted = client.delete(path, headers={"Authorization": f"Bearer {creator_token}"})
    missing = client.delete(path, headers={"Authorization": f"Bearer {creator_token}"})
    assert deleted.status_code == 204
    assert missing.status_code == 404

    update_audit = db_session.execute(
        select(AuditLog).where(AuditLog.action == "test_job_template.update")
    ).scalar_one()
    assert update_audit.detail["changed_fields"] == ["env_set_num", "pre_env_script"]
    assert "echo prepare" not in str(update_audit.detail)


def test_template_remains_visible_when_image_index_is_unavailable(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_vm_images(monkeypatch)
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    seed_mugen_cases(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/test-job-templates",
        json=template_payload(),
        headers=headers,
    )
    assert created.status_code == 201

    def fail_discovery(**_: object) -> list[VMImage]:
        raise ImageDiscoveryError("offline")

    monkeypatch.setattr(
        "app.modules.test_management.templates.discover_images",
        fail_discovery,
    )
    monkeypatch.setattr(
        "app.modules.test_management.service.discover_images",
        fail_discovery,
    )
    response = client.get("/api/v1/test-job-templates", headers=headers)

    assert response.status_code == 200
    assert response.json()["items"][0]["is_available"] is False
    assert response.json()["items"][0]["unavailable_reason"] == "无法读取镜像索引"

    path = f"/api/v1/test-job-templates/{created.json()['id']}"
    metadata_update = client.patch(
        path,
        json={"name": "renamed.template", "pre_env_script": "echo updated"},
        headers=headers,
    )
    config_update = client.patch(
        path,
        json={"arch": "x86_64"},
        headers=headers,
    )

    assert metadata_update.status_code == 200
    assert metadata_update.json()["name"] == "renamed.template"
    assert metadata_update.json()["is_available"] is False
    assert config_update.status_code == 503


def test_sync_mugen_cases_replaces_previous_index(db_session: Session) -> None:
    seed_mugen_cases(db_session)
    sync_mugen_cases(
        db_session,
        MugenCaseSyncRequest(
            commit_sha="def456",
            suites={"suite-c": {"cases": [{"name": "case-c1"}]}},
        ),
    )
    db_session.commit()

    cases = list(db_session.execute(select(test_management_models.MugenCase)).scalars())
    assert [(case.suite_name, case.case_name, case.commit_sha) for case in cases] == [
        ("suite-c", "case-c1", "def456")
    ]


def test_sync_mugen_cases_stores_dangerous_scan_reasons(db_session: Session) -> None:
    sync_mugen_cases(
        db_session,
        MugenCaseSyncRequest(
            commit_sha="sha-danger",
            suites={
                "systemd": {
                    "cases": [
                        {"name": "oe_test_service_initrd-cleanup"},
                        {"name": "oe_test_service_systemd-journald"},
                    ]
                }
            },
        ),
        dangerous_reasons={
            ("systemd", "oe_test_service_initrd-cleanup"): (
                "脚本伪造 initrd 环境(/etc/initrd-release)"
            ),
        },
    )
    db_session.commit()

    cases = {
        case.case_name: case
        for case in db_session.execute(select(test_management_models.MugenCase)).scalars()
    }
    flagged = cases["oe_test_service_initrd-cleanup"]
    assert flagged.dangerous is True
    assert flagged.dangerous_reason == "脚本伪造 initrd 环境(/etc/initrd-release)"
    safe = cases["oe_test_service_systemd-journald"]
    assert safe.dangerous is False
    assert safe.dangerous_reason is None


def test_test_job_list_lazily_marks_expired_running_job_error(
    client: TestClient,
    db_session: Session,
) -> None:
    actor = create_user(
        db_session,
        username="jobreader",
        password="test-pass",
        role=UserRole.TE,
        display_name="jobreader",
    )
    old_time = datetime.now(UTC) - timedelta(hours=16)
    job = test_management_models.TestJob(
        id=10050,
        creator_user_id=actor.id,
        name="stale-job",
        status=test_management_models.TestJobStatus.RUNNING.value,
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_failed_env=False,
        task_id="stale-job-task",
        created_at=old_time,
        updated_at=old_time,
    )
    db_session.add(job)
    db_session.add(
        TaskEvent(
            task_type="test_job",
            subject_type="test_job",
            subject_id=str(job.id),
            celery_task_id=job.task_id,
            phase="started",
            message="worker 已领取测试任务",
            created_at=old_time,
        )
    )
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "jobreader", "password": "test-pass"},
    )

    response = client.get(
        "/api/v1/test-jobs",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "error"
    assert response.json()["items"][0]["error_code"] == "task_timeout"


def test_mugen_sync_events_lazily_fail_expired_sync_and_release_matching_lock(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = login_as(client, db_session, username="syncadmin", role=UserRole.ADMIN)
    old_time = datetime.now(UTC) - timedelta(minutes=31)
    db_session.add(
        TaskEvent(
            task_type="mugen_sync",
            subject_type="mugen_sync",
            subject_id="mugen",
            celery_task_id="stale-sync-task",
            phase="started",
            message="开始同步 Mugen 用例索引",
            created_at=old_time,
        )
    )
    db_session.commit()
    released: list[str] = []
    monkeypatch.setattr(
        task_recovery,
        "_release_mugen_sync_lock",
        released.append,
    )

    response = client.get(
        "/api/v1/test-cases/sync/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()[-1]["error_code"] == "mugen_sync_failed"
    assert released == ["stale-sync-task"]


def test_destroy_env_node_vm_rejects_failed_destroy(monkeypatch: pytest.MonkeyPatch) -> None:
    resource = SimpleNamespace(id="resource-id")
    lease = SimpleNamespace(id="lease-id")
    node = SimpleNamespace(resource_id=resource.id, node_index=0, status="ready")
    job = SimpleNamespace(
        id="job-id",
        task_id="task-id",
        created_at=test_management_models.utc_now(),
    )
    actor = SimpleNamespace(id="user-id")

    class FakeSession:
        @staticmethod
        def get(_model: object, _id: str) -> object:
            return resource

        @staticmethod
        def commit() -> None:
            pass

        @staticmethod
        def expire_all() -> None:
            pass

    monkeypatch.setattr(vm_env, "get_resource_active_lease", lambda *_: lease)
    monkeypatch.setattr(vm_env, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(vm_env, "process_vm_destroy", lambda *_, **__: False)

    with pytest.raises(JobExecutionError, match="VM destroy failed"):
        vm_env.destroy_env_node_vm(
            FakeSession(),  # type: ignore[arg-type]
            job=job,  # type: ignore[arg-type]
            node=node,  # type: ignore[arg-type]
            actor=actor,  # type: ignore[arg-type]
        )

    assert node.status == "ready"


def test_cleanup_env_vms_continues_after_one_node_destroy_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = SimpleNamespace(node_index=0, status="ready")
    second = SimpleNamespace(node_index=1, status="ready")
    env_set = SimpleNamespace(set_index=1, status="running", nodes=[first, second])
    calls: list[int] = []

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

        @staticmethod
        def rollback() -> None:
            pass

    def fake_destroy(_db: object, *, node: object, **_: object) -> None:
        calls.append(node.node_index)  # type: ignore[attr-defined]
        if node is first:
            raise RuntimeError("first failed")
        node.status = test_management_models.TestEnvNodeStatus.DESTROYED.value  # type: ignore[attr-defined]

    monkeypatch.setattr(vm_env, "destroy_env_node_vm", fake_destroy)

    with pytest.raises(JobExecutionError, match="node 0: first failed"):
        vm_env.cleanup_env_vms(
            FakeSession(),  # type: ignore[arg-type]
            job=SimpleNamespace(),  # type: ignore[arg-type]
            env_set=env_set,  # type: ignore[arg-type]
            actor=SimpleNamespace(),  # type: ignore[arg-type]
            preserve=False,
        )

    assert calls == [0, 1]
    assert second.status == test_management_models.TestEnvNodeStatus.DESTROYED.value
    assert env_set.status == test_management_models.TestEnvSetStatus.ERROR.value


def test_process_test_job_marks_expired_job_as_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = create_user(
        db_session,
        username="expiredjob",
        password="test-pass",
        role=UserRole.TE,
    )
    job = seed_pending_test_job(
        db_session,
        creator_user_id=actor.id,
        created_at=test_management_models.utc_now() - timedelta(hours=16),
    )
    cleanup_calls: list[str] = []

    monkeypatch.setattr(test_execution, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        test_execution,
        "execute_env_set",
        lambda *_, **__: pytest.fail("expired job must not execute an env set"),
    )
    monkeypatch.setattr(
        test_execution,
        "cleanup_env_vms",
        lambda _db, *, env_set, **__: cleanup_calls.append(env_set.id),
    )

    test_execution.process_test_job(job.id)

    db_session.refresh(job)
    assert job.status == test_management_models.TestJobStatus.ERROR.value
    assert job.error_code == "task_timeout"
    assert cleanup_calls == [job.env_sets[0].id]


def test_run_test_job_task_has_fifteen_hour_soft_time_limit() -> None:
    assert test_management_tasks.run_test_job_task.soft_time_limit == 15 * 60 * 60


def test_run_test_job_task_ignores_legacy_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed: list[int] = []
    monkeypatch.setattr(test_management_tasks, "process_test_job", processed.append)

    test_management_tasks.run_test_job_task.run("legacy-uuid")
    test_management_tasks.run_test_job_task.run("10000")

    assert processed == [10000]


def test_process_test_job_maps_soft_time_limit_to_task_timeout(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = create_user(
        db_session,
        username="softtimeoutjob",
        password="test-pass",
        role=UserRole.TE,
    )
    job = seed_pending_test_job(db_session, creator_user_id=actor.id)
    cleanup_calls: list[str] = []

    monkeypatch.setattr(test_execution, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        test_execution,
        "execute_env_set",
        lambda *_, **__: (_ for _ in ()).throw(SoftTimeLimitExceeded()),
    )
    monkeypatch.setattr(
        test_execution,
        "cleanup_env_vms",
        lambda _db, *, env_set, **__: cleanup_calls.append(env_set.id),
    )

    test_execution.process_test_job(job.id)

    db_session.refresh(job)
    assert job.status == test_management_models.TestJobStatus.ERROR.value
    assert job.error_code == "task_timeout"
    assert cleanup_calls == [job.env_sets[0].id]


def test_process_test_job_records_unexpected_execution_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = create_user(
        db_session,
        username="brokenjob",
        password="test-pass",
        role=UserRole.TE,
    )
    job = seed_pending_test_job(db_session, creator_user_id=actor.id)
    cleanup_calls: list[str] = []

    monkeypatch.setattr(test_execution, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        test_execution,
        "execute_env_set",
        lambda *_, **__: (_ for _ in ()).throw(RuntimeError("unexpected failure")),
    )
    monkeypatch.setattr(
        test_execution,
        "cleanup_env_vms",
        lambda _db, *, env_set, **__: cleanup_calls.append(env_set.id),
    )

    test_execution.process_test_job(job.id)

    db_session.refresh(job)
    assert job.status == test_management_models.TestJobStatus.ERROR.value
    assert job.error_code == "unexpected_execution_error"
    assert "unexpected failure" in (job.error_message or "")
    assert cleanup_calls == [job.env_sets[0].id]


def test_failed_job_cleanup_keeps_previously_preserved_failed_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_env = SimpleNamespace(id="failed", set_index=1, status="failed")
    broken_env = SimpleNamespace(id="broken", set_index=2, status="error")
    job = SimpleNamespace(keep_failed_env=True, keep_env=False, env_sets=[failed_env, broken_env])
    cleaned: list[str] = []

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

        @staticmethod
        def rollback() -> None:
            pass

    monkeypatch.setattr(
        test_execution,
        "cleanup_env_vms",
        lambda _db, *, env_set, **__: cleaned.append(env_set.id),
    )

    test_execution.cleanup_failed_job_envs(
        FakeSession(),  # type: ignore[arg-type]
        job=job,  # type: ignore[arg-type]
        actor=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert cleaned == ["broken"]
    assert failed_env.status == test_management_models.TestEnvSetStatus.FAILED.value


def test_run_case_treats_ssh_failure_as_task_error(monkeypatch: pytest.MonkeyPatch) -> None:
    case_run = SimpleNamespace(
        suite_name="suite-a",
        case_name="case-a1",
        env_set_id=None,
        status="pending",
        exit_code=None,
        stdout_summary=None,
        stderr_summary=None,
        started_at=None,
        completed_at=None,
    )
    job = SimpleNamespace(
        id="job-id",
        task_id="task-id",
        created_at=test_management_models.utc_now(),
    )
    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(
            returncode=255,
            stdout="",
            stderr="connection lost",
        ),
    )

    with pytest.raises(RemoteCommandError, match="connection lost"):
        mugen_runner.run_case(
            FakeSession(),  # type: ignore[arg-type]
            job=job,  # type: ignore[arg-type]
            control=control,  # type: ignore[arg-type]
            case_run=case_run,  # type: ignore[arg-type]
        )

    assert case_run.status == test_management_models.TestCaseRunStatus.ERROR.value


def test_run_case_marks_local_ssh_error_as_case_error(monkeypatch: pytest.MonkeyPatch) -> None:
    case_run = SimpleNamespace(
        suite_name="suite-a",
        case_name="case-a1",
        env_set_id=None,
        status="pending",
        exit_code=None,
        stdout_summary=None,
        stderr_summary=None,
        started_at=None,
        completed_at=None,
    )
    events: list[str] = []

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(
        mugen_runner,
        "record_test_job_event",
        lambda *_, phase, **__: events.append(phase),
    )
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: (_ for _ in ()).throw(RemoteCommandError("sshpass missing")),
    )

    with pytest.raises(RemoteCommandError, match="sshpass missing"):
        mugen_runner.run_case(
            FakeSession(),  # type: ignore[arg-type]
            job=SimpleNamespace(
                id="job-id",
                task_id="task-id",
                created_at=test_management_models.utc_now(),
            ),  # type: ignore[arg-type]
            control=SimpleNamespace(ip="192.0.2.10"),  # type: ignore[arg-type]
            case_run=case_run,  # type: ignore[arg-type]
        )

    assert case_run.status == test_management_models.TestCaseRunStatus.ERROR.value
    assert case_run.completed_at is not None
    assert "case_error" in events


def test_run_case_caps_command_timeout_to_remaining_job_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_run = SimpleNamespace(
        suite_name="suite-a",
        case_name="case-a1",
        env_set_id=None,
        status="pending",
        exit_code=None,
        stdout_summary=None,
        stderr_summary=None,
        started_at=None,
        completed_at=None,
    )
    timeouts: list[int] = []

    class FakeDetector:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        @staticmethod
        def start() -> None:
            pass

        @staticmethod
        def stop() -> None:
            pass

        @staticmethod
        def is_hung() -> bool:
            return False

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(mugen_runner, "HangDetector", FakeDetector)
    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "remaining_test_job_seconds", lambda *_, **__: 7)
    call_count = {"n": 0}

    def _fake_run_control(*, timeout_seconds: int, **_: object) -> RemoteCommandResult:
        call_count["n"] += 1
        if call_count["n"] == 1:
            timeouts.append(timeout_seconds)
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mugen_runner, "run_control_command", _fake_run_control)

    mugen_runner.run_case(
        FakeSession(),  # type: ignore[arg-type]
        job=SimpleNamespace(),  # type: ignore[arg-type]
        control=SimpleNamespace(ip="192.0.2.10"),  # type: ignore[arg-type]
        case_run=case_run,  # type: ignore[arg-type]
    )

    assert timeouts == [7]


def test_run_case_marks_expired_job_as_case_error(monkeypatch: pytest.MonkeyPatch) -> None:
    case_run = SimpleNamespace(
        suite_name="suite-a",
        case_name="case-a1",
        env_set_id=None,
        status="pending",
        exit_code=None,
        stdout_summary=None,
        stderr_summary=None,
        started_at=None,
        completed_at=None,
    )

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "remaining_test_job_seconds", lambda *_, **__: 0)

    with pytest.raises(JobExecutionError) as exc_info:
        mugen_runner.run_case(
            FakeSession(),  # type: ignore[arg-type]
            job=SimpleNamespace(),  # type: ignore[arg-type]
            control=SimpleNamespace(ip="192.0.2.10"),  # type: ignore[arg-type]
            case_run=case_run,  # type: ignore[arg-type]
        )

    assert exc_info.value.code == "task_timeout"
    assert case_run.status == test_management_models.TestCaseRunStatus.ERROR.value


def test_run_case_maps_deadline_limited_command_timeout_to_task_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_run = SimpleNamespace(
        suite_name="suite-a",
        case_name="case-a1",
        env_set_id=None,
        status="pending",
        exit_code=None,
        stdout_summary=None,
        stderr_summary=None,
        started_at=None,
        completed_at=None,
    )

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *_, **__: None)
    monkeypatch.setattr(mugen_runner, "remaining_test_job_seconds", lambda *_, **__: 7)
    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(
            returncode=None,
            stdout="",
            stderr="",
            timed_out=True,
        ),
    )

    with pytest.raises(JobExecutionError) as exc_info:
        mugen_runner.run_case(
            FakeSession(),  # type: ignore[arg-type]
            job=SimpleNamespace(),  # type: ignore[arg-type]
            control=SimpleNamespace(ip="192.0.2.10"),  # type: ignore[arg-type]
            case_run=case_run,  # type: ignore[arg-type]
        )

    assert exc_info.value.code == "task_timeout"
    assert case_run.status == test_management_models.TestCaseRunStatus.ERROR.value


def test_ssh_alive_skips_host_key_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """心跳探活不校验 host key：测试机每轮 PXE 重装都会轮换 host key，
    known_hosts 里的旧 key 会让 accept-new 在 preauth 阶段秒断，
    心跳 3 连失败误判 vm_hang（prod 2026-09-09 实锤）。
    """
    from app.modules.test_management.frameworks.mugen_runner import _ssh_alive

    captured: dict[str, object] = {}

    def fake_run_ssh_command(**kwargs: object) -> RemoteCommandResult:
        captured.update(kwargs)
        return RemoteCommandResult(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(mugen_runner, "run_ssh_command", fake_run_ssh_command)

    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")

    assert _ssh_alive(control) is True  # type: ignore[arg-type]
    assert captured["options"].verify_host_key is False


def test_wait_for_ssh_ready_retries_until_login_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = iter(
        [
            RemoteCommandResult(returncode=255, stdout="", stderr="not ready"),
            RemoteCommandResult(returncode=0, stdout="", stderr=""),
        ]
    )
    sleeps: list[float] = []
    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")

    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **_: next(results))
    monkeypatch.setattr(mugen_runner.time, "sleep", sleeps.append)
    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *a, **kw: None)

    mugen_runner.wait_for_ssh_ready(
        db=None,  # type: ignore[arg-type]
        node=control,  # type: ignore[arg-type]
        job=SimpleNamespace(created_at=test_management_models.utc_now()),  # type: ignore[arg-type]
        timeout_seconds=60,
        retry_interval_seconds=10,
    )

    assert sleeps == [10]


def test_wait_for_ssh_ready_raises_job_cancelled_when_event_pre_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """cancel_event 进入前已 set：立即抛 job_cancelled，不发命令也不 sleep。"""
    cancel_event = threading.Event()
    cancel_event.set()
    sleeps: list[float] = []
    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")
    calls: list[dict] = []

    def _boom(**kwargs: object) -> RemoteCommandResult:
        calls.append(kwargs)
        raise AssertionError("run_control_command must not be called after cancel")

    monkeypatch.setattr(mugen_runner, "run_control_command", _boom)
    monkeypatch.setattr(mugen_runner.time, "sleep", sleeps.append)
    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *a, **kw: None)

    with pytest.raises(JobExecutionError) as exc_info:
        mugen_runner.wait_for_ssh_ready(
            db=None,  # type: ignore[arg-type]
            node=control,  # type: ignore[arg-type]
            job=SimpleNamespace(created_at=test_management_models.utc_now()),  # type: ignore[arg-type]
            timeout_seconds=60,
            retry_interval_seconds=10,
            cancel_event=cancel_event,
        )

    assert exc_info.value.code == "job_cancelled"
    assert sleeps == []
    assert calls == []


def test_wait_for_ssh_ready_raises_job_cancelled_when_result_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_control_command 因 cancel_event 返回 cancelled=True：
    wait_for_ssh_ready 立即抛 job_cancelled 且不再 sleep(避免忙循环)。
    """
    cancel_event = threading.Event()
    sleeps: list[float] = []
    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")

    def _fake_run_control(**kwargs: object) -> RemoteCommandResult:
        # 模拟本地 run_process 因 cancel_event 主动 kill:cancelled=True,timed_out=False
        cancel_event.set()
        return RemoteCommandResult(
            returncode=None, stdout="", stderr="", cancelled=True
        )

    monkeypatch.setattr(mugen_runner, "run_control_command", _fake_run_control)
    monkeypatch.setattr(mugen_runner.time, "sleep", sleeps.append)
    monkeypatch.setattr(mugen_runner, "record_test_job_event", lambda *a, **kw: None)

    with pytest.raises(JobExecutionError) as exc_info:
        mugen_runner.wait_for_ssh_ready(
            db=None,  # type: ignore[arg-type]
            node=control,  # type: ignore[arg-type]
            job=SimpleNamespace(created_at=test_management_models.utc_now()),  # type: ignore[arg-type]
            timeout_seconds=60,
            retry_interval_seconds=10,
            cancel_event=cancel_event,
        )

    assert exc_info.value.code == "job_cancelled"
    # 关键:取消后不再 sleep 继续下一轮(忙循环防护)
    assert sleeps == []


def test_ensure_test_job_within_deadline_raises_job_cancelled_before_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """cancel_event 已 set → 抛 job_cancelled,即使 job 尚未 15h 过期也优先取消语义。"""
    cancel_event = threading.Event()
    cancel_event.set()
    job = SimpleNamespace(  # type: ignore[arg-type]
        created_at=test_management_models.utc_now(),
    )

    with pytest.raises(JobExecutionError) as exc_info:
        test_execution.ensure_test_job_within_deadline(job, cancel_event=cancel_event)

    assert exc_info.value.code == "job_cancelled"


def test_ensure_test_job_within_deadline_no_event_preserves_task_timeout() -> None:
    """回归:cancel_event 缺省时只按 15h 判 task_timeout,不引入新行为。"""
    expired = SimpleNamespace(  # type: ignore[arg-type]
        created_at=test_management_models.utc_now()
        - timedelta(hours=16),
        id=1,
    )

    with pytest.raises(JobExecutionError) as exc_info:
        test_execution.ensure_test_job_within_deadline(expired)

    assert exc_info.value.code == "task_timeout"


def test_process_test_job_soft_timeout_converges_under_5s(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SoftTimeLimitExceeded 抛在主线程时,`executor.shutdown(wait=True)` 不再
    被 `with __exit__` 阻塞:handler 先 set cancel_event → 子线程从"卡在 SSH"
    秒级返回 → 走 cleanup_failed_job_envs → 标 task_timeout。总耗时 <5s。
    """
    actor = create_user(
        db_session, username="softconv", password="test-pass", role=UserRole.TE
    )
    job = seed_pending_test_job(db_session, creator_user_id=actor.id)

    seen_events: list[threading.Event | None] = []

    def _fake_execute_env_set(db, *, job, env_set, actor, cancel_event=None, **kwargs):
        seen_events.append(cancel_event)
        # 模拟一个"最长 30s 才返回的 SSH,但被 cancel_event 秒级打断"
        if cancel_event is not None:
            cancel_event.wait(timeout=30)
        return False, True

    def _soft_as_completed(*_args, **_kwargs):
        # 主线程刚进入 for future in as_completed(...) 就被 SIGALRM 打断
        yield from ()
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(test_execution, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(test_execution, "execute_env_set", _fake_execute_env_set)
    monkeypatch.setattr(test_execution, "as_completed", _soft_as_completed)
    monkeypatch.setattr(test_execution, "cleanup_env_vms", lambda *_, **__: None)

    started = time.monotonic()
    test_execution.process_test_job(job.id)
    elapsed = time.monotonic() - started

    db_session.refresh(job)
    assert job.status == test_management_models.TestJobStatus.ERROR.value
    assert job.error_code == "task_timeout"
    # 若被 shutdown(wait=True) 阻塞,会等满 30s;<5s 才证明 set 生效。
    assert elapsed < 5.0, f"Soft handler 阻塞过久: {elapsed:.2f}s"
    for ev in seen_events:
        assert ev is not None and ev.is_set()


def test_process_test_job_db_cancel_finalizes_as_cancelled_not_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """已持久化的取消在启动前收敛，不能再创建环境或执行用例。"""
    actor = create_user(
        db_session, username="dbcancel", password="test-pass", role=UserRole.TE
    )
    job = seed_pending_test_job(db_session, creator_user_id=actor.id)
    env_set = job.env_sets[0]
    case_run = test_management_models.TestCaseRun(
        job=job,
        env_set=env_set,
        suite_name="suite-a",
        case_name="case-a",
    )
    db_session.add(case_run)
    job.cancel_requested = True
    db_session.commit()

    monkeypatch.setattr(test_execution, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(
        test_execution,
        "execute_env_set",
        lambda *_, **__: pytest.fail("cancelled job must not execute an env set"),
    )

    test_execution.process_test_job(job.id)

    db_session.refresh(job)
    db_session.refresh(env_set)
    db_session.refresh(case_run)
    assert job.status == test_management_models.TestJobStatus.CANCELLED.value
    assert job.error_code is None
    assert env_set.status == test_management_models.TestEnvSetStatus.NOT_EXECUTED.value
    assert case_run.status == test_management_models.TestCaseRunStatus.NOT_EXECUTED.value


def test_process_test_job_preserves_recovery_terminal_status(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """旧 Worker 的成功结果不能覆盖恢复服务已提交的 error。"""
    actor = create_user(
        db_session, username="recoveredjob", password="test-pass", role=UserRole.TE
    )
    job = seed_pending_test_job(db_session, creator_user_id=actor.id)

    def emulate_recovery(db: Session, *, job, **_: object) -> tuple[bool, bool]:
        job.status = test_management_models.TestJobStatus.ERROR.value
        job.error_code = "task_timeout"
        job.error_message = "recovery won"
        db.commit()
        return False, False

    monkeypatch.setattr(test_execution, "SessionLocal", lambda: nullcontext(db_session))
    monkeypatch.setattr(test_execution, "execute_env_set", emulate_recovery)

    test_execution.process_test_job(job.id)

    db_session.refresh(job)
    assert job.status == test_management_models.TestJobStatus.ERROR.value
    assert job.error_code == "task_timeout"


def test_test_job_cancel_watcher_sets_lifecycle_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VM 创建和环境准备阶段复用同一取消观察，提前唤醒 SSH 执行。"""
    from app.modules.test_management.execution import _start_test_job_cancel_watcher

    cancel_event = threading.Event()
    monkeypatch.setattr(test_execution, "_CANCEL_OBSERVATION_SECONDS", 0.01)
    monkeypatch.setattr(test_execution, "_cancel_check_factory", lambda _job_id: lambda: True)

    stop_event, watcher = _start_test_job_cancel_watcher(10000, cancel_event)
    try:
        assert cancel_event.wait(timeout=1)
    finally:
        stop_event.set()
        watcher.join(timeout=1)


def test_build_env_file_includes_mugen_commit_sha() -> None:
    """`build_env_file` 输出必须含 `KRONOS_MUGEN_COMMIT_SHA=<sha>`。
    docker 模块 pre_env 靠这个变量在 source kronos.env 后 pin mugen 到
    TestJob 建时冻结的 sha;若缺, docker 路径会拉 master tip 漂移。
    """
    job = SimpleNamespace(
        id=10214,
        name="docker-test",
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="official",
        arch="x86_64",
        mugen_commit_sha="ae2e4a96af19b614728cf4e149c0bbf14e3cb74b",
        update_packages=[],
    )
    env_set = SimpleNamespace(set_index=1, node_num=1, add_disk_num=0, add_nic_num=0)
    control = SimpleNamespace(ip="10.0.0.1", username="root", password="p")

    text = mugen_runner.build_env_file(job=job, env_set=env_set, control=control, peer=None)

    assert "KRONOS_MUGEN_COMMIT_SHA=ae2e4a96af19b614728cf4e149c0bbf14e3cb74b" in text


def test_mugen_sync_policy_is_enforced_by_domain_module(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = create_user(
        db_session,
        username="syncuser",
        password="test-pass",
        role=UserRole.TE,
    )
    monkeypatch.setattr(
        test_management_service,
        "acquire_mugen_sync_lock",
        lambda: pytest.fail("non-admin must be rejected before acquiring the lock"),
    )

    with pytest.raises(test_management_service.TestManagementPolicyError):
        test_management_service.enqueue_mugen_case_sync(db_session, actor=actor)


@pytest.mark.parametrize("path", ["/api/v1/test-cases/sync", "/api/v1/test-cases/sync/events"])
def test_mugen_sync_policy_is_checked_before_lazy_recovery(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    token = login_as(client, db_session, username="syncuser", role=UserRole.TE)
    monkeypatch.setattr(
        test_management_router,
        "recover_interrupted_tasks",
        lambda *_args, **_kwargs: pytest.fail("unauthorized requests must not run recovery"),
    )

    request = client.post if path.endswith("/sync") else client.get
    response = request(
        path,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_mugen_sync_uses_task_id_as_lock_token(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = create_user(
        db_session,
        username="syncadmin",
        password="test-pass",
        role=UserRole.ADMIN,
    )
    lock_tokens: list[str] = []
    sent: dict[str, object] = {}

    def acquire_lock(token: str | None = None) -> str:
        assert token is not None
        lock_tokens.append(token)
        return token

    def send_task(name: str, **kwargs: object) -> None:
        sent.update({"name": name, **kwargs})

    monkeypatch.setattr(
        test_management_service,
        "acquire_mugen_sync_lock",
        acquire_lock,
    )
    monkeypatch.setattr(test_management_service.celery_app, "send_task", send_task)

    task_id = test_management_service.enqueue_mugen_case_sync(db_session, actor=actor)

    assert lock_tokens == [task_id]
    assert sent["task_id"] == task_id
    assert sent["args"] == [actor.id, task_id]


def test_write_remote_file_restricts_permissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run_ssh_command(**kwargs: object) -> RemoteCommandResult:
        captured.update(kwargs)
        return RemoteCommandResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        test_management_remote,
        "run_ssh_command",
        fake_run_ssh_command,
    )

    test_management_remote.write_remote_file(
        target=test_management_remote.RemoteTarget(
            host="192.0.2.1", username="root", password="secret"
        ),
        path="/opt/mugen/kronos.env",
        content="PASSWORD=secret\n",
    )

    assert "umask 077" in str(captured["command"])
    assert "chmod 600 /opt/mugen/kronos.env" in str(captured["command"])


def test_release_mugen_sync_lock_compares_and_deletes_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.value = "current-token"
            self.calls: list[tuple[str, int, str, str]] = []

        def eval(
            self,
            script: str,
            key_count: int,
            key: str,
            token: str,
        ) -> int:
            self.calls.append((script, key_count, key, token))
            if self.value == token:
                self.value = None
                return 1
            return 0

    client = FakeRedis()
    monkeypatch.setattr(test_management_service, "redis_client", lambda: client)

    test_management_service.release_mugen_sync_lock("stale-token")
    assert client.value == "current-token"

    test_management_service.release_mugen_sync_lock("current-token")
    assert client.value is None
    assert all(call[1] == 1 for call in client.calls)
    assert all(call[2] == test_management_service.MUGEN_SYNC_LOCK_KEY for call in client.calls)


def test_configure_mugen_node_succeeds_without_retry_on_first_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")
    node = SimpleNamespace(ip="192.0.2.20", username="root", password="password")

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        mugen_runner,
        "record_test_job_event",
        lambda *a, phase, level="info", **kw: events.append(phase),
    )

    mugen_runner.configure_mugen_node(
        FakeSession(),  # type: ignore[arg-type]
        job=SimpleNamespace(created_at=test_management_models.utc_now()),  # type: ignore[arg-type]
        control=control,  # type: ignore[arg-type]
        node=node,  # type: ignore[arg-type]
        role="control",
    )

    assert events == ["mugen_config", "mugen_config_done"]


def test_configure_mugen_node_retries_on_transient_failure_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = iter(
        [
            RemoteCommandResult(
                returncode=1,
                stdout="",
                stderr="Connection timed out during banner exchange",
            ),
            RemoteCommandResult(
                returncode=1,
                stdout="",
                stderr="Connection timed out during banner exchange",
            ),
            RemoteCommandResult(returncode=0, stdout="", stderr=""),
        ]
    )
    sleeps: list[float] = []
    events: list[tuple[str, str]] = []
    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")
    node = SimpleNamespace(ip="192.0.2.20", username="root", password="password")

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(mugen_runner, "run_control_command", lambda **_: next(results))
    monkeypatch.setattr(mugen_runner.time, "sleep", sleeps.append)
    monkeypatch.setattr(
        mugen_runner,
        "record_test_job_event",
        lambda *a, phase, level="info", **kw: events.append((phase, level)),
    )

    mugen_runner.configure_mugen_node(
        FakeSession(),  # type: ignore[arg-type]
        job=SimpleNamespace(created_at=test_management_models.utc_now()),  # type: ignore[arg-type]
        control=control,  # type: ignore[arg-type]
        node=node,  # type: ignore[arg-type]
        role="peer",
    )

    assert [phase for phase, _ in events] == [
        "mugen_config",
        "mugen_config_retry",
        "mugen_config_retry",
        "mugen_config_done",
    ]
    assert all(level == "warning" for _, level in events[1:-1])
    assert sleeps == [10, 10]


def test_configure_mugen_node_fails_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    events: list[tuple[str, str]] = []
    control = SimpleNamespace(ip="192.0.2.10", username="root", password="password")
    node = SimpleNamespace(ip="192.0.2.20", username="root", password="password")

    class FakeSession:
        @staticmethod
        def commit() -> None:
            pass

    monkeypatch.setattr(
        mugen_runner,
        "run_control_command",
        lambda **_: RemoteCommandResult(
            returncode=1,
            stdout="",
            stderr="Connection timed out during banner exchange",
        ),
    )
    monkeypatch.setattr(mugen_runner.time, "sleep", sleeps.append)
    monkeypatch.setattr(
        mugen_runner,
        "record_test_job_event",
        lambda *a, phase, level="info", **kw: events.append((phase, level)),
    )

    with pytest.raises(JobExecutionError) as exc_info:
        mugen_runner.configure_mugen_node(
            FakeSession(),  # type: ignore[arg-type]
            job=SimpleNamespace(created_at=test_management_models.utc_now()),  # type: ignore[arg-type]
            control=control,  # type: ignore[arg-type]
            node=node,  # type: ignore[arg-type]
            role="control",
        )

    assert exc_info.value.code == "mugen_config_failed"
    assert sum(1 for phase, _ in events if phase == "mugen_config_retry") == 4
    assert any(
        phase == "mugen_config_failed" and level == "error" for phase, level in events
    )
    assert sleeps == [10, 10, 10, 10]

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
from types import SimpleNamespace

import pytest
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
from app.modules.test_management import tasks as test_management_tasks
from app.modules.test_management.envs import vm as vm_env
from app.modules.test_management.errors import TestJobExecutionError as JobExecutionError
from app.modules.test_management.frameworks.mugen import parse_suite_documents
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

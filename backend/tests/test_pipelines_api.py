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
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.credentials import encrypt_secret
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.leases.schemas import LeaseCreate
from app.modules.leases.service import create_lease
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.pipelines.seed import seed_pipeline_types
from app.modules.resources.models import Resource, ResourceType
from app.modules.tasks.models import TaskEvent
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
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
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
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def stub_run_job_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub enqueue_run_job so trigger tests don't need a Celery broker."""
    from app.modules.pipelines import service as pipeline_service

    def fake_enqueue(run_job, actor_user_id):  # noqa: ANN001
        run_job.status = "pending"
        return "fake-task-id"

    monkeypatch.setattr(pipeline_service, "enqueue_run_job", fake_enqueue)


@pytest.fixture()
def seeded_pipeline_types(db_session: Session) -> None:
    """Seed `update` and `release` pipeline types so trigger_pipeline dispatch works."""
    seed_pipeline_types(db_session)


def test_list_module_templates(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    db_session.add(
        TestModuleTemplate(
            name="docker",
            display_name="Docker Test",
            suite_name="smoke",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/pipelines/module-templates",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "docker"
    assert data[0]["suite_name"] == "smoke"


def test_list_module_templates_filter_by_pipeline_type(
    client: TestClient, db_session: Session
) -> None:
    token = login_as(client, db_session, username="adminfilt", role=UserRole.ADMIN)
    db_session.add_all(
        [
            TestModuleTemplate(
                name="docker",
                display_name="Docker",
                suite_name="smoke",
                pipeline_type="update",
            ),
            TestModuleTemplate(
                name="release-smoke",
                display_name="smoke",
                suite_name="smoke",
                pipeline_type="release",
            ),
            TestModuleTemplate(
                name="release-ltp",
                display_name="ltp",
                suite_name="ltp",
                pipeline_type="release",
            ),
        ]
    )
    db_session.commit()

    # No filter → all 3
    response = client.get("/api/v1/pipelines/module-templates", headers=auth_headers(token))
    assert response.status_code == 200
    assert len(response.json()) == 3

    # Filter by release → 2
    response = client.get(
        "/api/v1/pipelines/module-templates?pipeline_type=release",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all(t["pipeline_type"] == "release" for t in items)

    # Filter by update → 1
    response = client.get(
        "/api/v1/pipelines/module-templates?pipeline_type=update",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "docker"


def test_update_module_template(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    template = TestModuleTemplate(
        name="kernel",
        display_name="Kernel Test",
        suite_name="ltp",
    )
    db_session.add(template)
    db_session.commit()

    response = client.put(
        f"/api/v1/pipelines/module-templates/{template.id}",
        headers=auth_headers(token),
        json={
            "display_name": "Kernel LTP Test",
            "pre_env_script": "echo prepare",
            "post_env_script": "echo cleanup",
        },
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Kernel LTP Test"
    assert response.json()["pre_env_script"] == "echo prepare"


def test_create_pipeline_config(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
    )
    db_session.add(template)
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "openEuler Update Weekly",
            "config_data": {
                "module_template_ids": [template.id],
                "repo_base_url": "http://121.36.84.172/repo.openeuler.org",
            },
            "versions": ["24.03-LTS-SP3", "22.03-LTS-SP4"],
            "archs": ["aarch64", "x86_64"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "openEuler Update Weekly"
    assert data["versions"] == ["24.03-LTS-SP3", "22.03-LTS-SP4"]
    assert data["archs"] == ["aarch64", "x86_64"]
    assert data["config_data"]["module_template_ids"] == [template.id]


def _add_update_template(db: Session, name: str) -> TestModuleTemplate:
    template = TestModuleTemplate(
        name=name,
        display_name=name,
        suite_name="cli-test",
        pipeline_type="update",
        case_filter=(
            "repodata_union" if name == "pkgunion" else
            "repodata_packages" if name == "pkgcmd" else
            "service_test_cases" if name == "pkgserver" else "none"
        ),
        env_type="both",
    )
    db.add(template)
    db.flush()
    return template


def test_create_update_config_rejects_pkgunion_with_pkgcmd(
    client: TestClient, db_session: Session
) -> None:
    """pkgunion 与 pkgcmd 用例并集重叠（repodata 路全包含），保存配置时拦截。"""
    pkgunion = _add_update_template(db_session, "pkgunion")
    pkgcmd = _add_update_template(db_session, "pkgcmd")
    db_session.commit()
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "union-conflict",
            "config_data": {"module_template_ids": [pkgunion.id, pkgcmd.id]},
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
        },
    )
    assert response.status_code == 422
    assert "pkgunion" in response.json()["error"]["message"]


def test_create_update_config_rejects_pkgunion_with_pkgserver(
    client: TestClient, db_session: Session
) -> None:
    pkgunion = _add_update_template(db_session, "pkgunion")
    pkgserver = _add_update_template(db_session, "pkgserver")
    db_session.commit()
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "union-conflict-2",
            "config_data": {"module_template_ids": [pkgserver.id, pkgunion.id]},
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
        },
    )
    assert response.status_code == 422


def test_create_update_config_allows_pkgunion_alone_and_legacy_pair(
    client: TestClient, db_session: Session
) -> None:
    """pkgunion 单独勾选合法；不含 pkgunion 时 pkgcmd+pkgserver 同勾维持现状合法。"""
    pkgunion = _add_update_template(db_session, "pkgunion")
    pkgcmd = _add_update_template(db_session, "pkgcmd")
    pkgserver = _add_update_template(db_session, "pkgserver")
    db_session.commit()
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)

    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "union-only",
            "config_data": {"module_template_ids": [pkgunion.id]},
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
        },
    )
    assert response.status_code == 201, response.text

    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "legacy-pair",
            "config_data": {"module_template_ids": [pkgcmd.id, pkgserver.id]},
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
        },
    )
    assert response.status_code == 201, response.text


def test_update_update_config_rejects_pkgunion_conflict(
    client: TestClient, db_session: Session
) -> None:
    """update 路径同样拦截：合法配置改成 pkgunion+pkgserver 组合 → 422。"""
    pkgunion = _add_update_template(db_session, "pkgunion")
    pkgserver = _add_update_template(db_session, "pkgserver")
    db_session.commit()
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    created = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "union-update-target",
            "config_data": {"module_template_ids": [pkgserver.id]},
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
        },
    )
    assert created.status_code == 201
    config_id = created.json()["id"]

    response = client.put(
        f"/api/v1/pipelines/configs/{config_id}",
        headers=auth_headers(token),
        json={
            "config_data": {"module_template_ids": [pkgserver.id, pkgunion.id]},
        },
    )
    assert response.status_code == 422


def test_create_release_config_valid(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
) -> None:
    """release config：单版本 + case_selections + kernel_variant 合法创建。"""
    from app.modules.test_management.models import MugenCase

    db_session.add(
        MugenCase(
            suite_name="smoke",
            case_name="oe_test_smoke_basic",
            env_type="vm",
            node_num=1,
            commit_sha="abc",
        )
    )
    db_session.commit()
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "release-rc1",
            "pipeline_type": "release",
            "versions": ["24.03-LTS-SP3"],
            "archs": ["aarch64", "x86_64"],
            "image_round": "round-9",
            "config_data": {
                "case_selections": [
                    {"suite_name": "smoke", "case_names": ["oe_test_smoke_basic"]}
                ],
                "kernel_variant": "26.09-with-kernel-6.18",
            },
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["config_data"]["case_selections"] == [
        {"suite_name": "smoke", "case_names": ["oe_test_smoke_basic"]}
    ]


def test_create_release_config_rejects_multi_version(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "release-multi",
            "pipeline_type": "release",
            "versions": ["24.03-LTS-SP3", "25.03"],
            "archs": ["x86_64"],
            "config_data": {"case_selections": []},
        },
    )
    assert response.status_code == 422


def test_create_release_config_rejects_both_kernel_params(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "release-both-kernel",
            "pipeline_type": "release",
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
            "config_data": {
                "case_selections": [],
                "kernel_variant": "26.09-with-kernel-6.18",
                "kernel_rpm_url": "http://example/kernel.rpm",
            },
        },
    )
    assert response.status_code == 422


def test_create_release_config_rejects_bad_rpm_url(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
) -> None:
    """kernel_rpm_url 必须 HTTP/HTTPS + .rpm 结尾（配置级 fail-fast）。"""
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "release-bad-url",
            "pipeline_type": "release",
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
            "config_data": {
                "case_selections": [],
                "kernel_rpm_url": "ftp://example/not-rpm",
            },
        },
    )
    assert response.status_code == 422


def test_create_release_config_rejects_missing_case_selections(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
) -> None:
    """release 必须提供 case_selections（避免 kernel_variant 单独提交却 0 RunJob 的静默 no-op）。"""
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "release-no-cases",
            "pipeline_type": "release",
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
            "config_data": {"kernel_variant": "26.09-with-kernel-6.18"},
        },
    )
    assert response.status_code == 422


def test_create_release_config_rejects_unknown_suite(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "release-bad-suite",
            "pipeline_type": "release",
            "versions": ["24.03-LTS-SP3"],
            "archs": ["x86_64"],
            "config_data": {
                "case_selections": [
                    {"suite_name": "nonexistent-suite", "case_names": []}
                ],
            },
        },
    )
    assert response.status_code == 422


def test_list_pipeline_configs(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    db_session.add(
        PipelineConfig(
            name="weekly",
            versions=["24.03-LTS-SP3"],
            archs=["aarch64"],
            config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "weekly"


def test_list_pipeline_configs_includes_latest_execution(
    client: TestClient, db_session: Session
) -> None:
    """配置列表每条带最近一次 execution（status+triggered_at）；无执行为 null。"""

    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    cfg_no_exec = PipelineConfig(
        name="no-exec",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    cfg_with_exec = PipelineConfig(
        name="with-exec",
        versions=["24.03-LTS-SP4"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add_all([cfg_no_exec, cfg_with_exec])
    db_session.flush()
    db_session.add(
        PipelineExecution(
            config_id=cfg_with_exec.id,
            triggered_by="admin",
            versions=["24.03-LTS-SP4"],
            archs=["aarch64"],
            # stored status 故意写 succeeded，但无 runs → compute_execution_status 应返回
            # "pending"；断言 pending 即验证 API 走的是 computed status（stored 恒不准）。
            status="succeeded",
        )
    )
    db_session.commit()

    response = client.get("/api/v1/pipelines/configs", headers=auth_headers(token))
    assert response.status_code == 200
    by_name = {c["name"]: c for c in response.json()}
    assert by_name["no-exec"]["latest_execution"] is None
    latest = by_name["with-exec"]["latest_execution"]
    assert latest is not None
    assert latest["status"] == "pending"
    assert latest["triggered_at"] is not None


def test_update_pipeline_config_versions(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    config = PipelineConfig(
        name="weekly",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add(config)
    db_session.commit()

    response = client.put(
        f"/api/v1/pipelines/configs/{config.id}",
        headers=auth_headers(token),
        json={
            "versions": ["24.03-LTS-SP3", "24.03-LTS-SP4", "22.03-LTS-SP4"],
        },
    )

    assert response.status_code == 200
    assert response.json()["versions"] == ["24.03-LTS-SP3", "24.03-LTS-SP4", "22.03-LTS-SP4"]


def test_non_admin_cannot_create_config(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="teuser", role=UserRole.TE)

    response = client.post(
        "/api/v1/pipelines/configs",
        headers=auth_headers(token),
        json={
            "name": "test",
            "config_data": {"module_template_ids": []},
            "versions": [],
            "archs": [],
            "repo_base_url": "http://example.com",
        },
    )

    assert response.status_code == 403


def test_trigger_pipeline_creates_run_and_jobs(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    docker_tmpl = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
    )
    config = PipelineConfig(
        name="weekly",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={
            "module_template_ids": [docker_tmpl.id] if False else [],
            "repo_base_url": "http://example.com",
        },
    )
    db_session.add_all([docker_tmpl, config])
    db_session.commit()
    config.config_data = {**(config.config_data or {}), "module_template_ids": [docker_tmpl.id]}
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )

    assert response.status_code == 201
    exec_data = response.json()
    assert exec_data["versions"] == ["24.03-LTS-SP3"]
    assert exec_data["status"] == "pending"

    # Get runs for this execution
    runs_resp = client.get(
        f"/api/v1/pipelines/executions/{exec_data['id']}/runs",
        headers=auth_headers(token),
    )
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) == 1
    assert runs[0]["version"] == "24.03-LTS-SP3"

    # Get jobs for the run
    jobs_response = client.get(
        f"/api/v1/pipelines/runs/{runs[0]['id']}/jobs",
        headers=auth_headers(token),
    )
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["arch"] == "aarch64"
    assert jobs[0]["status"] == "pending"


@pytest.mark.parametrize(
    "path_kind",
    ["run_jobs", "execution_summary", "run_job_detail"],
)
def test_pipeline_status_reads_lazily_recover_stale_run_job(
    client: TestClient,
    db_session: Session,
    path_kind: str,
) -> None:
    token = login_as(
        client,
        db_session,
        username=f"reader{len(path_kind)}",
        role=UserRole.ADMIN,
    )
    old_time = datetime.now(UTC) - timedelta(hours=16)
    config = PipelineConfig(
        name=f"config-{path_kind}",
        versions=["openEuler-24.03-LTS-SP4"],
        archs=["aarch64"],
    )
    template = TestModuleTemplate(
        name=f"module-{path_kind}",
        display_name="Module",
        suite_name="suite",
    )
    db_session.add_all([config, template])
    db_session.flush()
    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="user-1",
        versions=config.versions,
        archs=config.archs,
    )
    db_session.add(execution)
    db_session.flush()
    run = PipelineRun(
        config_id=config.id,
        execution_id=execution.id,
        version=config.versions[0],
        triggered_by="user-1",
    )
    db_session.add(run)
    db_session.flush()
    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="aarch64",
        status="running",
        task_id=f"task-{path_kind}",
    )
    db_session.add(run_job)
    db_session.flush()
    db_session.add(
        TaskEvent(
            task_type="pipeline_runjob",
            subject_type="runjob",
            subject_id=run_job.id,
            celery_task_id=run_job.task_id,
            phase="started",
            message="started",
            created_at=old_time,
        )
    )
    db_session.commit()

    paths = {
        "run_jobs": f"/api/v1/pipelines/runs/{run.id}/jobs",
        "execution_summary": f"/api/v1/pipelines/executions/{execution.id}/summary",
        "run_job_detail": f"/api/v1/pipelines/run-jobs/{run_job.id}",
    }
    path = paths.get(path_kind)
    assert path is not None
    response = client.get(path, headers=auth_headers(token))

    assert response.status_code == 200
    db_session.refresh(run_job)
    assert run_job.status == "error"
    recovery_event = db_session.scalar(
        select(TaskEvent).where(
            TaskEvent.subject_id == run_job.id,
            TaskEvent.error_code == "task_timeout",
        )
    )
    assert recovery_event is not None


def test_trigger_pipeline_rejects_unsupported_64k_version(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin64k", role=UserRole.ADMIN)
    config = PipelineConfig(
        name="unsupported-64k",
        versions=["openEuler-24.03-LTS-SP3-64k"],
        archs=["aarch64"],
        config_data={"module_template_ids": []},
    )
    db_session.add(config)
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )

    assert response.status_code == 422
    assert "当前仅支持" in response.json()["error"]["message"]
    assert db_session.scalar(select(func.count(PipelineExecution.id))) == 0


def test_trigger_pipeline_rejects_unplanned_64k_architecture(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin64karch", role=UserRole.ADMIN)
    config = PipelineConfig(
        name="unsupported-64k-arch",
        versions=["openEuler-24.03-LTS-SP4-64k"],
        archs=["riscv64"],
        config_data={"module_template_ids": []},
    )
    db_session.add(config)
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )

    assert response.status_code == 422
    assert "aarch64" in response.json()["error"]["message"]
    assert db_session.scalar(select(func.count(PipelineExecution.id))) == 0


def test_trigger_physical_pipeline_requires_available_owned_resource(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="adminphysical", role=UserRole.ADMIN)
    template = TestModuleTemplate(
        name="kernel",
        display_name="Kernel",
        suite_name="ltp",
        env_type="physical",
    )
    config = PipelineConfig(
        name="physical",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": []},
    )
    db_session.add_all([template, config])
    db_session.commit()
    config.config_data = {"module_template_ids": [template.id]}
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )

    assert response.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(PipelineExecution)) == 0

    actor = db_session.scalar(select(User).where(User.username == "adminphysical"))
    assert actor is not None
    resource = Resource(
        resource_code="physical-for-trigger",
        resource_type=ResourceType.PHYSICAL.value,
        arch="aarch64",
        primary_ip="10.0.0.10",
        ssh_username="root",
        ssh_password_ciphertext=encrypt_secret("test-pass"),
        usage_scenario="kernel-update",
    )
    db_session.add(resource)
    db_session.commit()
    create_lease(
        db_session,
        resource=resource,
        actor=actor,
        payload=LeaseCreate(purpose="physical test"),
    )
    blocking_job = TestJob(
        creator_user_id=actor.id,
        name="already-running",
        status="running",
        framework="mugen",
        env_type="physical",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-1",
        arch="aarch64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_failed_env=False,
    )
    blocking_env = TestEnvSet(job=blocking_job, set_index=0, status="running", node_num=1)
    TestEnvNode(
        env_set=blocking_env,
        node_index=0,
        role="control",
        status="ready",
        resource_id=resource.id,
    )
    db_session.add(blocking_job)
    db_session.commit()

    busy = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )
    assert busy.status_code == 409
    assert "没有可用的自有物理机" in busy.json()["error"]["message"]

    blocking_job.status = "succeeded"
    db_session.commit()
    available = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )
    assert available.status_code == 201


def test_trigger_enqueues_run_jobs_only_after_commit(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """竞态防护：所有 run_job 的 enqueue 必须在 db.commit() 之后。

    worker 用独立 session 查 run_job；若 enqueue 早于 commit，worker 在事务可见前
    消费 task 会查不到 run_job 而 return，导致 run_job 永远 pending。
    """
    from sqlalchemy import event

    from app.modules.pipelines import service as pipeline_service

    commits = {"n": 0}

    @event.listens_for(db_session, "after_commit")
    def _on_commit(session: Session) -> None:
        commits["n"] += 1

    observed: list[int] = []

    def fake_enqueue(run_job, actor_user_id):  # noqa: ANN001
        observed.append(commits["n"])
        return "fake-task-id"

    monkeypatch.setattr(pipeline_service, "enqueue_run_job", fake_enqueue)

    token = login_as(client, db_session, username="admintc", role=UserRole.ADMIN)
    tmpl = TestModuleTemplate(name="dockertc", display_name="Docker TC", suite_name="smoke")
    config = PipelineConfig(
        name="wktc",
        versions=["v1", "v2"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add_all([tmpl, config])
    db_session.commit()
    config.config_data = {**(config.config_data or {}), "module_template_ids": [tmpl.id]}
    db_session.commit()

    baseline = commits["n"]
    try:
        response = client.post(
            "/api/v1/pipelines/trigger",
            headers=auth_headers(token),
            json={"config_id": config.id},
        )
    finally:
        event.remove(db_session, "after_commit", _on_commit)

    assert response.status_code == 201
    assert len(observed) == 2, observed
    assert all(c > baseline for c in observed), (baseline, observed)


def test_trigger_marks_runjob_error_when_enqueue_fails(
    client: TestClient,
    db_session: Session,
    seeded_pipeline_types: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """单个 run_job enqueue 失败 → 标该 run_job error，其余继续，返 201。"""

    from app.modules.pipelines import service as pipeline_service
    from app.modules.test_management.service import TestJobQueueUnavailableError

    calls = {"n": 0}

    def fake_enqueue(run_job, actor_user_id):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 2:
            raise TestJobQueueUnavailableError("broker down")
        return "fake-task-id"

    monkeypatch.setattr(pipeline_service, "enqueue_run_job", fake_enqueue)

    token = login_as(client, db_session, username="admintc2", role=UserRole.ADMIN)
    tmpl = TestModuleTemplate(name="dockertc2", display_name="Docker TC2", suite_name="smoke")
    config = PipelineConfig(
        name="wktc2",
        versions=["v1", "v2", "v3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add_all([tmpl, config])
    db_session.commit()
    config.config_data = {**(config.config_data or {}), "module_template_ids": [tmpl.id]}
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )

    assert response.status_code == 201
    exec_id = response.json()["id"]

    run_jobs_db = (
        db_session.execute(
            select(PipelineRunJob)
            .join(PipelineRun, PipelineRun.id == PipelineRunJob.pipeline_run_id)
            .where(PipelineRun.execution_id == exec_id)
            .order_by(PipelineRun.version, PipelineRunJob.arch)
        )
        .scalars()
        .all()
    )
    statuses = [rj.status for rj in run_jobs_db]
    assert len(statuses) == 3, statuses
    assert statuses.count("error") == 1, statuses
    assert statuses.count("pending") == 2, statuses

    events = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.subject_type == "runjob",
                TaskEvent.phase == "enqueue_failed",
                TaskEvent.error_code == "queue_unavailable",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1


def test_trigger_pipeline_multiple_versions_and_archs(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin2", role=UserRole.ADMIN)
    tmpl = TestModuleTemplate(name="kernel", display_name="Kernel", suite_name="ltp")
    config = PipelineConfig(
        name="multi",
        versions=["24.03-LTS-SP3", "22.03-LTS-SP4"],
        archs=["aarch64", "x86_64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add_all([tmpl, config])
    db_session.commit()
    config.config_data = {**(config.config_data or {}), "module_template_ids": [tmpl.id]}
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )

    assert response.status_code == 201
    exec_data = response.json()
    assert set(exec_data["versions"]) == {"24.03-LTS-SP3", "22.03-LTS-SP4"}

    runs_resp = client.get(
        f"/api/v1/pipelines/executions/{exec_data['id']}/runs",
        headers=auth_headers(token),
    )
    assert len(runs_resp.json()) == 2


def test_trigger_pipeline_env_type_both_creates_one_job(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    token = login_as(client, db_session, username="admin3", role=UserRole.ADMIN)
    pkgcmd_tmpl = TestModuleTemplate(
        name="pkgcmd",
        display_name="Pkgcmd",
        suite_name="cli-test",
        case_filter="repodata_packages",
        env_type="both",
    )
    config = PipelineConfig(
        name="split",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={
            "module_template_ids": [],
            "pkgcmd_physical_enabled": False,
            "repo_base_url": "http://example.com",
        },
    )
    db_session.add_all([pkgcmd_tmpl, config])
    db_session.commit()
    config.config_data = {**(config.config_data or {}), "module_template_ids": [pkgcmd_tmpl.id]}
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},
    )

    assert response.status_code == 201
    exec_data = response.json()

    runs_resp = client.get(
        f"/api/v1/pipelines/executions/{exec_data['id']}/runs",
        headers=auth_headers(token),
    )
    run_id = runs_resp.json()[0]["id"]

    jobs_response = client.get(
        f"/api/v1/pipelines/runs/{run_id}/jobs",
        headers=auth_headers(token),
    )
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["env_type"] is None


def test_trigger_pipeline_image_round_override_persists_on_execution(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    """Trigger-level image_round should be persisted on PipelineExecution so the
    Celery worker (which reads execution fresh from DB) sees the override.
    """

    token = login_as(client, db_session, username="adminir", role=UserRole.ADMIN)
    docker_tmpl = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
    )
    config = PipelineConfig(
        name="release-cfg",
        pipeline_type="update",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://x"},
        dist="openEuler",
        image_round="",  # config-level empty
    )
    db_session.add_all([docker_tmpl, config])
    db_session.commit()
    config.config_data = {"module_template_ids": [docker_tmpl.id], "repo_base_url": "http://x"}
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={
            "config_id": config.id,
            "image_round": "round-9",  # trigger-level override
        },
    )

    assert response.status_code == 201
    execution_id = response.json()["id"]

    execution = db_session.get(PipelineExecution, execution_id)
    assert execution is not None
    assert execution.image_round == "round-9"  # override persisted


def test_trigger_pipeline_without_image_round_uses_config_value(
    client: TestClient,
    db_session: Session,
    stub_run_job_queue: None,
    seeded_pipeline_types: None,
) -> None:
    """If trigger doesn't pass image_round, execution.image_round stays None
    and builder falls back to config.image_round.
    """

    token = login_as(client, db_session, username="adminir2", role=UserRole.ADMIN)
    docker_tmpl = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
    )
    config = PipelineConfig(
        name="update-cfg",
        pipeline_type="update",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://x"},
        dist="openEuler",
        image_round="round-1",  # config-level set
    )
    db_session.add_all([docker_tmpl, config])
    db_session.commit()
    config.config_data = {"module_template_ids": [docker_tmpl.id], "repo_base_url": "http://x"}
    db_session.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        headers=auth_headers(token),
        json={"config_id": config.id},  # no image_round override
    )

    assert response.status_code == 201
    execution_id = response.json()["id"]

    execution = db_session.get(PipelineExecution, execution_id)
    assert execution is not None
    assert execution.image_round is None  # no override


def test_build_test_job_prefers_execution_image_round_over_config(
    db_session: Session,
) -> None:
    """Builder should use execution.image_round when set, else fall back to config.image_round."""
    from app.modules.pipelines.builder import build_test_job_for_run_job
    from app.modules.test_management.models import MugenCase

    # Seed a mugen case so select_cases doesn't return empty
    db_session.add(
        MugenCase(
            suite_name="smoke",
            case_name="oe_test_smoke",
            env_type="vm",
            node_num=1,
            commit_sha="abc",
        )
    )
    db_session.flush()

    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
    )
    config = PipelineConfig(
        name="cfg",
        pipeline_type="update",
        versions=["v1"],
        archs=["x86_64"],
        config_data={"module_template_ids": [template.id], "repo_base_url": "http://x"},
        dist="openEuler",
        image_round="config-level-round",
    )
    db_session.add_all([template, config])
    db_session.flush()

    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="admin",
        versions=["v1"],
        archs=["x86_64"],
        image_round="trigger-level-round",  # override
    )
    db_session.add(execution)
    db_session.flush()

    run = PipelineRun(
        config_id=config.id,
        execution_id=execution.id,
        version="v1",
        status="pending",
        triggered_by="admin",
    )
    db_session.add(run)
    db_session.flush()

    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="x86_64",
        env_type=None,
        status="pending",
    )
    db_session.add(run_job)
    db_session.flush()

    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version="v1",
        actor_user_id="admin",
    )
    assert job.image_round == "trigger-level-round"


def test_build_test_job_falls_back_to_config_image_round(
    db_session: Session,
) -> None:
    """When execution.image_round is None, builder should use config.image_round."""
    from app.modules.pipelines.builder import build_test_job_for_run_job
    from app.modules.test_management.models import MugenCase

    db_session.add(
        MugenCase(
            suite_name="smoke",
            case_name="oe_test_smoke",
            env_type="vm",
            node_num=1,
            commit_sha="abc",
        )
    )
    db_session.flush()

    template = TestModuleTemplate(
        name="docker",
        display_name="Docker",
        suite_name="smoke",
    )
    config = PipelineConfig(
        name="cfg2",
        pipeline_type="update",
        versions=["v1"],
        archs=["x86_64"],
        config_data={"module_template_ids": [template.id], "repo_base_url": "http://x"},
        dist="openEuler",
        image_round="config-level-round",
    )
    db_session.add_all([template, config])
    db_session.flush()

    # execution with image_round=None (no override)
    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="admin",
        versions=["v1"],
        archs=["x86_64"],
    )
    db_session.add(execution)
    db_session.flush()

    run = PipelineRun(
        config_id=config.id,
        execution_id=execution.id,
        version="v1",
        status="pending",
        triggered_by="admin",
    )
    db_session.add(run)
    db_session.flush()

    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="x86_64",
        env_type=None,
        status="pending",
    )
    db_session.add(run_job)
    db_session.flush()

    job = build_test_job_for_run_job(
        db_session,
        run_job=run_job,
        config=config,
        template=template,
        version="v1",
        actor_user_id="admin",
    )
    assert job.image_round == "config-level-round"


def test_list_pipeline_runs(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin4", role=UserRole.ADMIN)
    config = PipelineConfig(
        name="weekly",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add(config)
    db_session.commit()


    tmpl = TestModuleTemplate(name="docker", display_name="Docker", suite_name="smoke")
    db_session.add(tmpl)
    db_session.flush()
    run = PipelineRun(
        config_id=config.id,
        version="24.03-LTS-SP3",
        status="succeeded",
        triggered_by="admin4",
    )
    db_session.add(run)
    db_session.flush()
    # Add a RunJob with succeeded status so read-time worst-wins returns "succeeded"
    db_session.add(
        PipelineRunJob(
            pipeline_run_id=run.id,
            module_template_id=tmpl.id,
            arch="aarch64",
            env_type=None,
            status="succeeded",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/pipelines/runs",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "succeeded"


# ---------- pipeline_types CRUD + frameworks ----------


def test_list_pipeline_types(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    seed_pipeline_types(db_session)

    response = client.get("/api/v1/pipelines/types", headers=auth_headers(token))
    assert response.status_code == 200
    types = response.json()
    names = [t["name"] for t in types]
    assert "update" in names
    assert "release" in names

    update = next(t for t in types if t["name"] == "update")
    assert update["strategy_kind"] == "update_strategy"
    assert update["test_framework"] == "mugen"
    assert update["is_system"] is True


def test_create_pipeline_type_admin_only(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    response = client.post(
        "/api/v1/pipelines/types",
        headers=auth_headers(token),
        json={
            "name": "smoke",
            "display_name": "Smoke Test",
            "strategy_kind": "direct_run",
            "test_framework": "mugen",
        },
    )
    assert response.status_code == 403


def test_create_pipeline_type_rejects_a_class(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/types",
        headers=auth_headers(token),
        json={
            "name": "custom_update",
            "display_name": "Custom Update",
            "strategy_kind": "update_strategy",
            "test_framework": "mugen",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_pipeline_type_duplicate_name_409(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    seed_pipeline_types(db_session)
    response = client.post(
        "/api/v1/pipelines/types",
        headers=auth_headers(token),
        json={
            "name": "release",
            "display_name": "Dup",
            "strategy_kind": "direct_run",
            "test_framework": "mugen",
        },
    )
    assert response.status_code == 409


def test_create_pipeline_type_unknown_framework_422(
    client: TestClient, db_session: Session
) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    response = client.post(
        "/api/v1/pipelines/types",
        headers=auth_headers(token),
        json={
            "name": "pytest_pipeline",
            "display_name": "Pytest",
            "strategy_kind": "direct_run",
            "test_framework": "pytest",
        },
    )
    assert response.status_code == 422


def test_create_and_delete_pipeline_type_no_refs(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    create_resp = client.post(
        "/api/v1/pipelines/types",
        headers=auth_headers(token),
        json={
            "name": "smoke",
            "display_name": "Smoke",
            "strategy_kind": "direct_run",
            "test_framework": "mugen",
        },
    )
    assert create_resp.status_code == 201
    type_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/pipelines/types/{type_id}", headers=auth_headers(token))
    assert delete_resp.status_code == 204

    # Confirm it's gone
    list_resp = client.get("/api/v1/pipelines/types", headers=auth_headers(token))
    assert all(t["name"] != "smoke" for t in list_resp.json())


def test_delete_system_type_returns_403(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    seed_pipeline_types(db_session)
    update = next(
        t
        for t in client.get("/api/v1/pipelines/types", headers=auth_headers(token)).json()
        if t["name"] == "update"
    )
    response = client.delete(f"/api/v1/pipelines/types/{update['id']}", headers=auth_headers(token))
    assert response.status_code == 403


def test_delete_type_with_refs_returns_409(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    seed_pipeline_types(db_session)
    create_resp = client.post(
        "/api/v1/pipelines/types",
        headers=auth_headers(token),
        json={
            "name": "smoke",
            "display_name": "Smoke",
            "strategy_kind": "direct_run",
            "test_framework": "mugen",
        },
    )
    type_id = create_resp.json()["id"]

    # Add a config that references "smoke"
    db_session.add(
        PipelineConfig(
            name="cfg",
            pipeline_type="smoke",
            versions=["v1"],
            archs=["x86_64"],
            config_data={"suites": []},
        )
    )
    db_session.commit()

    delete_resp = client.delete(f"/api/v1/pipelines/types/{type_id}", headers=auth_headers(token))
    assert delete_resp.status_code == 409
    assert delete_resp.json()["error"]["code"] == "conflict"


def test_list_frameworks(client: TestClient, db_session: Session) -> None:
    token = login_as(client, db_session, username="te1", role=UserRole.TE)
    response = client.get("/api/v1/pipelines/frameworks", headers=auth_headers(token))
    assert response.status_code == 200
    frameworks = response.json()
    names = [f["name"] for f in frameworks]
    assert "mugen" in names
    mugen = next(f for f in frameworks if f["name"] == "mugen")
    assert mugen["display_name"]  # non-empty


# ---------- config delete + execution delete + list filtering ----------


def _seed_config_with_execution(db_session: Session, *, name="cfg-with-exec"):

    config = PipelineConfig(
        name=name,
        pipeline_type="update",
        versions=["v1"],
        archs=["x86_64"],
        config_data={"module_template_ids": [], "repo_base_url": ""},
    )
    db_session.add(config)
    db_session.flush()
    execution = PipelineExecution(
        config_id=config.id,
        triggered_by="admin",
        versions=["v1"],
        archs=["x86_64"],
    )
    db_session.add(execution)
    db_session.commit()
    return config, execution


def test_delete_pipeline_config_no_refs_returns_204(
    client: TestClient, db_session: Session, seeded_pipeline_types: None
) -> None:
    token = login_as(client, db_session, username="admindel1", role=UserRole.ADMIN)

    config = PipelineConfig(
        name="to-delete",
        pipeline_type="update",
        versions=["v1"],
        archs=["x86_64"],
        config_data={"module_template_ids": [], "repo_base_url": ""},
    )
    db_session.add(config)
    db_session.commit()

    response = client.delete(f"/api/v1/pipelines/configs/{config.id}", headers=auth_headers(token))
    assert response.status_code == 204
    # Confirm gone
    assert db_session.get(PipelineConfig, config.id) is None


def test_delete_pipeline_config_with_refs_returns_409(
    client: TestClient, db_session: Session, seeded_pipeline_types: None
) -> None:
    token = login_as(client, db_session, username="admindel2", role=UserRole.ADMIN)
    config, _execution = _seed_config_with_execution(db_session)

    response = client.delete(f"/api/v1/pipelines/configs/{config.id}", headers=auth_headers(token))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_delete_pipeline_config_non_admin_returns_403(
    client: TestClient, db_session: Session
) -> None:
    token = login_as(client, db_session, username="tedel1", role=UserRole.TE)

    config = PipelineConfig(
        name="te-delete",
        pipeline_type="update",
        versions=["v1"],
        archs=["x86_64"],
        config_data={},
    )
    db_session.add(config)
    db_session.commit()
    response = client.delete(f"/api/v1/pipelines/configs/{config.id}", headers=auth_headers(token))
    assert response.status_code == 403


def test_delete_pipeline_config_not_found_returns_404(
    client: TestClient, db_session: Session
) -> None:
    token = login_as(client, db_session, username="admindel3", role=UserRole.ADMIN)
    response = client.delete(
        "/api/v1/pipelines/configs/nonexistent-id", headers=auth_headers(token)
    )
    assert response.status_code == 404


def test_delete_pipeline_execution_returns_204_and_cascades(
    client: TestClient, db_session: Session, seeded_pipeline_types: None
) -> None:

    token = login_as(client, db_session, username="admindel4", role=UserRole.ADMIN)
    config, execution = _seed_config_with_execution(db_session)
    # Add a run to verify cascade (note: SQLite test DB doesn't enforce FK by default;
    # cascade is verified in production via PostgreSQL ondelete=CASCADE)
    run = PipelineRun(
        config_id=config.id,
        execution_id=execution.id,
        version="v1",
        status="pending",
        triggered_by="admin",
    )
    db_session.add(run)
    db_session.commit()
    execution_id = execution.id

    response = client.delete(
        f"/api/v1/pipelines/executions/{execution_id}", headers=auth_headers(token)
    )
    assert response.status_code == 204
    assert db_session.get(PipelineExecution, execution_id) is None


def test_delete_pipeline_execution_non_admin_returns_403(
    client: TestClient, db_session: Session
) -> None:
    token = login_as(client, db_session, username="tedel2", role=UserRole.TE)
    response = client.delete(
        "/api/v1/pipelines/executions/nonexistent", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_delete_pipeline_executions_by_config_batch(
    client: TestClient, db_session: Session, seeded_pipeline_types: None
) -> None:

    token = login_as(client, db_session, username="admindel5", role=UserRole.ADMIN)
    config, _ = _seed_config_with_execution(db_session)
    # Add 2 more executions
    for _ in range(2):
        db_session.add(
            PipelineExecution(
                config_id=config.id,
                triggered_by="admin",
                versions=["v1"],
                archs=["x86_64"],
            )
        )
    db_session.commit()
    assert (
        db_session.execute(
            select(func.count())
            .select_from(PipelineExecution)
            .where(PipelineExecution.config_id == config.id)
        ).scalar_one()
        == 3
    )

    response = client.delete(
        f"/api/v1/pipelines/configs/{config.id}/executions",
        headers=auth_headers(token),
    )
    assert response.status_code == 204
    # All 3 executions gone
    assert (
        db_session.execute(
            select(func.count())
            .select_from(PipelineExecution)
            .where(PipelineExecution.config_id == config.id)
        ).scalar_one()
        == 0
    )
    # Config still exists

    assert db_session.get(PipelineConfig, config.id) is not None


def test_list_pipeline_executions_filter_by_config_id(
    client: TestClient, db_session: Session, seeded_pipeline_types: None
) -> None:
    token = login_as(client, db_session, username="adminlst1", role=UserRole.ADMIN)
    config_a, _ = _seed_config_with_execution(db_session, name="cfg-a")
    config_b, _ = _seed_config_with_execution(db_session, name="cfg-b")

    response = client.get(
        f"/api/v1/pipelines/executions?config_id={config_a.id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["config_id"] == config_a.id


def test_list_pipeline_executions_limit_param(
    client: TestClient, db_session: Session, seeded_pipeline_types: None
) -> None:

    token = login_as(client, db_session, username="adminlst2", role=UserRole.ADMIN)
    config, _ = _seed_config_with_execution(db_session)
    # Add 5 more executions
    for _ in range(5):
        db_session.add(
            PipelineExecution(
                config_id=config.id,
                triggered_by="admin",
                versions=["v1"],
                archs=["x86_64"],
            )
        )
    db_session.commit()

    response = client.get("/api/v1/pipelines/executions?limit=3", headers=auth_headers(token))
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_run_log_read_endpoints_file_folder_download(
    client: TestClient, db_session: Session, tmp_path
) -> None:
    """Regression guard for the log read endpoints.

    Commit 715140a dropped the ``@router.get(.../files)`` decorator from
    ``list_dir_artifact_files_endpoint``, so every ``pkg_folder`` artifact
    (kernel ``ltp_results`` / ``logs`` / ``results``) 404'd as
    "请求的内容不存在" when clicked. None of these endpoints had coverage.
    """
    from app.modules.test_management.models import TestLogArtifact

    token = login_as(client, db_session, username="adminlog", role=UserRole.ADMIN)
    config = PipelineConfig(
        name="weekly",
        versions=["24.03-LTS-SP3"],
        archs=["aarch64"],
        config_data={"module_template_ids": [], "repo_base_url": "http://example.com"},
    )
    db_session.add(config)
    db_session.commit()
    run = PipelineRun(
        config_id=config.id,
        version="24.03-LTS-SP3",
        status="succeeded",
        triggered_by="adminlog",
    )
    db_session.add(run)
    db_session.flush()

    log_file = tmp_path / "ltp.txt"
    log_file.write_text("line1 TPASS\nline2 TFAIL\n", encoding="utf-8")
    file_art = TestLogArtifact(
        pipeline_run_id=run.id,
        job_id=999,
        module="kernel",
        arch="aarch64",
        artifact_type="module_log",
        artifact_name="ltp.txt",
        storage_path=str(log_file),
    )
    folder_dir = tmp_path / "ltp_results"
    (folder_dir / "LTP_RUN_ON.log").parent.mkdir(parents=True, exist_ok=True)
    (folder_dir / "LTP_RUN_ON.log").write_text("abort01 1 TPASS\n", encoding="utf-8")
    folder_art = TestLogArtifact(
        pipeline_run_id=run.id,
        job_id=999,
        module="kernel",
        arch="aarch64",
        artifact_type="pkg_folder",
        artifact_name="ltp_results",
        storage_path=str(folder_dir),
    )
    db_session.add_all([file_art, folder_art])
    db_session.flush()

    h = auth_headers(token)

    r = client.get(f"/api/v1/pipelines/runs/{run.id}/logs/{file_art.id}", headers=h)
    assert r.status_code == 200
    assert "line1" in r.json()["content"]

    r = client.get(f"/api/v1/pipelines/runs/{run.id}/logs/{folder_art.id}/files", headers=h)
    assert r.status_code == 200
    assert r.json()["files"] == ["LTP_RUN_ON.log"]

    r = client.get(
        f"/api/v1/pipelines/runs/{run.id}/logs/{folder_art.id}/files",
        headers=h,
        params={"path": "LTP_RUN_ON.log"},
    )
    assert r.status_code == 200
    assert "TPASS" in r.json()["content"]

    # Folder-file full download (streams the whole file, no 1 MB truncation).
    r = client.get(
        f"/api/v1/pipelines/runs/{run.id}/logs/{folder_art.id}/files/download",
        headers=h,
        params={"path": "LTP_RUN_ON.log"},
    )
    assert r.status_code == 200
    assert b"abort01 1 TPASS" in r.content

    # Folder-file download guards.
    assert (
        client.get(
            f"/api/v1/pipelines/runs/{run.id}/logs/{folder_art.id}/files/download",
            headers=h,
        ).status_code
        == 404  # no path
    )
    assert (
        client.get(
            f"/api/v1/pipelines/runs/{run.id}/logs/{folder_art.id}/files/download",
            headers=h,
            params={"path": "../../../etc/passwd"},
        ).status_code
        == 404  # traversal
    )
    assert (
        client.get(
            f"/api/v1/pipelines/runs/{run.id}/logs/{file_art.id}/files/download",
            headers=h,
            params={"path": "ltp.txt"},
        ).status_code
        == 404  # not a folder artifact
    )

    r = client.get(f"/api/v1/pipelines/runs/{run.id}/logs/{file_art.id}/download", headers=h)
    assert r.status_code == 200
    assert b"line2 TFAIL" in r.content

    r = client.get(f"/api/v1/pipelines/runs/other-run-id/logs/{file_art.id}", headers=h)
    assert r.status_code == 404


# --- RunJob cancel ---


def test_admin_can_cancel_running_runjob(
    client: TestClient, db_session: Session, seeded_pipeline_types: None,
    stub_run_job_queue: None,
) -> None:
    """ADMIN 对 running 状态的 RunJob 发起取消 → 202 + cancelling + cancel_requested。"""
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    h = auth_headers(token)

    run_job = PipelineRunJob(
        pipeline_run_id="r1", module_template_id="t1",
        arch="x86_64", env_type=None, status="running",
    )
    db_session.add(run_job)
    db_session.commit()

    r = client.post(f"/api/v1/pipelines/run-jobs/{run_job.id}/cancel", headers=h)
    assert r.status_code == 202
    assert r.json()["status"] == "cancelling"

    db_session.refresh(run_job)
    assert run_job.cancel_requested is True
    assert run_job.status == "cancelling"


def test_admin_cancel_of_pending_runjob_finishes_without_a_test_job(
    client: TestClient, db_session: Session, seeded_pipeline_types: None,
    stub_run_job_queue: None,
) -> None:
    """未被 worker 领取的 RunJob 取消后直接收敛，不能卡在 cancelling。"""
    token = login_as(client, db_session, username="admin", role=UserRole.ADMIN)
    run_job = PipelineRunJob(
        pipeline_run_id="r1", module_template_id="t1",
        arch="x86_64", env_type=None, status="pending",
    )
    db_session.add(run_job)
    db_session.commit()

    response = client.post(
        f"/api/v1/pipelines/run-jobs/{run_job.id}/cancel",
        headers=auth_headers(token),
    )

    assert response.status_code == 202
    assert response.json()["status"] == "cancelled"
    db_session.refresh(run_job)
    assert run_job.cancel_requested is True
    assert run_job.status == "cancelled"
    assert run_job.test_job_id is None

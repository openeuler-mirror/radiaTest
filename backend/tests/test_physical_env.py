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
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.credentials import encrypt_secret
from app.db.base import Base
from app.modules.leases.schemas import LeaseCreate
from app.modules.leases.service import create_lease
from app.modules.pipelines.models import TestModuleTemplate
from app.modules.resources.models import (
    ManagementStatus,
    OccupancyStatus,
    Resource,
    ResourceType,
)
from app.modules.resources.physical_install_models import PhysicalInstallImage
from app.modules.test_management.envs.physical import (
    create_env_node_physical,
)
from app.modules.test_management.errors import TestJobExecutionError
from app.modules.test_management.models import (
    TestEnvNode,
    TestEnvNodeStatus,
    TestEnvSet,
    TestJob,
)
from app.modules.users.models import UserRole
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


def _make_physical_resource(
    db: Session,
    *,
    code: str = "phys-001",
    arch: str = "aarch64",
    ip: str = "10.0.0.1",
    usage_scenario: str = "",
) -> Resource:
    resource = Resource(
        resource_code=code,
        resource_type=ResourceType.PHYSICAL.value,
        management_status=ManagementStatus.ACTIVE.value,
        occupancy_status=OccupancyStatus.IDLE.value,
        arch=arch,
        primary_ip=ip,
        ssh_username="root",
        ssh_password_ciphertext=encrypt_secret("pass123"),
        is_critical=False,
        tags=[],
        usage_scenario=usage_scenario,
    )
    db.add(resource)
    db.commit()
    return resource


def _occupy(db: Session, resource: Resource, user: object) -> None:
    create_lease(
        db,
        resource=resource,
        actor=user,
        payload=LeaseCreate(
            purpose="test",
            expected_ends_at=datetime.now(UTC) + timedelta(hours=8),
        ),
    )
    db.commit()


def _make_install_image(
    db: Session,
    *,
    os_version: str = "openEuler-24.03-LTS-SP3",
    arch: str = "aarch64",
) -> PhysicalInstallImage:
    image = PhysicalInstallImage(
        os_version=os_version,
        arch=arch,
        efi_url="http://h/efi.efi",
        repo_url="http://h/repo",
    )
    db.add(image)
    db.commit()
    return image


def _make_job_and_node(
    db: Session, *, arch: str = "aarch64"
) -> tuple[TestJob, TestEnvSet, TestEnvNode, object]:
    user = create_user(
        db, username="admin01", password="testpass", role=UserRole.ADMIN, display_name="admin"
    )
    db.commit()
    job = TestJob(
        creator_user_id=user.id,
        name="test-physical",
        status="preparing",
        framework="mugen",
        env_type="physical",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="20240101",
        arch=arch,
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_failed_env=True,
    )
    db.add(job)
    db.flush()
    env_set = TestEnvSet(
        job_id=job.id,
        set_index=0,
        status="creating_vms",
        node_num=1,
    )
    db.add(env_set)
    db.flush()
    node = TestEnvNode(
        env_set_id=env_set.id,
        node_index=0,
        role="control",
        status=TestEnvNodeStatus.PENDING.value,
    )
    db.add(node)
    db.commit()
    return job, env_set, node, user


def _make_kernel_physical_job(
    db: Session, *, arch: str = "aarch64", os_version: str = "24.03-LTS-SP3"
) -> tuple[TestJob, TestEnvSet, TestEnvNode, object]:
    """kernel 模块物理机 RunJob 链：template→config→execution→run→run_job→job。"""
    from app.modules.pipelines.models import (
        PipelineConfig,
        PipelineExecution,
        PipelineRun,
        PipelineRunJob,
    )

    user = create_user(
        db, username="admin02", password="testpass", role=UserRole.ADMIN, display_name="admin"
    )
    db.commit()
    template = TestModuleTemplate(
        name="kernel",
        display_name="Kernel LTP Test",
        suite_name="ltp",
        env_type="physical",
        result_parser="ltp",
        test_framework="mugen",
    )
    db.add(template)
    db.flush()
    config = PipelineConfig(
        name="cfg-k",
        pipeline_type="update",
        versions=[os_version],
        archs=[arch],
        config_data={"module_template_ids": [template.id], "repo_base_url": "http://e/r"},
        dist="openEuler",
        image_round="round-9",
    )
    db.add(config)
    db.flush()
    execution = PipelineExecution(
        config_id=config.id, triggered_by="admin", versions=[os_version], archs=[arch]
    )
    db.add(execution)
    db.flush()
    run = PipelineRun(
        config_id=config.id,
        execution_id=execution.id,
        version=os_version,
        status="pending",
        triggered_by="admin",
    )
    db.add(run)
    db.flush()
    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch=arch,
        env_type="physical",
        status="pending",
    )
    db.add(run_job)
    db.flush()
    job = TestJob(
        creator_user_id=user.id,
        name="test-kernel-physical",
        status="preparing",
        framework="mugen",
        env_type="physical",
        dist="openEuler",
        os_version=os_version,
        image_round="round-9",
        arch=arch,
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_failed_env=True,
        physical_usage_scenario="kernel-update",
        result_parser="ltp",
    )
    db.add(job)
    db.flush()
    env_set = TestEnvSet(job_id=job.id, set_index=0, status="creating_vms", node_num=1)
    db.add(env_set)
    db.flush()
    node = TestEnvNode(
        env_set_id=env_set.id,
        node_index=0,
        role="control",
        status=TestEnvNodeStatus.PENDING.value,
    )
    db.add(node)
    db.commit()
    return job, env_set, node, user


def test_create_env_node_physical_kernel_calls_install_latest(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """kernel + 非 -64k → PXE 成功后调 install_latest；成功 → node READY + kernel_version 设。"""
    resource = _make_physical_resource(db_session, usage_scenario="kernel-update")
    _make_install_image(db_session)
    job, env_set, node, user = _make_kernel_physical_job(db_session)

    _occupy(db_session, resource, user)

    monkeypatch.setattr("app.modules.vms.pxe_install.run_pxe_install", MagicMock(return_value=True))
    calls: list[str] = []

    def fake_install(*, os_version, resource, record_event):  # noqa: ANN001
        calls.append(os_version)
        resource.kernel_version = "5.10.0-foo.x86_64"

    monkeypatch.setattr("app.modules.vms.service.install_latest_kernel_via_ssh", fake_install)

    create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)

    assert calls == ["24.03-LTS-SP3"]
    assert node.status == TestEnvNodeStatus.READY.value
    assert resource.kernel_version == "5.10.0-foo.x86_64"


def test_create_env_node_physical_non_kernel_skips_install_latest(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """非 kernel 模块（无 pipeline 链，module_name=None）→ 不调 install_latest，node READY。"""
    resource = _make_physical_resource(db_session)
    _make_install_image(db_session)
    job, env_set, node, user = _make_job_and_node(db_session)
    _occupy(db_session, resource, user)

    monkeypatch.setattr("app.modules.vms.pxe_install.run_pxe_install", MagicMock(return_value=True))
    install_calls: list[int] = []
    monkeypatch.setattr(
        "app.modules.vms.service.install_latest_kernel_via_ssh",
        lambda *a, **k: install_calls.append(1),
    )

    create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)

    assert install_calls == []
    assert node.status == TestEnvNodeStatus.READY.value


def test_create_env_node_physical_64k_kernel_installs_before_ready(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """kernel + -64k 把目标版本交给 PXE 后处理，完成后才把节点标为 READY。"""
    resource = _make_physical_resource(db_session, usage_scenario="kernel-update")
    image = _make_install_image(db_session, os_version="openEuler-24.03-LTS-SP4")
    job, env_set, node, user = _make_kernel_physical_job(db_session, os_version="24.03-LTS-SP4-64k")
    _occupy(db_session, resource, user)

    pxe_calls: list[dict[str, object]] = []

    def fake_pxe_install(**kwargs: object) -> bool:
        assert node.status != TestEnvNodeStatus.READY.value
        pxe_calls.append(kwargs)
        return True

    monkeypatch.setattr("app.modules.vms.pxe_install.run_pxe_install", fake_pxe_install)
    install_calls: list[int] = []
    monkeypatch.setattr(
        "app.modules.vms.service.install_latest_kernel_via_ssh",
        lambda *a, **k: install_calls.append(1),
    )

    create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)

    assert install_calls == []
    assert pxe_calls == [
        {
            "resource_id": resource.id,
            "image_id": image.id,
            "actor_user_id": user.id,
            "target_os_version": "24.03-LTS-SP4-64k",
        }
    ]
    assert node.status == TestEnvNodeStatus.READY.value


def test_create_env_node_physical_64k_not_transferred_marks_node_not_executed(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """最新轮没有 64k 时节点不是 READY，也不作为机器故障处理。"""
    from app.modules.vms.service import Kernel64kNotTransferredError

    resource = _make_physical_resource(db_session, usage_scenario="kernel-update")
    _make_install_image(db_session, os_version="openEuler-24.03-LTS-SP4")
    job, env_set, node, user = _make_kernel_physical_job(db_session, os_version="24.03-LTS-SP4-64k")
    _occupy(db_session, resource, user)

    monkeypatch.setattr(
        "app.modules.vms.pxe_install.run_pxe_install",
        MagicMock(side_effect=Kernel64kNotTransferredError("not transferred")),
    )

    ready = create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)

    assert ready is False
    assert node.status == TestEnvNodeStatus.NOT_EXECUTED.value
    assert resource.management_status == ManagementStatus.ACTIVE.value


def test_create_env_node_physical_kernel_install_failure_marks_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """install_latest raise → node ERROR + resource DISABLED + raise kernel_install_failed。"""
    from app.modules.vms.service import LatestKernelInstallError

    resource = _make_physical_resource(db_session, usage_scenario="kernel-update")
    _make_install_image(db_session)
    job, env_set, node, user = _make_kernel_physical_job(db_session)
    _occupy(db_session, resource, user)

    monkeypatch.setattr("app.modules.vms.pxe_install.run_pxe_install", MagicMock(return_value=True))
    monkeypatch.setattr(
        "app.modules.vms.service.install_latest_kernel_via_ssh",
        MagicMock(side_effect=LatestKernelInstallError("boom")),
    )

    with pytest.raises(TestJobExecutionError) as exc_info:
        create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)
    assert exc_info.value.code == "kernel_install_failed"
    assert node.status == TestEnvNodeStatus.ERROR.value
    assert resource.management_status == ManagementStatus.DISABLED.value


def test_create_env_node_physical_rejects_other_users_resource(db_session: Session) -> None:
    resource = _make_physical_resource(db_session, code="phys-other", arch="aarch64")
    job, env_set, node, user = _make_job_and_node(db_session)
    other = create_user(
        db_session, username="other02", password="otherpass", role=UserRole.TSE, display_name="o"
    )
    db_session.commit()
    _occupy(db_session, resource, other)

    with pytest.raises(TestJobExecutionError) as exc_info:
        create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)
    assert exc_info.value.code == "physical_resource_unavailable"


def test_create_env_node_physical_waits_for_active_test_to_release_resource(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = _make_physical_resource(
        db_session,
        code="phys-queued",
        usage_scenario="kernel-update",
    )
    _make_install_image(db_session)
    job, env_set, node, user = _make_kernel_physical_job(db_session)
    _occupy(db_session, resource, user)

    blocking_job = TestJob(
        creator_user_id=user.id,
        name="blocking-physical-test",
        status="running",
        framework="mugen",
        env_type="physical",
        dist="openEuler",
        os_version="24.03-LTS-SP3",
        image_round="round-8",
        arch="aarch64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_failed_env=False,
        physical_usage_scenario="kernel-update",
    )
    blocking_env = TestEnvSet(
        job=blocking_job,
        set_index=0,
        status="running",
        node_num=1,
        env_type="physical",
    )
    TestEnvNode(
        env_set=blocking_env,
        node_index=0,
        role="control",
        status="ready",
        resource_id=resource.id,
        primary_ip=resource.primary_ip,
    )
    db_session.add(blocking_job)
    db_session.commit()

    waits: list[int] = []

    def release_after_wait(seconds: int) -> None:
        waits.append(seconds)
        blocking_job.status = "succeeded"
        db_session.commit()

    monkeypatch.setattr(
        "app.modules.test_management.envs.physical._sleep",
        release_after_wait,
        raising=False,
    )

    def run_after_release(**_kwargs: object) -> bool:
        assert waits == [60]
        return True

    monkeypatch.setattr(
        "app.modules.vms.pxe_install.run_pxe_install",
        run_after_release,
    )
    monkeypatch.setattr(
        "app.modules.vms.service.install_latest_kernel_via_ssh",
        lambda **_kwargs: None,
    )

    create_env_node_physical(
        db_session,
        job=job,
        env_set=env_set,
        node=node,
        actor=user,
    )

    assert node.resource_id == resource.id


def test_create_env_node_physical_reinstalls_and_sets_node(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = _make_physical_resource(db_session)
    image = _make_install_image(db_session)
    job, env_set, node, user = _make_job_and_node(db_session)
    _occupy(db_session, resource, user)

    fake = MagicMock(return_value=True)
    monkeypatch.setattr("app.modules.vms.pxe_install.run_pxe_install", fake)

    create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)

    assert node.resource_id == resource.id
    assert node.primary_ip == resource.primary_ip
    assert node.status == TestEnvNodeStatus.READY.value
    fake.assert_called_once_with(
        resource_id=resource.id,
        image_id=image.id,
        actor_user_id=user.id,
        target_os_version=job.os_version,
    )


def test_create_env_node_physical_raises_when_no_occupied(
    db_session: Session,
) -> None:
    _make_physical_resource(db_session, code="phys-idle", arch="aarch64")
    job, env_set, node, user = _make_job_and_node(db_session)

    with pytest.raises(TestJobExecutionError) as exc_info:
        create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)
    assert exc_info.value.code == "physical_resource_unavailable"


def test_create_env_node_physical_raises_when_no_image(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = _make_physical_resource(db_session)
    job, env_set, node, user = _make_job_and_node(db_session)
    _occupy(db_session, resource, user)
    # no install image created

    with pytest.raises(TestJobExecutionError) as exc_info:
        create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)
    assert exc_info.value.code == "install_image_unavailable"


def test_create_env_node_physical_raises_when_reinstall_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = _make_physical_resource(db_session)
    _make_install_image(db_session)
    job, env_set, node, user = _make_job_and_node(db_session)
    _occupy(db_session, resource, user)

    monkeypatch.setattr(
        "app.modules.vms.pxe_install.run_pxe_install", MagicMock(return_value=False)
    )

    with pytest.raises(TestJobExecutionError) as exc_info:
        create_env_node_physical(db_session, job=job, env_set=env_set, node=node, actor=user)
    assert exc_info.value.code == "pxe_reinstall_failed"
    assert node.status == TestEnvNodeStatus.ERROR.value

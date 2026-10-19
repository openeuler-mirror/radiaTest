# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import worker
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.leases.models import ResourceLease
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineRun,
    PipelineRunJob,
    TestModuleTemplate,
)
from app.modules.resources.models import (
    OccupancyStatus,
    Resource,
    ResourceType,
    VirtualResourceSpec,
)
from app.modules.tasks import recovery
from app.modules.tasks.models import TaskEvent
from app.modules.tasks.recovery import (
    RecoveryTaskType,
    RecoveryTrigger,
    recover_interrupted_tasks,
)
from app.modules.test_management.models import TEST_JOB_TIMEOUT
from app.modules.test_management.models import TestJob as DBTestJob
from app.modules.test_management.models import TestJobStatus as DBTestJobStatus
from app.modules.vms import service as vm_service
from app.modules.vms.execution_state import (
    get_vm_destroy_execution,
    mark_vm_destroy_queued,
    mark_vm_destroy_started,
)
from app.modules.vms.models import VMRequest, VMRequestStatus


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


def make_vm_request(
    *,
    status: VMRequestStatus,
    task_id: str | None,
    created_at: datetime,
) -> VMRequest:
    return VMRequest(
        requester_user_id="user-1",
        status=status.value,
        purpose="worker recovery test",
        expected_ends_at=created_at + timedelta(days=1),
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
        task_id=task_id,
        host_attempts=[],
        created_at=created_at,
        updated_at=created_at,
    )


def make_test_job(
    *,
    job_id: int,
    status: DBTestJobStatus,
    task_id: str,
    created_at: datetime,
) -> DBTestJob:
    return DBTestJob(
        id=job_id,
        creator_user_id="user-1",
        name=f"job-{job_id}",
        status=status.value,
        framework="mugen",
        env_type="vm",
        dist="openEuler",
        os_version="openEuler-24.03-LTS-SP4",
        image_round="round-9",
        arch="aarch64",
        mugen_commit_sha="abc123",
        env_set_num=1,
        keep_failed_env=False,
        task_id=task_id,
        created_at=created_at,
        updated_at=created_at,
    )


def make_vm_resource(*, code: str) -> Resource:
    return Resource(
        resource_code=code,
        resource_type=ResourceType.VIRTUAL.value,
        name=code,
        occupancy_status=OccupancyStatus.OCCUPIED.value,
        primary_ip="172.168.131.100",
        arch="aarch64",
        ssh_username="root",
        ssh_password_ciphertext="ciphertext",
        tags=[],
        extra={},
    )


def make_pipeline_run_job(
    db: Session,
    *,
    status: str,
    task_id: str | None,
    created_at: datetime,
) -> PipelineRunJob:
    # 名称后缀：有 task_id 用它保证唯一；无 task_id(孤儿分支用例)退到短随机串。
    suffix = task_id if task_id is not None else uuid4().hex[:8]
    template = TestModuleTemplate(
        name=f"module-{suffix}",
        display_name="Module",
        suite_name="suite",
    )
    config = PipelineConfig(
        name=f"config-{suffix}",
        versions=["openEuler-24.03-LTS-SP4"],
        archs=["aarch64"],
    )
    db.add_all([template, config])
    db.flush()
    run = PipelineRun(
        config_id=config.id,
        version="openEuler-24.03-LTS-SP4",
        triggered_by="user-1",
    )
    db.add(run)
    db.flush()
    run_job = PipelineRunJob(
        pipeline_run_id=run.id,
        module_template_id=template.id,
        arch="aarch64",
        status=status,
        task_id=task_id,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(run_job)
    db.flush()
    return run_job


def add_task_event(
    db: Session,
    *,
    task_type: RecoveryTaskType,
    subject_type: str,
    subject_id: str,
    task_id: str,
    phase: str,
    created_at: datetime,
) -> None:
    db.add(
        TaskEvent(
            task_type=task_type.value,
            subject_type=subject_type,
            subject_id=subject_id,
            celery_task_id=task_id,
            phase=phase,
            message=phase,
            created_at=created_at,
        )
    )


def test_worker_startup_recovers_pipeline_run_job_and_started_queued_vm(
    db_session: Session,
) -> None:
    as_of = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
    task_id = "pipeline-task"
    run_job = make_pipeline_run_job(
        db_session,
        status="running",
        task_id=task_id,
        created_at=as_of,
    )
    unstarted_run_job = make_pipeline_run_job(
        db_session,
        status="preparing",
        task_id="unstarted-pipeline-task",
        created_at=as_of,
    )
    queued_vm = make_vm_request(
        status=VMRequestStatus.QUEUED,
        task_id=task_id,
        created_at=as_of,
    )
    pending_test_job = make_test_job(
        job_id=10000,
        status=DBTestJobStatus.PENDING,
        task_id=task_id,
        created_at=as_of,
    )
    db_session.add_all([queued_vm, pending_test_job])
    db_session.flush()
    run_job.test_job_id = pending_test_job.id
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.PIPELINE_RUN_JOB,
        subject_type="runjob",
        subject_id=run_job.id,
        task_id=task_id,
        phase="started",
        created_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_CREATE,
        subject_type="vm_request",
        subject_id=queued_vm.id,
        task_id=task_id,
        phase="started",
        created_at=as_of,
    )
    db_session.commit()

    first = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.WORKER_STARTUP,
        task_types=(
            RecoveryTaskType.PIPELINE_RUN_JOB,
            RecoveryTaskType.TEST_JOB,
            RecoveryTaskType.VM_CREATE,
        ),
        as_of=as_of,
    )

    db_session.refresh(run_job)
    db_session.refresh(unstarted_run_job)
    db_session.refresh(queued_vm)
    db_session.refresh(pending_test_job)
    assert first.recovered[RecoveryTaskType.PIPELINE_RUN_JOB] == 1
    assert first.recovered[RecoveryTaskType.TEST_JOB] == 1
    assert first.recovered[RecoveryTaskType.VM_CREATE] == 1
    assert run_job.status == "error"
    assert unstarted_run_job.status == "preparing"
    assert queued_vm.status == VMRequestStatus.FAILED.value
    assert queued_vm.error_code == "worker_interrupted"
    assert pending_test_job.status == DBTestJobStatus.ERROR.value

    second = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.WORKER_STARTUP,
        task_types=(
            RecoveryTaskType.PIPELINE_RUN_JOB,
            RecoveryTaskType.TEST_JOB,
            RecoveryTaskType.VM_CREATE,
        ),
        as_of=as_of,
    )
    assert second.total == 0


@pytest.mark.parametrize(
    "trigger",
    [RecoveryTrigger.WORKER_STARTUP, RecoveryTrigger.LAZY_READ],
)
def test_recovery_cancels_interrupted_cancelling_run_job_and_test_job(
    db_session: Session,
    trigger: RecoveryTrigger,
) -> None:
    """取消已持久化时，恢复不能把 RunJob/TestJob 误标为 error。"""
    as_of = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    created_at = (
        as_of - TEST_JOB_TIMEOUT - timedelta(seconds=1)
        if trigger == RecoveryTrigger.LAZY_READ
        else as_of
    )
    task_id = "cancelling-pipeline-task"
    run_job = make_pipeline_run_job(
        db_session,
        status="cancelling",
        task_id=task_id,
        created_at=created_at,
    )
    test_job = make_test_job(
        job_id=10002,
        status=DBTestJobStatus.RUNNING,
        task_id=task_id,
        created_at=created_at,
    )
    run_job.cancel_requested = True
    run_job.test_job_id = test_job.id
    test_job.cancel_requested = True
    db_session.add(test_job)
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.PIPELINE_RUN_JOB,
        subject_type="runjob",
        subject_id=run_job.id,
        task_id=task_id,
        phase="started",
        created_at=created_at,
    )
    db_session.commit()

    summary = recover_interrupted_tasks(
        db_session,
        trigger=trigger,
        task_types=(
            RecoveryTaskType.PIPELINE_RUN_JOB,
            RecoveryTaskType.TEST_JOB,
        ),
        as_of=as_of,
    )

    db_session.refresh(run_job)
    db_session.refresh(test_job)
    assert summary.recovered[RecoveryTaskType.PIPELINE_RUN_JOB] == 1
    assert summary.recovered[RecoveryTaskType.TEST_JOB] == 1
    assert run_job.status == "cancelled"
    assert test_job.status == DBTestJobStatus.CANCELLED.value
    assert test_job.error_code is None


@pytest.mark.parametrize(
    "trigger",
    [RecoveryTrigger.WORKER_STARTUP, RecoveryTrigger.LAZY_READ],
)
def test_recovery_recovers_stale_queued_vm_destroy_but_keeps_recent_one(
    db_session: Session,
    trigger: RecoveryTrigger,
) -> None:
    """仅清理超过宿主脚本时限且没有 started 记录的 VM 销毁锁。"""
    as_of = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    stale = make_vm_resource(code="vm-destroy-queued-stale")
    recent = make_vm_resource(code="vm-destroy-queued-recent")
    timeout = timedelta(seconds=recovery.get_settings().vm_host_script_timeout_seconds)
    db_session.add_all([stale, recent])
    db_session.flush()
    mark_vm_destroy_queued(
        stale,
        task_id="destroy-queued-stale",
        enqueued_at=as_of - timeout - timedelta(seconds=1),
    )
    mark_vm_destroy_queued(
        recent,
        task_id="destroy-queued-recent",
        enqueued_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_DESTROY,
        subject_type="resource",
        subject_id=stale.id,
        task_id="destroy-queued-stale",
        phase="queued",
        created_at=as_of - timeout - timedelta(seconds=1),
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_DESTROY,
        subject_type="resource",
        subject_id=recent.id,
        task_id="destroy-queued-recent",
        phase="queued",
        created_at=as_of,
    )
    db_session.commit()

    summary = recover_interrupted_tasks(
        db_session,
        trigger=trigger,
        task_types=(RecoveryTaskType.VM_DESTROY,),
        as_of=as_of,
    )

    db_session.refresh(stale)
    db_session.refresh(recent)
    assert summary.recovered[RecoveryTaskType.VM_DESTROY] == 1
    assert get_vm_destroy_execution(stale) is None
    assert stale.extra["last_destroy_error"]["code"] == (
        "worker_interrupted" if trigger == RecoveryTrigger.WORKER_STARTUP else "timeout"
    )
    assert get_vm_destroy_execution(recent) is not None


def _make_host_resource(*, code: str, ip: str) -> Resource:
    return Resource(
        resource_code=code,
        resource_type=ResourceType.PHYSICAL.value,
        name=code,
        occupancy_status=OccupancyStatus.IDLE.value,
        primary_ip=ip,
        arch="aarch64",
        ssh_username="root",
        ssh_password_ciphertext="ciphertext",
        tags=["vm-host"],
        extra={},
    )


def test_recovery_finalizes_stale_vm_destroy_when_host_confirms_missing(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """恢复回读宿主确认 VM 已消失(记账中断的典型残留)时，自动落账收敛而非仅清锁。"""
    as_of = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    timeout = timedelta(seconds=recovery.get_settings().vm_host_script_timeout_seconds)
    host = _make_host_resource(code="vm-host-finalize", ip="172.168.131.20")
    stale = make_vm_resource(code="vm-destroy-finalize")
    db_session.add_all([host, stale])
    db_session.flush()
    stale.virtual_spec = VirtualResourceSpec(
        vm_name="vm-destroy-finalize",
        host_resource_id=host.id,
        system_disk_path="/var/lib/libvirt/images/kronos/instances/vm.qcow2",
        data_disk_paths=[],
    )
    lease = ResourceLease(
        resource_id=stale.id,
        user_id="user-1",
        purpose="联调",
        starts_at=as_of - timedelta(days=1),
        expected_ends_at=as_of + timedelta(days=1),
    )
    db_session.add(lease)
    db_session.flush()
    stale.current_lease_id = lease.id
    mark_vm_destroy_started(
        stale,
        task_id="destroy-finalize",
        started_at=as_of - timeout - timedelta(seconds=1),
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_DESTROY,
        subject_type="resource",
        subject_id=stale.id,
        task_id="destroy-finalize",
        phase="destroy_started",
        created_at=as_of - timeout - timedelta(seconds=1),
    )
    db_session.commit()

    def fake_run_host_script(**kwargs: object) -> object:
        assert kwargs["script_name"] == "inspect-vm.sh"
        return {
            "status": "success",
            "domain_exists": False,
            "power_state": None,
            "system_disk_exists": False,
            "data_disks_existing": [],
        }

    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)

    summary = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_DESTROY,),
        as_of=as_of,
    )

    db_session.refresh(stale)
    db_session.refresh(lease)
    assert summary.recovered[RecoveryTaskType.VM_DESTROY] == 1
    assert get_vm_destroy_execution(stale) is None
    assert stale.deleted_at is not None
    assert stale.occupancy_status == OccupancyStatus.IDLE.value
    assert lease.released_at is not None
    succeeded = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.task_type == "vm_destroy",
                TaskEvent.subject_id == stale.id,
                TaskEvent.phase == "destroy_succeeded",
            )
        )
        .scalars()
        .first()
    )
    assert succeeded is not None
    assert "宿主" in succeeded.message


def test_recovery_keeps_interrupt_semantics_when_host_still_has_vm(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """恢复回读发现宿主上 VM 仍在时，维持"清锁可重试、不删 VM 本体"的既有取舍。"""
    as_of = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    timeout = timedelta(seconds=recovery.get_settings().vm_host_script_timeout_seconds)
    host = _make_host_resource(code="vm-host-keep", ip="172.168.131.21")
    stale = make_vm_resource(code="vm-destroy-keep")
    db_session.add_all([host, stale])
    db_session.flush()
    stale.virtual_spec = VirtualResourceSpec(
        vm_name="vm-destroy-keep",
        host_resource_id=host.id,
        system_disk_path="/var/lib/libvirt/images/kronos/instances/vm.qcow2",
        data_disk_paths=[],
    )
    mark_vm_destroy_started(
        stale,
        task_id="destroy-keep",
        started_at=as_of - timeout - timedelta(seconds=1),
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_DESTROY,
        subject_type="resource",
        subject_id=stale.id,
        task_id="destroy-keep",
        phase="destroy_started",
        created_at=as_of - timeout - timedelta(seconds=1),
    )
    db_session.commit()

    def fake_run_host_script(**kwargs: object) -> object:
        assert kwargs["script_name"] == "inspect-vm.sh"
        return {
            "status": "success",
            "domain_exists": True,
            "power_state": "running",
            "system_disk_exists": True,
            "data_disks_existing": [],
        }

    monkeypatch.setattr(vm_service, "run_host_script", fake_run_host_script)

    summary = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_DESTROY,),
        as_of=as_of,
    )

    db_session.refresh(stale)
    assert summary.recovered[RecoveryTaskType.VM_DESTROY] == 1
    assert get_vm_destroy_execution(stale) is None
    assert stale.deleted_at is None
    assert stale.extra["last_destroy_error"]["code"] == "timeout"
    interrupted = (
        db_session.execute(
            select(TaskEvent).where(
                TaskEvent.task_type == "vm_destroy",
                TaskEvent.subject_id == stale.id,
                TaskEvent.phase == "destroy_interrupted",
            )
        )
        .scalars()
        .first()
    )
    assert interrupted is not None


def test_worker_startup_recovers_started_tasks_and_ignores_queued_tasks(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    as_of = datetime(2026, 7, 25, 3, 0, tzinfo=UTC)
    started_vm = make_vm_request(
        status=VMRequestStatus.CREATING,
        task_id="vm-started",
        created_at=as_of,
    )
    queued_vm = make_vm_request(
        status=VMRequestStatus.PENDING,
        task_id="vm-queued",
        created_at=as_of,
    )
    started_job = make_test_job(
        job_id=10000,
        status=DBTestJobStatus.PREPARING,
        task_id="job-started",
        created_at=as_of,
    )
    queued_job = make_test_job(
        job_id=10001,
        status=DBTestJobStatus.PENDING,
        task_id="job-queued",
        created_at=as_of,
    )
    started_destroy = make_vm_resource(code="vm-destroy-started")
    queued_destroy = make_vm_resource(code="vm-destroy-queued")
    db_session.add_all(
        [
            started_vm,
            queued_vm,
            started_job,
            queued_job,
            started_destroy,
            queued_destroy,
        ]
    )
    db_session.flush()

    mark_vm_destroy_queued(
        started_destroy,
        task_id="destroy-started",
        enqueued_at=as_of,
    )
    mark_vm_destroy_started(
        started_destroy,
        task_id="destroy-started",
        started_at=as_of,
    )
    mark_vm_destroy_queued(
        queued_destroy,
        task_id="destroy-queued",
        enqueued_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_CREATE,
        subject_type="vm_request",
        subject_id=started_vm.id,
        task_id="vm-started",
        phase="started",
        created_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.TEST_JOB,
        subject_type="test_job",
        subject_id=str(started_job.id),
        task_id="job-started",
        phase="started",
        created_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.MUGEN_SYNC,
        subject_type="mugen_sync",
        subject_id="mugen",
        task_id="mugen-started",
        phase="started",
        created_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.MUGEN_SYNC,
        subject_type="mugen_sync",
        subject_id="mugen",
        task_id="mugen-queued",
        phase="queued",
        created_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_DESTROY,
        subject_type="resource",
        subject_id=started_destroy.id,
        task_id="destroy-started",
        phase="destroy_started",
        created_at=as_of,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_DESTROY,
        subject_type="resource",
        subject_id=queued_destroy.id,
        task_id="destroy-queued",
        phase="queued",
        created_at=as_of,
    )
    db_session.commit()

    released_tokens: list[str] = []
    monkeypatch.setattr(
        recovery,
        "_release_mugen_sync_lock",
        released_tokens.append,
    )

    summary = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.WORKER_STARTUP,
        as_of=as_of,
    )

    db_session.refresh(started_vm)
    db_session.refresh(queued_vm)
    db_session.refresh(started_job)
    db_session.refresh(queued_job)
    db_session.refresh(started_destroy)
    db_session.refresh(queued_destroy)
    assert summary.total == 4
    assert started_vm.status == VMRequestStatus.FAILED.value
    assert started_vm.error_code == "worker_interrupted"
    assert queued_vm.status == VMRequestStatus.PENDING.value
    assert started_job.status == DBTestJobStatus.ERROR.value
    assert started_job.error_code == "worker_interrupted"
    assert queued_job.status == DBTestJobStatus.PENDING.value
    assert get_vm_destroy_execution(started_destroy) is None
    assert get_vm_destroy_execution(queued_destroy) is not None
    assert released_tokens == ["mugen-started"]

    recovery_events = list(
        db_session.execute(
            select(TaskEvent).where(TaskEvent.error_code == "worker_interrupted")
        ).scalars()
    )
    assert len(recovery_events) == 4
    assert db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == "worker.recover_interrupted_task")
    ) == 4

    second = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.WORKER_STARTUP,
        as_of=as_of,
    )
    assert second.total == 0
    assert released_tokens == ["mugen-started"]
    assert db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == "worker.recover_interrupted_task")
    ) == 4


def test_lazy_recovery_uses_each_task_deadline(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    as_of = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    old_time = as_of - timedelta(hours=16)
    recent_time = as_of - timedelta(minutes=5)
    stale_vm = make_vm_request(
        status=VMRequestStatus.QUEUED,
        task_id="vm-stale",
        created_at=old_time,
    )
    recent_vm = make_vm_request(
        status=VMRequestStatus.QUEUED,
        task_id="vm-recent",
        created_at=recent_time,
    )
    stale_job = make_test_job(
        job_id=10000,
        status=DBTestJobStatus.RUNNING,
        task_id="job-stale",
        created_at=old_time,
    )
    stale_destroy = make_vm_resource(code="vm-destroy-stale")
    stale_run_job = make_pipeline_run_job(
        db_session,
        status="running",
        task_id="pipeline-stale",
        created_at=old_time,
    )
    linked_recent_job = make_test_job(
        job_id=10001,
        status=DBTestJobStatus.RUNNING,
        task_id="pipeline-stale",
        created_at=recent_time,
    )
    stale_run_job.test_job_id = linked_recent_job.id
    recent_run_job = make_pipeline_run_job(
        db_session,
        status="running",
        task_id="pipeline-recent",
        created_at=recent_time,
    )
    db_session.add_all(
        [stale_vm, recent_vm, stale_job, linked_recent_job, stale_destroy]
    )
    db_session.flush()
    mark_vm_destroy_started(
        stale_destroy,
        task_id="destroy-stale",
        started_at=old_time,
    )
    for request, created_at in (
        (stale_vm, old_time),
        (recent_vm, recent_time),
    ):
        add_task_event(
            db_session,
            task_type=RecoveryTaskType.VM_CREATE,
            subject_type="vm_request",
            subject_id=request.id,
            task_id=request.task_id or "",
            phase="started",
            created_at=created_at,
        )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.TEST_JOB,
        subject_type="test_job",
        subject_id=str(stale_job.id),
        task_id="job-stale",
        phase="started",
        created_at=old_time,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.MUGEN_SYNC,
        subject_type="mugen_sync",
        subject_id="mugen",
        task_id="mugen-stale",
        phase="started",
        created_at=old_time,
    )
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.VM_DESTROY,
        subject_type="resource",
        subject_id=stale_destroy.id,
        task_id="destroy-stale",
        phase="destroy_started",
        created_at=old_time,
    )
    for run_job, created_at in (
        (stale_run_job, old_time),
        (recent_run_job, recent_time),
    ):
        add_task_event(
            db_session,
            task_type=RecoveryTaskType.PIPELINE_RUN_JOB,
            subject_type="runjob",
            subject_id=run_job.id,
            task_id=run_job.task_id or "",
            phase="started",
            created_at=created_at,
        )
    db_session.commit()

    released_tokens: list[str] = []
    monkeypatch.setattr(
        recovery,
        "_release_mugen_sync_lock",
        released_tokens.append,
    )

    summary = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.LAZY_READ,
        as_of=as_of,
    )

    db_session.refresh(stale_vm)
    db_session.refresh(recent_vm)
    db_session.refresh(stale_job)
    db_session.refresh(linked_recent_job)
    db_session.refresh(stale_destroy)
    db_session.refresh(stale_run_job)
    db_session.refresh(recent_run_job)
    assert summary.total == 6
    assert stale_vm.error_code == "stale_creating"
    assert recent_vm.status == VMRequestStatus.QUEUED.value
    assert stale_job.error_code == "task_timeout"
    assert linked_recent_job.error_code == "task_timeout"
    assert get_vm_destroy_execution(stale_destroy) is None
    assert stale_run_job.status == "error"
    assert recent_run_job.status == "running"
    assert stale_destroy.extra["last_destroy_error"] == {
        "code": "timeout",
        "message": "VM 销毁超过最长执行时间，锁定已清除",
    }
    assert released_tokens == ["mugen-stale"]
    assert db_session.scalar(
        select(func.count())
        .select_from(TaskEvent)
        .where(TaskEvent.error_code == "mugen_sync_failed")
    ) == 1


def test_worker_startup_recovery_failure_does_not_escape(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_session() -> Session:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(worker, "SessionLocal", fail_session)

    with caplog.at_level(logging.ERROR, logger="kronos.worker"):
        worker.recover_worker_tasks()

    assert "Worker startup recovery failed" in caplog.text


def test_mugen_recovery_rolls_back_when_lock_cannot_be_released(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    as_of = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    add_task_event(
        db_session,
        task_type=RecoveryTaskType.MUGEN_SYNC,
        subject_type="mugen_sync",
        subject_id="mugen",
        task_id="mugen-started",
        phase="started",
        created_at=as_of - timedelta(hours=1),
    )
    db_session.commit()

    def fail_release(_token: str) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(recovery, "_release_mugen_sync_lock", fail_release)

    failed = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.WORKER_STARTUP,
        as_of=as_of,
    )

    assert failed.recovered.get(RecoveryTaskType.MUGEN_SYNC) is None
    assert failed.failed_task_types == (RecoveryTaskType.MUGEN_SYNC,)
    assert db_session.scalar(
        select(func.count())
        .select_from(TaskEvent)
        .where(
            TaskEvent.task_type == RecoveryTaskType.MUGEN_SYNC.value,
            TaskEvent.phase == "failed",
        )
    ) == 0
    assert db_session.scalar(select(func.count()).select_from(AuditLog)) == 0

    released: list[str] = []
    monkeypatch.setattr(recovery, "_release_mugen_sync_lock", released.append)
    recovered = recover_interrupted_tasks(
        db_session,
        trigger=RecoveryTrigger.WORKER_STARTUP,
        as_of=as_of,
    )

    assert recovered.recovered[RecoveryTaskType.MUGEN_SYNC] == 1
    assert released == ["mugen-started"]

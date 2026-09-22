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
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import and_, exists, or_, select, tuple_
from sqlalchemy.orm import Session, aliased

from app.core.config import get_settings
from app.modules.resources.models import Resource
from app.modules.tasks.models import TaskEvent
from app.modules.tasks.service import get_latest_task_event, record_task_recovery
from app.modules.test_management.models import (
    TEST_JOB_TIMEOUT,
    TestJob,
    TestJobStatus,
)
from app.modules.vms.execution_state import (
    clear_vm_destroy_execution,
    get_vm_destroy_execution,
)
from app.modules.vms.models import VMRequest, VMRequestStatus

logger = logging.getLogger("kronos.worker_recovery")

# VM 创建超过 60 分钟视为中断，懒读触发时据此判定 creating 状态过期。
VM_CREATE_TIMEOUT = timedelta(minutes=60)


class RecoveryTrigger(StrEnum):
    """恢复触发来源：WORKER_STARTUP(进程启动时全量扫)或 LAZY_READ(读取时顺手收敛)。"""

    WORKER_STARTUP = "worker_startup"
    LAZY_READ = "lazy_read"


class RecoveryTaskType(StrEnum):
    """可恢复的异步任务类型，各自有独立超时阈值与终态。"""

    VM_CREATE = "vm_create"
    VM_DESTROY = "vm_destroy"
    MUGEN_SYNC = "mugen_sync"
    TEST_JOB = "test_job"
    PIPELINE_RUN_JOB = "pipeline_runjob"


@dataclass(frozen=True)
class RecoverySummary:
    recovered: dict[RecoveryTaskType, int] = field(default_factory=dict)
    failed_task_types: tuple[RecoveryTaskType, ...] = ()

    @property
    def total(self) -> int:
        return sum(self.recovered.values())


@dataclass(frozen=True)
class _RecoveryOutcome:
    count: int
    mugen_lock_tokens: tuple[str, ...] = ()


_RecoveryHandler = Callable[[Session, RecoveryTrigger, datetime], _RecoveryOutcome]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalized(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _latest_event(
    db: Session,
    *,
    task_type: RecoveryTaskType,
    subject_type: str,
    subject_id: str,
    celery_task_id: str,
) -> TaskEvent | None:
    return get_latest_task_event(
        db,
        task_type=task_type.value,
        subject_type=subject_type,
        subject_id=subject_id,
        celery_task_id=celery_task_id,
    )


@dataclass(frozen=True)
class RecoveryEventDraft:
    """恢复事件输入：恢复编排函数传给 _record_recovery 的参数集合。"""

    task_type: RecoveryTaskType
    subject_type: str
    subject_id: str
    celery_task_id: str
    phase: str
    trigger: RecoveryTrigger
    before_status: str
    after_status: str
    error_code: str
    message: str
    last_event: TaskEvent | None
    detail: dict[str, object] | None = None


def _record_recovery(
    db: Session,
    *,
    event: RecoveryEventDraft,
) -> None:
    """记录恢复事件：同时写 task_event(供详情页)与 audit_log(供审计)。

    恢复不删除原始 started 事件，只追加 failed/destroy_interrupted 等终态
    事件，保留中断前的最后阶段与宿主信息便于排查。
    """
    record_task_recovery(
        db,
        recovery=TaskRecoveryDraft(
            task_type=event.task_type.value,
            subject_type=event.subject_type,
            subject_id=event.subject_id,
            celery_task_id=event.celery_task_id,
            phase=event.phase,
            trigger=event.trigger.value,
            before_status=event.before_status,
            after_status=event.after_status,
            error_code=event.error_code,
            message=event.message,
            last_event=event.last_event,
            detail=event.detail,
        ),
    )


def _recovery_error(
    trigger: RecoveryTrigger,
    *,
    lazy_code: str,
    startup_message: str,
    lazy_message: str,
) -> tuple[str, str]:
    if trigger == RecoveryTrigger.WORKER_STARTUP:
        return "worker_interrupted", startup_message
    return lazy_code, lazy_message


def _vm_host_attempts_summary(request: VMRequest) -> list[dict[str, object]]:
    keys = ("host_resource_id", "host_ip", "attempt", "status", "error_code")
    return [
        {key: attempt[key] for key in keys if attempt.get(key) is not None}
        for attempt in request.host_attempts
    ]


def _recover_vm_creates(
    db: Session,
    trigger: RecoveryTrigger,
    as_of: datetime,
) -> _RecoveryOutcome:
    conditions = [
        VMRequest.status.in_(
            [VMRequestStatus.CREATING.value, VMRequestStatus.QUEUED.value]
        ),
        VMRequest.task_id.is_not(None),
    ]
    started_conditions = [
        TaskEvent.task_type == RecoveryTaskType.VM_CREATE.value,
        TaskEvent.subject_type == "vm_request",
        TaskEvent.subject_id == VMRequest.id,
        TaskEvent.celery_task_id == VMRequest.task_id,
        TaskEvent.phase == "started",
    ]
    if trigger == RecoveryTrigger.LAZY_READ:
        started_conditions.append(TaskEvent.created_at <= as_of - VM_CREATE_TIMEOUT)
    conditions.append(exists(select(TaskEvent.id).where(*started_conditions)))
    requests = list(
        db.execute(
            select(VMRequest).where(*conditions).with_for_update(skip_locked=True)
        ).scalars()
    )
    # 孤儿分支：task_id 为 NULL 说明申请从未成功派发，其 started 事件也带不上
    # celery 身份，上面的 EXISTS 恒不命中。超时基准改用 VMRequest.created_at，
    # 且两种触发都要求超过 VM_CREATE_TIMEOUT，避免与"正在提交"的写入窗口竞态。
    orphans = list(
        db.execute(
            select(VMRequest)
            .where(
                VMRequest.task_id.is_(None),
                VMRequest.status.in_(
                    [
                        VMRequestStatus.PENDING.value,
                        VMRequestStatus.CREATING.value,
                        VMRequestStatus.QUEUED.value,
                    ]
                ),
                VMRequest.created_at <= as_of - VM_CREATE_TIMEOUT,
            )
            .with_for_update(skip_locked=True)
        ).scalars()
    )
    error_code, message = _recovery_error(
        trigger,
        lazy_code="stale_creating",
        startup_message="Worker 异常退出，VM 创建状态已标记失败",
        lazy_message="VM 创建超过 60 分钟，已标记失败",
    )

    def _fail(request: VMRequest, *, code: str, msg: str, celery_task_id: str) -> None:
        before_status = request.status
        last_event = _latest_event(
            db,
            task_type=RecoveryTaskType.VM_CREATE,
            subject_type="vm_request",
            subject_id=request.id,
            celery_task_id=celery_task_id,
        )
        request.status = VMRequestStatus.FAILED.value
        request.error_code = code
        request.error_message = msg
        request.completed_at = as_of
        attempts = _vm_host_attempts_summary(request)
        _record_recovery(
            db,
            event=RecoveryEventDraft(
            task_type=RecoveryTaskType.VM_CREATE,
            subject_type="vm_request",
            subject_id=request.id,
            celery_task_id=celery_task_id,
            phase="failed",
            trigger=trigger,
            before_status=before_status,
            after_status=VMRequestStatus.FAILED.value,
            error_code=code,
            message=msg,
            last_event=last_event,
            detail={"host_attempts": attempts} if attempts else None,
            ),
        )

    for request in requests:
        if request.task_id is None:
            raise RuntimeError("恢复数据缺少任务 ID")
        _fail(request, code=error_code, msg=message, celery_task_id=request.task_id)
    for request in orphans:
        _fail(
            request,
            code="orphaned_no_task",
            msg="申请从未成功派发(无 task_id)，已回收为失败",
            celery_task_id="",
        )
    return _RecoveryOutcome(count=len(requests) + len(orphans))


def _recover_pipeline_run_jobs(
    db: Session,
    trigger: RecoveryTrigger,
    as_of: datetime,
) -> _RecoveryOutcome:
    from app.modules.pipelines.service import recover_interrupted_run_jobs

    return _RecoveryOutcome(
        count=recover_interrupted_run_jobs(
            db,
            trigger=trigger.value,
            as_of=as_of,
            timeout=TEST_JOB_TIMEOUT,
        )
    )


def _recover_test_jobs(
    db: Session,
    trigger: RecoveryTrigger,
    as_of: datetime,
) -> _RecoveryOutcome:
    from app.modules.pipelines.service import list_recoverable_pipeline_test_job_keys

    active_status = TestJob.status.in_(
        [
            TestJobStatus.PREPARING.value,
            TestJobStatus.RUNNING.value,
        ]
    )
    pipeline_test_job_keys = list_recoverable_pipeline_test_job_keys(
        db,
        trigger=trigger.value,
        as_of=as_of,
        timeout=TEST_JOB_TIMEOUT,
    )
    pipeline_pending = and_(
        TestJob.status.in_(
            [
                TestJobStatus.PENDING.value,
                TestJobStatus.PREPARING.value,
                TestJobStatus.RUNNING.value,
            ]
        ),
        tuple_(TestJob.id, TestJob.task_id).in_(pipeline_test_job_keys),
    )
    if trigger == RecoveryTrigger.LAZY_READ:
        active_status = and_(
            active_status,
            TestJob.created_at <= as_of - TEST_JOB_TIMEOUT,
        )
    conditions = [
        or_(active_status, pipeline_pending),
        TestJob.task_id.is_not(None),
    ]
    jobs = list(
        db.execute(select(TestJob).where(*conditions).with_for_update(skip_locked=True)).scalars()
    )
    error_code, message = _recovery_error(
        trigger,
        lazy_code="task_timeout",
        startup_message="Worker 异常退出，测试任务已标记异常",
        lazy_message="测试任务超过 15 小时总超时，已标记异常",
    )
    for job in jobs:
        if job.task_id is None:
            raise RuntimeError("恢复数据缺少任务 ID")
        last_event = _latest_event(
            db,
            task_type=RecoveryTaskType.TEST_JOB,
            subject_type="test_job",
            subject_id=str(job.id),
            celery_task_id=job.task_id,
        )
        before_status = job.status
        cancelled = job.cancel_requested
        after_status = TestJobStatus.CANCELLED.value if cancelled else TestJobStatus.ERROR.value
        recovery_code = "worker_interrupted_during_cancellation" if cancelled else error_code
        recovery_message = "Worker 异常退出，取消中的测试任务已收敛" if cancelled else message
        job.status = after_status
        job.error_code = None if cancelled else error_code
        job.error_message = None if cancelled else message
        job.completed_at = as_of
        _record_recovery(
            db,
            event=RecoveryEventDraft(
            task_type=RecoveryTaskType.TEST_JOB,
            subject_type="test_job",
            subject_id=str(job.id),
            celery_task_id=job.task_id,
            phase="cancelled" if cancelled else "error",
            trigger=trigger,
            before_status=before_status,
            after_status=after_status,
            error_code=recovery_code,
            message=recovery_message,
            last_event=last_event,
            ),
        )
    return _RecoveryOutcome(count=len(jobs))


@dataclass(frozen=True)
class UnfinishedEventQuery:
    """未完成事件的查询条件。"""

    task_type: RecoveryTaskType
    started_phase: str
    terminal_phases: Collection[str]
    trigger: RecoveryTrigger
    cutoff: datetime


def _unfinished_started_events(
    db: Session,
    *,
    query: UnfinishedEventQuery,
) -> list[TaskEvent]:
    task_type = query.task_type
    started_phase = query.started_phase
    terminal_phases = query.terminal_phases
    trigger = query.trigger
    cutoff = query.cutoff
    """找出"已 started 但之后无终态"的未完成事件。

    用 NOT EXISTS 子查询检查 started 之后是否出现过任一终态事件；
    with_for_update(skip_locked) 跳过被其他事务锁定的行，避免恢复并发阻塞。
    LAZY_READ 时额外要求 started 早于 cutoff，只收超时任务，启动触发则全收。
    """
    started = aliased(TaskEvent)
    terminal = aliased(TaskEvent)
    terminal_exists = exists(
        select(terminal.id).where(
            terminal.task_type == task_type.value,
            terminal.celery_task_id == started.celery_task_id,
            terminal.phase.in_(terminal_phases),
            terminal.created_at >= started.created_at,
        )
    )
    conditions = [
        started.task_type == task_type.value,
        started.phase == started_phase,
        started.celery_task_id.is_not(None),
        ~terminal_exists,
    ]
    if trigger == RecoveryTrigger.LAZY_READ:
        conditions.append(started.created_at <= cutoff)
    return list(
        db.execute(
            select(started).where(*conditions).with_for_update(skip_locked=True)
        ).scalars()
    )


def _recover_mugen_syncs(
    db: Session,
    trigger: RecoveryTrigger,
    as_of: datetime,
) -> _RecoveryOutcome:
    timeout = timedelta(seconds=get_settings().mugen_sync_lock_ttl_seconds)
    started_events = _unfinished_started_events(
                         db,
                         query=UnfinishedEventQuery(
                         task_type=RecoveryTaskType.MUGEN_SYNC,
                         started_phase="started",
                         terminal_phases=("succeeded", "failed"),
                         trigger=trigger,
                         cutoff=as_of - timeout,
                         ),
                     )
    error_code, message = _recovery_error(
        trigger,
        lazy_code="mugen_sync_failed",
        startup_message="Worker 异常退出，Mugen 用例同步已标记失败",
        lazy_message="Mugen 用例同步超过 30 分钟，已标记失败",
    )
    for started in started_events:
        if started.celery_task_id is None:
            raise RuntimeError("恢复数据缺少任务 ID")
        last_event = _latest_event(
            db,
            task_type=RecoveryTaskType.MUGEN_SYNC,
            subject_type=started.subject_type,
            subject_id=started.subject_id,
            celery_task_id=started.celery_task_id,
        )
        _record_recovery(
            db,
            event=RecoveryEventDraft(
            task_type=RecoveryTaskType.MUGEN_SYNC,
            subject_type=started.subject_type,
            subject_id=started.subject_id,
            celery_task_id=started.celery_task_id,
            phase="failed",
            trigger=trigger,
            before_status="started",
            after_status="failed",
            error_code=error_code,
            message=message,
            last_event=last_event,
            ),
        )
    return _RecoveryOutcome(
        count=len(started_events),
        mugen_lock_tokens=tuple(
            event.celery_task_id
            for event in started_events
            if event.celery_task_id is not None
        ),
    )


def _recover_vm_destroys(
    db: Session,
    trigger: RecoveryTrigger,
    as_of: datetime,
) -> _RecoveryOutcome:
    """恢复中断的 VM 销毁：先回读宿主事实，再决定收敛落账或清锁可重试。

    销毁不像创建那样可直接判失败——默认只清锁让租约可重试释放，不删除 VM
    本体(可能仍在运行)。回读宿主确认 VM 与磁盘均已不存在(如脚本已删但记账
    中断)时，才按宿主事实自动落账收敛。LAZY_READ 时按宿主脚本超时阈值判定，
    未超时则跳过。
    """
    # 延迟导入避免 tasks ↔ vms 循环依赖(与 _release_mugen_sync_lock 同理)。
    from app.modules.vms.service import (
        finalize_destroy_by_host_fact,
        host_confirms_vm_gone,
        inspect_vm_host_state,
    )

    timeout = timedelta(seconds=get_settings().vm_host_script_timeout_seconds)
    started_events = _unfinished_started_events(
                         db,
                         query=UnfinishedEventQuery(
                         task_type=RecoveryTaskType.VM_DESTROY,
                         started_phase="destroy_started",
                         terminal_phases=(
            "destroy_succeeded",
            "destroy_failed",
            "host_script_failed",
            "destroy_interrupted",
        ),
                         trigger=trigger,
                         cutoff=as_of - timeout,
                         ),
                     )
    queued_events = _unfinished_started_events(
                        db,
                        query=UnfinishedEventQuery(
                        task_type=RecoveryTaskType.VM_DESTROY,
                        started_phase="queued",
                        terminal_phases=(
            "destroy_started",
            "destroy_succeeded",
            "destroy_failed",
            "host_script_failed",
            "destroy_interrupted",
        ),
                        trigger=trigger,
                        cutoff=as_of - timeout,
                        ),
                    )
    error_code, message = _recovery_error(
        trigger,
        lazy_code="timeout",
        startup_message="Worker 异常退出，VM 销毁锁定已清除",
        lazy_message="VM 销毁超过最长执行时间，锁定已清除",
    )
    recovered = 0
    for started in started_events:
        if started.celery_task_id is None:
            raise RuntimeError("恢复数据缺少任务 ID")
        resource = (
            db.execute(
                select(Resource)
                .where(Resource.id == started.subject_id, Resource.deleted_at.is_(None))
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .one_or_none()
        )
        if resource is None:
            continue
        execution = get_vm_destroy_execution(resource)
        if execution is None or execution.task_id != started.celery_task_id:
            continue
        started_at = execution.started_at or started.created_at
        if (
            trigger == RecoveryTrigger.LAZY_READ
            and _normalized(started_at) > as_of - timeout
        ):
            continue
        # 回读宿主事实：确认 VM 与磁盘均不存在才落账收敛；仍在则走清锁可重试。
        inspect_result = inspect_vm_host_state(db, resource)
        if host_confirms_vm_gone(inspect_result):
            finalize_destroy_by_host_fact(
                db,
                resource=resource,
                task_id=started.celery_task_id,
                source=f"恢复({trigger.value})回读",
            )
            recovered += 1
            continue
        last_event = _latest_event(
            db,
            task_type=RecoveryTaskType.VM_DESTROY,
            subject_type=started.subject_type,
            subject_id=started.subject_id,
            celery_task_id=started.celery_task_id,
        )
        clear_vm_destroy_execution(
            resource,
            error={"code": error_code, "message": message},
        )
        _record_recovery(
            db,
            event=RecoveryEventDraft(
            task_type=RecoveryTaskType.VM_DESTROY,
            subject_type=started.subject_type,
            subject_id=started.subject_id,
            celery_task_id=started.celery_task_id,
            phase="destroy_interrupted",
            trigger=trigger,
            before_status="destroy_started",
            after_status="retryable",
            error_code=error_code,
            message=message,
            last_event=last_event,
            ),
        )
        recovered += 1
    for queued in queued_events:
        if queued.celery_task_id is None:
            raise RuntimeError("恢复数据缺少任务 ID")
        resource = (
            db.execute(
                select(Resource)
                .where(Resource.id == queued.subject_id, Resource.deleted_at.is_(None))
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .one_or_none()
        )
        if resource is None:
            continue
        execution = get_vm_destroy_execution(resource)
        if (
            execution is None
            or execution.task_id != queued.celery_task_id
            or execution.started_at is not None
        ):
            continue
        enqueued_at = execution.enqueued_at or queued.created_at
        if _normalized(enqueued_at) > as_of - timeout:
            continue
        # 回读宿主事实：入队从未执行时 VM 一般仍在，回读确认消失才落账收敛。
        inspect_result = inspect_vm_host_state(db, resource)
        if host_confirms_vm_gone(inspect_result):
            finalize_destroy_by_host_fact(
                db,
                resource=resource,
                task_id=queued.celery_task_id,
                source=f"恢复({trigger.value})回读",
            )
            recovered += 1
            continue
        last_event = _latest_event(
            db,
            task_type=RecoveryTaskType.VM_DESTROY,
            subject_type=queued.subject_type,
            subject_id=queued.subject_id,
            celery_task_id=queued.celery_task_id,
        )
        clear_vm_destroy_execution(
            resource,
            error={"code": error_code, "message": message},
        )
        _record_recovery(
            db,
            event=RecoveryEventDraft(
            task_type=RecoveryTaskType.VM_DESTROY,
            subject_type=queued.subject_type,
            subject_id=queued.subject_id,
            celery_task_id=queued.celery_task_id,
            phase="destroy_interrupted",
            trigger=trigger,
            before_status="queued",
            after_status="retryable",
            error_code=error_code,
            message=message,
            last_event=last_event,
            ),
        )
        recovered += 1
    return _RecoveryOutcome(count=recovered)


def _release_mugen_sync_lock(token: str) -> None:
    """释放 Mugen 同步锁。延迟导入避免与 test_management 循环依赖。"""
    from app.modules.test_management.service import release_mugen_sync_lock

    release_mugen_sync_lock(token)


# 各任务类型的恢复处理器。恢复按类型独立提交，单个失败不影响其他类型。
_HANDLERS: dict[RecoveryTaskType, _RecoveryHandler] = {
    RecoveryTaskType.VM_CREATE: _recover_vm_creates,
    RecoveryTaskType.VM_DESTROY: _recover_vm_destroys,
    RecoveryTaskType.MUGEN_SYNC: _recover_mugen_syncs,
    RecoveryTaskType.TEST_JOB: _recover_test_jobs,
    RecoveryTaskType.PIPELINE_RUN_JOB: _recover_pipeline_run_jobs,
}


def recover_interrupted_tasks(
    db: Session,
    *,
    trigger: RecoveryTrigger,
    task_types: Collection[RecoveryTaskType] | None = None,
    as_of: datetime | None = None,
) -> RecoverySummary:
    """按任务类型依次恢复中断任务，返回每类恢复数与失败类型列表。

    每类独立提交：某类抛错则回滚该类、记日志并继续下一类，不整体失败。
    mugen_sync 恢复后还要释放对应的同步锁令牌。
    """
    selected = tuple(task_types) if task_types is not None else tuple(_HANDLERS)
    current_time = _normalized(as_of or _utc_now())
    recovered: dict[RecoveryTaskType, int] = {}
    failed: list[RecoveryTaskType] = []

    for task_type in selected:
        try:
            outcome = _HANDLERS[task_type](db, trigger, current_time)
            for token in outcome.mugen_lock_tokens:
                _release_mugen_sync_lock(token)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            failed.append(task_type)
            logger.exception(
                "Worker task recovery failed: trigger=%s task_type=%s",
                trigger.value,
                task_type.value,
            )
            continue

        recovered[task_type] = outcome.count

    return RecoverySummary(
        recovered=recovered,
        failed_task_types=tuple(dict.fromkeys(failed)),
    )

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, tuple_
from sqlalchemy.orm import Session

from app.modules.audit.service import record_audit_log
from app.modules.tasks.models import TaskEvent

# 任务事件领域服务：追加写入事件轨迹并按主体查询。事件只追加不覆盖，
# 保留历史执行事实，供详情页与中断恢复使用。


@dataclass(frozen=True)
class TaskEventDraft:
    """任务事件草稿：record_task_event 的入参集合。"""

    task_type: str
    subject_type: str
    subject_id: str
    phase: str
    message: str
    celery_task_id: str | None = None
    level: str = "info"
    host_resource_id: str | None = None
    host_ip: str | None = None
    error_code: str | None = None


def record_task_event(
    db: Session,
    *,
    draft: TaskEventDraft,
) -> TaskEvent:
    task_type = draft.task_type
    subject_type = draft.subject_type
    subject_id = draft.subject_id
    phase = draft.phase
    message = draft.message
    celery_task_id = draft.celery_task_id
    level = draft.level
    host_resource_id = draft.host_resource_id
    host_ip = draft.host_ip
    error_code = draft.error_code
    """追加一条任务事件并 flush 取 id。不提交，由调用方控制事务。"""
    event = TaskEvent(
        task_type=task_type,
        subject_type=subject_type,
        subject_id=subject_id,
        celery_task_id=celery_task_id,
        level=level,
        phase=phase,
        message=message,
        host_resource_id=host_resource_id,
        host_ip=host_ip,
        error_code=error_code,
    )
    db.add(event)
    db.flush()
    return event


def get_latest_task_event(
    db: Session,
    *,
    task_type: str,
    subject_type: str,
    subject_id: str,
    celery_task_id: str,
) -> TaskEvent | None:
    """返回指定执行身份的最新任务事件。"""
    return (
        db.execute(
            select(TaskEvent)
            .where(
                TaskEvent.task_type == task_type,
                TaskEvent.subject_type == subject_type,
                TaskEvent.subject_id == subject_id,
                TaskEvent.celery_task_id == celery_task_id,
            )
            .order_by(TaskEvent.created_at.desc(), TaskEvent.id.desc())
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )


def filter_started_task_keys(
    db: Session,
    *,
    task_type: str,
    subject_type: str,
    candidates: Collection[tuple[str, str]],
    started_before: datetime | None = None,
) -> set[tuple[str, str]]:
    """从候选执行身份中返回存在 started 事件的 `(subject_id, celery_task_id)`。"""
    if not candidates:
        return set()
    conditions = [
        TaskEvent.task_type == task_type,
        TaskEvent.subject_type == subject_type,
        TaskEvent.phase == "started",
        TaskEvent.celery_task_id.is_not(None),
        tuple_(TaskEvent.subject_id, TaskEvent.celery_task_id).in_(candidates),
    ]
    if started_before is not None:
        conditions.append(TaskEvent.created_at <= started_before)
    rows = db.execute(
        select(TaskEvent.subject_id, TaskEvent.celery_task_id).where(*conditions)
    ).all()
    return {(subject_id, task_id) for subject_id, task_id in rows if task_id is not None}


@dataclass(frozen=True)
class TaskRecoveryDraft:
    """恢复事件草稿：record_task_recovery 的入参集合。"""

    task_type: str
    subject_type: str
    subject_id: str
    celery_task_id: str
    phase: str
    trigger: str
    before_status: str
    after_status: str
    error_code: str
    message: str
    last_event: TaskEvent | None
    detail: dict[str, object] | None = None


def record_task_recovery(
    db: Session,
    *,
    recovery: TaskRecoveryDraft,
) -> None:
    task_type = recovery.task_type
    subject_type = recovery.subject_type
    subject_id = recovery.subject_id
    celery_task_id = recovery.celery_task_id
    phase = recovery.phase
    trigger = recovery.trigger
    before_status = recovery.before_status
    after_status = recovery.after_status
    error_code = recovery.error_code
    message = recovery.message
    last_event = recovery.last_event
    detail = recovery.detail
    """追加恢复事件和系统审计，保留中断前最后阶段与宿主信息。"""
    last_phase = last_event.phase if last_event is not None else "unknown"
    host_ip = last_event.host_ip if last_event is not None else None
    event_message = (
        f"{message}；Celery task {celery_task_id}，最后阶段 {last_phase}"
        f"{f'，最后宿主 {host_ip}' if host_ip else ''}"
    )
    record_task_event(
        db,
        draft=TaskEventDraft(
            task_type=task_type,
            subject_type=subject_type,
            subject_id=subject_id,
            celery_task_id=celery_task_id,
            phase=phase,
            message=event_message,
            level="error",
            host_resource_id=last_event.host_resource_id if last_event is not None else None,
            host_ip=host_ip,
            error_code=error_code,
        ),
    )
    audit_detail: dict[str, object] = {
        "trigger": trigger,
        "task_type": task_type,
        "celery_task_id": celery_task_id,
        "last_phase": last_phase,
        "reason": message,
        "before_status": before_status,
        "after_status": after_status,
    }
    if last_event is not None and last_event.host_resource_id:
        audit_detail["last_host_resource_id"] = last_event.host_resource_id
    if host_ip:
        audit_detail["last_host_ip"] = host_ip
    if detail:
        audit_detail.update(detail)
    record_audit_log(
        db,
        actor_user_id=None,
        action="worker.recover_interrupted_task",
        target_type=subject_type,
        target_id=subject_id,
        detail=audit_detail,
    )


def list_task_events(
    db: Session,
    *,
    subject_type: str,
    subject_id: str,
) -> list[TaskEvent]:
    statement = (
        select(TaskEvent)
        .where(TaskEvent.subject_type == subject_type, TaskEvent.subject_id == subject_id)
        .order_by(TaskEvent.created_at.asc(), TaskEvent.id.asc())
    )
    return list(db.execute(statement).scalars().all())


def cleanup_task_events(db: Session, *, days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = db.execute(delete(TaskEvent).where(TaskEvent.created_at < cutoff))
    return result.rowcount or 0

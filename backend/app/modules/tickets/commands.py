# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Callable

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.notifications.service import (
    TicketNotificationState,
    notify_ticket_change,
    notify_ticket_comment,
)
from app.modules.tickets.errors import (
    TicketConflictError,
    TicketPermissionError,
    TicketValidationError,
    TicketVersionConflictError,
)
from app.modules.tickets.models import Ticket, TicketComment, TicketStatus
from app.modules.tickets.schemas import (
    TicketAccept,
    TicketCommentCreate,
    TicketContentUpdate,
    TicketCreate,
    TicketDetailRead,
    TicketHandlingUpdate,
    TicketReject,
)
from app.modules.tickets.service import (
    get_ticket,
    normalize_datetime,
    now_utc,
    serialize_ticket,
)
from app.modules.users.models import User, UserRole

# 工单命令层：每个 *_command 是一个事务——执行状态转换/鉴权后提交并返回详情。
# 状态转换统一走 _update_in_status 的乐观并发守卫；受理/拒绝/完成/处理更新在
# 转换前用 TicketNotificationState.capture 快照，供 notifications 模块 diff。

TicketOperation = Callable[[], Ticket]


def _execute_detail(db: Session, operation: TicketOperation) -> TicketDetailRead:
    """执行一个工单操作并在成功时提交、失败时回滚，统一返回带评论的详情。"""
    try:
        ticket = operation()
        db.commit()
        db.refresh(ticket)
        return serialize_ticket(db, ticket, include_comments=True)
    except Exception:
        db.rollback()
        raise


def create_ticket_command(
    db: Session,
    *,
    actor: User,
    payload: TicketCreate,
) -> TicketDetailRead:
    return _execute_detail(db, lambda: _create_ticket(db, actor=actor, payload=payload))


def update_ticket_content_command(
    db: Session,
    *,
    ticket_id: int,
    actor: User,
    payload: TicketContentUpdate,
) -> TicketDetailRead:
    return _execute_detail(
        db,
        lambda: _update_ticket_content(
            db,
            ticket=get_ticket(db, ticket_id),
            actor=actor,
            payload=payload,
        ),
    )


def accept_ticket_command(
    db: Session,
    *,
    ticket_id: int,
    actor: User,
    payload: TicketAccept,
) -> TicketDetailRead:
    return _execute_detail(
        db,
        lambda: _accept_ticket(
            db,
            ticket=get_ticket(db, ticket_id),
            actor=actor,
            payload=payload,
        ),
    )


def reject_ticket_command(
    db: Session,
    *,
    ticket_id: int,
    actor: User,
    payload: TicketReject,
) -> TicketDetailRead:
    return _execute_detail(
        db,
        lambda: _reject_ticket(
            db,
            ticket=get_ticket(db, ticket_id),
            actor=actor,
            payload=payload,
        ),
    )


def update_ticket_handling_command(
    db: Session,
    *,
    ticket_id: int,
    actor: User,
    payload: TicketHandlingUpdate,
) -> TicketDetailRead:
    return _execute_detail(
        db,
        lambda: _update_ticket_handling(
            db,
            ticket=get_ticket(db, ticket_id),
            actor=actor,
            payload=payload,
        ),
    )


def complete_ticket_command(
    db: Session,
    *,
    ticket_id: int,
    actor: User,
) -> TicketDetailRead:
    return _execute_detail(
        db,
        lambda: _complete_ticket(
            db,
            ticket=get_ticket(db, ticket_id),
            actor=actor,
        ),
    )


def add_ticket_comment_command(
    db: Session,
    *,
    ticket_id: int,
    actor: User,
    payload: TicketCommentCreate,
) -> TicketDetailRead:
    return _execute_detail(
        db,
        lambda: _add_ticket_comment(
            db,
            ticket=get_ticket(db, ticket_id),
            actor=actor,
            payload=payload,
        ),
    )


def _create_ticket(db: Session, *, actor: User, payload: TicketCreate) -> Ticket:
    ticket = Ticket(
        submitter_user_id=actor.id,
        ticket_type=payload.ticket_type.value,
        title=payload.title,
        body=payload.body,
        status=TicketStatus.PENDING.value,
    )
    db.add(ticket)
    db.flush()
    return ticket


def _update_ticket_content(
    db: Session,
    *,
    ticket: Ticket,
    actor: User,
    payload: TicketContentUpdate,
) -> Ticket:
    """
    编辑工单标题/正文。权限边界：管理员不可编辑(避免改用户意图)，只有
    提出人本人可改，且仅 PENDING 状态可改，受理后内容冻结。
    """
    if actor.role == UserRole.ADMIN.value:
        raise TicketPermissionError("管理员不能编辑工单内容")
    if ticket.submitter_user_id != actor.id:
        raise TicketPermissionError("只有提出人可以编辑工单内容")
    if ticket.status != TicketStatus.PENDING.value:
        raise TicketConflictError("只有待处理工单可以编辑")
    values = {
        field: getattr(payload, field)
        for field in payload.model_fields_set
        if field in {"title", "body"}
    }
    values["updated_at"] = now_utc()
    _update_in_status(
        db,
        ticket=ticket,
        expected_status=TicketStatus.PENDING,
        values=values,
    )
    return ticket


def _require_admin(actor: User) -> None:
    """受理/拒绝/完成/调整处理信息的鉴权入口，仅 ADMIN 可执行。"""
    if actor.role != UserRole.ADMIN.value:
        raise TicketPermissionError("仅管理员可以执行此操作")


def _get_active_admin(db: Session, user_id: str) -> User:
    """校验责任人必须是启用状态的管理员，防止指派给无权处理的人。"""
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.ADMIN.value or not user.is_active:
        raise TicketValidationError("责任人必须是启用状态的管理员")
    return user


def _accept_ticket(
    db: Session,
    *,
    ticket: Ticket,
    actor: User,
    payload: TicketAccept,
) -> Ticket:
    _require_admin(actor)
    before = TicketNotificationState.capture(ticket)
    _get_active_admin(db, payload.assignee_user_id)
    planned_completion_at = normalize_datetime(payload.planned_completion_at)
    if planned_completion_at <= now_utc():
        raise TicketValidationError("完成时间必须晚于当前时间")
    _update_in_status(
        db,
        ticket=ticket,
        expected_status=TicketStatus.PENDING,
        values={
            "status": TicketStatus.ACCEPTED.value,
            "priority": payload.priority.value,
            "assignee_user_id": payload.assignee_user_id,
            "planned_completion_at": planned_completion_at,
            "updated_at": now_utc(),
        },
    )
    notify_ticket_change(db, ticket=ticket, actor=actor, before=before)
    return ticket


def _reject_ticket(
    db: Session,
    *,
    ticket: Ticket,
    actor: User,
    payload: TicketReject,
) -> Ticket:
    _require_admin(actor)
    before = TicketNotificationState.capture(ticket)
    _update_in_status(
        db,
        ticket=ticket,
        expected_status=TicketStatus.PENDING,
        values={
            "status": TicketStatus.REJECTED.value,
            "rejection_reason": f"[{actor.username}] {payload.reason}",
            "updated_at": now_utc(),
        },
    )
    notify_ticket_change(db, ticket=ticket, actor=actor, before=before)
    return ticket


def _update_ticket_handling(
    db: Session,
    *,
    ticket: Ticket,
    actor: User,
    payload: TicketHandlingUpdate,
) -> Ticket:
    _require_admin(actor)
    before = TicketNotificationState.capture(ticket)
    values: dict[str, object] = {}
    if "priority" in payload.model_fields_set:
        values["priority"] = payload.priority.value
    if "assignee_user_id" in payload.model_fields_set:
        _get_active_admin(db, payload.assignee_user_id)
        values["assignee_user_id"] = payload.assignee_user_id
    if "planned_completion_at" in payload.model_fields_set:
        values["planned_completion_at"] = normalize_datetime(payload.planned_completion_at)
    values["updated_at"] = now_utc()
    _update_in_status(
        db,
        ticket=ticket,
        expected_status=TicketStatus.ACCEPTED,
        values=values,
    )
    notify_ticket_change(db, ticket=ticket, actor=actor, before=before)
    return ticket


def _complete_ticket(db: Session, *, ticket: Ticket, actor: User) -> Ticket:
    _require_admin(actor)
    before = TicketNotificationState.capture(ticket)
    completed_at = now_utc()
    _update_in_status(
        db,
        ticket=ticket,
        expected_status=TicketStatus.ACCEPTED,
        values={
            "status": TicketStatus.COMPLETED.value,
            "completed_at": completed_at,
            "updated_at": completed_at,
        },
    )
    notify_ticket_change(db, ticket=ticket, actor=actor, before=before)
    return ticket


def _add_ticket_comment(
    db: Session,
    *,
    ticket: Ticket,
    actor: User,
    payload: TicketCommentCreate,
) -> Ticket:
    """追加评论。权限：管理员、提出人或现任责任人均可评论，其余拒绝。"""
    if (
        actor.role != UserRole.ADMIN.value
        and actor.id != ticket.submitter_user_id
        and actor.id != ticket.assignee_user_id
    ):
        raise TicketPermissionError("不能评论此工单")
    comment = TicketComment(
        ticket_id=ticket.id,
        author_user_id=actor.id,
        body=payload.body,
    )
    db.add(comment)
    db.flush()
    notify_ticket_comment(db, ticket=ticket, comment=comment, actor=actor)
    return ticket


def _update_in_status(
    db: Session,
    *,
    ticket: Ticket,
    expected_status: TicketStatus,
    values: dict[str, object],
) -> None:
    """乐观并发状态守卫：仅当工单当前状态等于 expected_status 时才更新。

    UPDATE ... WHERE status = expected_status，若 rowcount != 1 说明工单已被
    其他并发操作改变状态，抛 TicketVersionConflictError，避免状态跳变。
    """
    result = db.execute(
        update(Ticket)
        .where(Ticket.id == ticket.id, Ticket.status == expected_status.value)
        .values(**values)
    )
    if result.rowcount != 1:
        raise TicketVersionConflictError("工单已被其他操作更新")
    db.expire(ticket)
    db.refresh(ticket)

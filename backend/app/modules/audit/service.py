# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PAGE_SIZE, PageParams
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogListParams, AuditLogRead
from app.modules.users.models import User


def record_audit_log(
    db: Session,
    *,
    actor_user_id: str | None,
    action: str,
    target_type: str,
    target_id: str | None,
    detail: dict[str, object] | None = None,
) -> AuditLog:
    """追加一条审计日志。审计日志只增不删，用于行为回溯和合规取证。"""
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
    )
    db.add(log)
    db.flush()
    return log


def list_audit_logs(
    db: Session,
    *,
    params: AuditLogListParams,
    pagination: PageParams,
) -> tuple[list[AuditLogRead], int]:
    """分页查询审计日志，按创建时间倒序，返回 (条目列表, 总数)。"""
    conditions = []
    if params.action:
        conditions.append(AuditLog.action.ilike(f"%{params.action}%"))
    if params.target_type:
        conditions.append(AuditLog.target_type.ilike(f"%{params.target_type}%"))
    if params.started_at:
        conditions.append(AuditLog.created_at >= params.started_at)
    if params.ended_at:
        conditions.append(AuditLog.created_at <= params.ended_at)
    if params.actor_username:
        conditions.append(User.username.ilike(f"%{params.actor_username}%"))

    base_statement = select(AuditLog, User.username).outerjoin(
        User,
        AuditLog.actor_user_id == User.id,
    )
    if conditions:
        base_statement = base_statement.where(and_(*conditions))
    statement = (
        base_statement.order_by(AuditLog.created_at.desc(), AuditLog.id)
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    count_statement = select(func.count(AuditLog.id)).outerjoin(
        User,
        AuditLog.actor_user_id == User.id,
    )
    if conditions:
        count_statement = count_statement.where(and_(*conditions))

    rows = db.execute(statement).all()
    items = [
        AuditLogRead(
            id=log.id,
            actor_user_id=log.actor_user_id,
            actor_username=username,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            detail=log.detail,
            created_at=log.created_at,
        )
        for log, username in rows
    ]
    total = db.scalar(count_statement) or 0
    return items, total

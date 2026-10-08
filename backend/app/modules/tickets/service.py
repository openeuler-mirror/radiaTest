# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.pagination import PAGE_SIZE, PageParams
from app.modules.tickets.errors import (
    TicketNotFoundError,
)
from app.modules.tickets.models import (
    Ticket,
    TicketComment,
    TicketPriority,
    TicketStatus,
)
from app.modules.tickets.schemas import (
    TicketCommentRead,
    TicketDetailRead,
    TicketListParams,
    TicketRead,
)
from app.modules.users.models import User

# 工单领域服务：序列化、分页筛选与逾期判定。状态转换与鉴权在 commands 层，
# 本模块只做只读聚合。


def now_utc() -> datetime:
    return datetime.now(UTC)


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def user_label_data(prefix: str, user: User | None) -> dict[str, object]:
    return {
        f"{prefix}_user_id": user.id if user else None,
        f"{prefix}_username": user.username if user else None,
        f"{prefix}_display_name": user.display_name if user else None,
    }


def ticket_read_data(
    ticket: Ticket,
    *,
    submitter: User | None,
    assignee: User | None,
) -> dict[str, object]:
    """
    组装工单序列化数据。is_overdue 仅对已受理且有计划完成时间的工单判定，
    用于列表/详情的高亮提示，不参与状态机。
    """
    return {
        **ticket.__dict__,
        **user_label_data("submitter", submitter),
        **user_label_data("assignee", assignee),
        "is_overdue": bool(
            ticket.status == TicketStatus.ACCEPTED.value
            and ticket.planned_completion_at
            and normalize_datetime(ticket.planned_completion_at) < now_utc()
        ),
    }


def serialize_ticket(
    db: Session,
    ticket: Ticket,
    *,
    include_comments: bool = False,
) -> TicketRead | TicketDetailRead:
    submitter = db.get(User, ticket.submitter_user_id)
    assignee = db.get(User, ticket.assignee_user_id) if ticket.assignee_user_id else None
    data = ticket_read_data(ticket, submitter=submitter, assignee=assignee)
    if not include_comments:
        return TicketRead.model_validate(data)

    comments = list(
        db.execute(
            select(TicketComment)
            .where(TicketComment.ticket_id == ticket.id)
            .order_by(TicketComment.created_at, TicketComment.id)
        )
        .scalars()
        .all()
    )
    author_ids = {comment.author_user_id for comment in comments}
    authors = {}
    for user in (
        db.execute(select(User).where(User.id.in_(author_ids)))
        .scalars()
        .all()
    ):
        authors[user.id] = user
    comment_reads: list[TicketCommentRead] = []
    for comment in comments:
        author = authors.get(comment.author_user_id)
        if author is None:
            raise KeyError(comment.author_user_id)
        comment_reads.append(
            TicketCommentRead(
                id=comment.id,
                author_user_id=comment.author_user_id,
                author_username=author.username,
                author_display_name=author.display_name,
                body=comment.body,
                created_at=comment.created_at,
            )
        )
    data["comments"] = comment_reads
    return TicketDetailRead.model_validate(data)


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise TicketNotFoundError(ticket_id)
    return ticket


def paginate_tickets(
    db: Session,
    *,
    params: TicketListParams,
    pagination: PageParams,
) -> tuple[list[TicketRead], int]:
    """分页查询工单。filters 按 match(and/or) 组合；优先级 priority 取
    TicketPriority 枚举值，特殊值 "UNSET" 表示筛选未设优先级的工单。
    返回 (条目列表, 总数)。
    """
    submitter = aliased(User)
    assignee = aliased(User)
    filters = []
    if params.ticket_id is not None:
        filters.append(Ticket.id == params.ticket_id)
    if params.submitter:
        filters.append(
            or_(
                submitter.username.ilike(f"%{params.submitter}%"),
                submitter.display_name.ilike(f"%{params.submitter}%"),
            )
        )
    if params.title:
        filters.append(Ticket.title.ilike(f"%{params.title}%"))
    if params.ticket_type:
        filters.append(Ticket.ticket_type == params.ticket_type.value)
    if params.status:
        filters.append(Ticket.status == params.status.value)
    if params.priority == "UNSET":
        filters.append(Ticket.priority.is_(None))
    elif isinstance(params.priority, TicketPriority):
        filters.append(Ticket.priority == params.priority.value)
    if params.assignee:
        filters.append(
            or_(
                assignee.username.ilike(f"%{params.assignee}%"),
                assignee.display_name.ilike(f"%{params.assignee}%"),
            )
        )

    condition = None
    if filters:
        condition = or_(*filters) if params.match == "or" else and_(*filters)
    statement = (
        select(Ticket, submitter, assignee)
        .join(submitter, Ticket.submitter_user_id == submitter.id)
        .outerjoin(assignee, Ticket.assignee_user_id == assignee.id)
    )
    count_statement = (
        select(func.count(Ticket.id))
        .join(submitter, Ticket.submitter_user_id == submitter.id)
        .outerjoin(assignee, Ticket.assignee_user_id == assignee.id)
    )
    if condition is not None:
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    statement = statement.order_by(Ticket.id.desc()).offset(pagination.offset).limit(PAGE_SIZE)
    rows = db.execute(statement).all()
    items = [
        TicketRead.model_validate(
            ticket_read_data(ticket, submitter=submitter_user, assignee=assignee_user)
        )
        for ticket, submitter_user, assignee_user in rows
    ]
    return items, db.scalar(count_statement) or 0

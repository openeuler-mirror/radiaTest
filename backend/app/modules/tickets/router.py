# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.api_runtime import APIError
from app.core.pagination import PageParams, PageResponse, get_page_params
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.tickets.commands import (
    accept_ticket_command,
    add_ticket_comment_command,
    complete_ticket_command,
    create_ticket_command,
    reject_ticket_command,
    update_ticket_content_command,
    update_ticket_handling_command,
)
from app.modules.tickets.errors import (
    TicketConflictError,
    TicketError,
    TicketNotFoundError,
    TicketPermissionError,
    TicketValidationError,
    TicketVersionConflictError,
)
from app.modules.tickets.models import TicketPriority, TicketStatus, TicketType
from app.modules.tickets.schemas import (
    TicketAccept,
    TicketCommentCreate,
    TicketContentUpdate,
    TicketCreate,
    TicketDetailRead,
    TicketHandlingUpdate,
    TicketListParams,
    TicketRead,
    TicketReject,
)
from app.modules.tickets.service import get_ticket, paginate_tickets, serialize_ticket
from app.modules.users.models import User

# 工单路由：薄层，只做请求解析、鉴权入口与异常→HTTP 状态码映射，
# 业务规则与状态转换在 commands 层。所有端点经 run_ticket_endpoint 统一捕获
# TicketError 子类并映射。

router = APIRouter(prefix="/tickets", tags=["tickets"])


def raise_ticket_error(exc: Exception) -> None:
    """把工单领域异常映射为统一 APIError：404/403/400/409(版本或状态冲突)。"""
    if isinstance(exc, TicketNotFoundError):
        raise APIError(
            status_code=404,
            code="not_found",
            message="工单不存在",
        ) from exc
    if isinstance(exc, TicketPermissionError):
        raise APIError(
            status_code=403,
            code="forbidden",
            message=f"没有操作权限：{exc}",
        ) from exc
    if isinstance(exc, TicketValidationError):
        raise APIError(
            status_code=400,
            code="bad_request",
            message=f"请求参数错误：{exc}",
        ) from exc
    if isinstance(exc, TicketVersionConflictError):
        raise APIError(
            status_code=409,
            code="ticket_version_conflict",
            message=str(exc),
        ) from exc
    if isinstance(exc, TicketConflictError):
        raise APIError(
            status_code=409,
            code="ticket_state_conflict",
            message=f"工单状态冲突：{exc}",
        ) from exc
    raise exc


def run_ticket_endpoint(operation: Callable[[], TicketDetailRead]) -> TicketDetailRead:
    """统一执行工单命令：捕获领域异常并映射，省去每个端点重复 try/except。"""
    try:
        return operation()
    except TicketError as exc:
        raise_ticket_error(exc)
        raise


@router.get("", response_model=PageResponse[TicketRead])
class TicketQueryFilters(BaseModel):
    """工单列表查询过滤条件（查询参数）。"""

    match: Literal["and", "or"] = "and"
    ticket_id: int | None = None
    submitter: str | None = None
    title: str | None = None
    ticket_type: TicketType | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | Literal["UNSET"] | None = None
    assignee: str | None = None


def read_tickets(
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    filters: Annotated[TicketQueryFilters, Depends()],
) -> PageResponse[TicketRead]:
    """分页查询工单列表，支持多条件组合过滤。

    Args:
        pagination: 分页参数（page/size）.
        match: 多条件逻辑，and 全部满足、or 任一满足.
        ticket_id: 精确匹配工单 ID.
        submitter: 提出人用户名模糊匹配.
        title: 标题模糊匹配.
        ticket_type: 工单类型过滤.
        status_filter: 工单状态过滤.
        priority: 优先级过滤，UNSET 表示未设置.
        assignee: 责任人用户名模糊匹配.

    Returns:
        PageResponse[TicketRead]: 当前页工单摘要与总数.
    """
    params = TicketListParams(
        match=filters.match,
        ticket_id=filters.ticket_id,
        submitter=filters.submitter,
        title=filters.title,
        ticket_type=filters.ticket_type,
        status=filters.status,
        priority=filters.priority,
        assignee=filters.assignee,
    )
    items, total = paginate_tickets(db, params=params, pagination=pagination)
    return PageResponse(items=items, total=total, page=pagination.page)


@router.post("", response_model=TicketDetailRead, status_code=status.HTTP_201_CREATED)
def create_ticket_endpoint(
    payload: TicketCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """提出人创建工单，初始状态为待处理。

    Args:
        payload: 工单创建内容（类型/标题/正文）.

    Returns:
        TicketDetailRead: 创建成功的工单详情，HTTP 201.
    """
    return run_ticket_endpoint(
        lambda: create_ticket_command(db, actor=current_user, payload=payload)
    )


@router.get("/{ticket_id}", response_model=TicketDetailRead)
def read_ticket(
    ticket_id: int,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """查询单个工单详情（含评论）。

    Args:
        ticket_id: 工单 ID.

    Returns:
        TicketDetailRead: 工单详情.

    Raises:
        APIError: 404 工单不存在.
    """
    return run_ticket_endpoint(
        lambda: serialize_ticket(db, get_ticket(db, ticket_id), include_comments=True)
    )


@router.patch("/{ticket_id}", response_model=TicketDetailRead)
def update_ticket_endpoint(
    ticket_id: int,
    payload: TicketContentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """提出人编辑待处理工单的标题或正文，受理后内容冻结。

    Args:
        ticket_id: 工单 ID.
        payload: 待更新字段（title/body）.

    Returns:
        TicketDetailRead: 更新后的工单详情.

    Raises:
        APIError: 404 工单不存在 / 403 非提出人或管理员 / 409 非待处理或版本冲突.
    """
    return run_ticket_endpoint(
        lambda: update_ticket_content_command(
            db,
            ticket_id=ticket_id,
            actor=current_user,
            payload=payload,
        )
    )


@router.post("/{ticket_id}/accept", response_model=TicketDetailRead)
def accept_ticket_endpoint(
    ticket_id: int,
    payload: TicketAccept,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """管理员受理工单：指派责任人、设置优先级与计划完成时间。

    Args:
        ticket_id: 工单 ID.
        payload: 受理信息（责任人/优先级/计划完成时间）.

    Returns:
        TicketDetailRead: 受理后的工单详情.

    Raises:
        APIError: 404 工单不存在 / 403 非管理员 / 400 责任人或时间非法 / 409 版本冲突.
    """
    return run_ticket_endpoint(
        lambda: accept_ticket_command(
            db,
            ticket_id=ticket_id,
            actor=current_user,
            payload=payload,
        )
    )


@router.post("/{ticket_id}/reject", response_model=TicketDetailRead)
def reject_ticket_endpoint(
    ticket_id: int,
    payload: TicketReject,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """管理员拒绝待处理工单并记录原因。

    Args:
        ticket_id: 工单 ID.
        payload: 拒绝原因（reason）.

    Returns:
        TicketDetailRead: 拒绝后的工单详情.

    Raises:
        APIError: 404 工单不存在 / 403 非管理员 / 409 版本冲突.
    """
    return run_ticket_endpoint(
        lambda: reject_ticket_command(
            db,
            ticket_id=ticket_id,
            actor=current_user,
            payload=payload,
        )
    )


@router.patch("/{ticket_id}/handling", response_model=TicketDetailRead)
def update_ticket_handling_endpoint(
    ticket_id: int,
    payload: TicketHandlingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """管理员调整已受理工单的处理信息（优先级/责任人/计划完成时间）。

    Args:
        ticket_id: 工单 ID.
        payload: 待调整的处理字段.

    Returns:
        TicketDetailRead: 调整后的工单详情.

    Raises:
        APIError: 404 工单不存在 / 403 非管理员 / 400 责任人非法 / 409 版本冲突.
    """
    return run_ticket_endpoint(
        lambda: update_ticket_handling_command(
            db,
            ticket_id=ticket_id,
            actor=current_user,
            payload=payload,
        )
    )


@router.post("/{ticket_id}/complete", response_model=TicketDetailRead)
def complete_ticket_endpoint(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """管理员将已受理工单标记为完成。

    Args:
        ticket_id: 工单 ID.

    Returns:
        TicketDetailRead: 完成后的工单详情.

    Raises:
        APIError: 404 工单不存在 / 403 非管理员 / 409 版本冲突.
    """
    return run_ticket_endpoint(
        lambda: complete_ticket_command(
            db,
            ticket_id=ticket_id,
            actor=current_user,
        )
    )


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_comment_endpoint(
    ticket_id: int,
    payload: TicketCommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetailRead:
    """为工单追加评论，仅管理员/提出人/现任责任人可评论。

    Args:
        ticket_id: 工单 ID.
        payload: 评论内容（body）.

    Returns:
        TicketDetailRead: 含新评论的工单详情，HTTP 201.

    Raises:
        APIError: 404 工单不存在 / 403 无评论权限.
    """
    return run_ticket_endpoint(
        lambda: add_ticket_comment_command(
            db,
            ticket_id=ticket_id,
            actor=current_user,
            payload=payload,
        )
    )

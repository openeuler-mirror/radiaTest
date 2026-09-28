# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, PageResponse, get_page_params
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.notifications.schemas import NotificationRead, NotificationUnreadCount
from app.modules.notifications.service import (
    NotificationNotFoundError,
    mark_all_notifications_read,
    mark_notification_read,
    paginate_notifications,
    unread_notification_count,
)
from app.modules.users.models import User

# 通知路由：仅当前用户自己的通知(收件人隔离)，分页/未读数/标记已读，无管理端。

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PageResponse[NotificationRead])
def read_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
) -> PageResponse[NotificationRead]:
    """分页查询当前用户的通知列表。

    Returns:
        当前用户通知分页结果.
    """
    items, total = paginate_notifications(
        db,
        user_id=current_user.id,
        pagination=pagination,
    )
    return PageResponse(items=items, total=total, page=pagination.page)


@router.get("/unread-count", response_model=NotificationUnreadCount)
def read_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationUnreadCount:
    """查询当前用户的未读通知数。

    Returns:
        未读通知计数.
    """
    return NotificationUnreadCount(
        count=unread_notification_count(db, user_id=current_user.id)
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationRead:
    """标记指定通知为已读。

    Args:
        notification_id: 通知 ID.

    Returns:
        更新后的通知.

    Raises:
        HTTPException: 404 通知不存在.
    """
    try:
        notification = mark_notification_read(
            db,
            user_id=current_user.id,
            notification_id=notification_id,
        )
    except NotificationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Notification not found") from exc
    db.commit()
    db.refresh(notification)
    return NotificationRead.model_validate(notification)


@router.post("/read-all", response_model=NotificationUnreadCount)
def read_all_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationUnreadCount:
    """将当前用户所有未读通知标记为已读。

    Returns:
        操作后的未读计数（恒为 0）.
    """
    mark_all_notifications_read(db, user_id=current_user.id)
    db.commit()
    return NotificationUnreadCount(count=0)

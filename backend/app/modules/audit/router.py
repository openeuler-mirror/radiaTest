# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, PageResponse, get_page_params
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.audit.schemas import AuditLogListParams, AuditLogRead
from app.modules.audit.service import list_audit_logs
from app.modules.users.models import User, UserRole

router = APIRouter(prefix="/audit-logs", tags=["audit"])


def require_admin(user: User) -> None:
    """审计日志仅 ADMIN 可读，其余角色 403。"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


@router.get("", response_model=PageResponse[AuditLogRead])
def read_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    params: Annotated[AuditLogListParams, Depends()],
) -> PageResponse[AuditLogRead]:
    """
    分页查询审计日志，仅 ADMIN。

    Args:
        pagination: 分页参数（page/size）.
        params: 动作、操作人、目标类型及起止时间过滤参数.

    Returns:
        PageResponse[AuditLogRead]: 分页审计日志列表.

    Raises:
        HTTPException: 403 非 ADMIN.
    """
    require_admin(current_user)
    items, total = list_audit_logs(db, params=params, pagination=pagination)
    return PageResponse(items=items, total=total, page=pagination.page)

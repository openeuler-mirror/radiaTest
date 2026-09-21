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

from app.core.api_runtime import APIError
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import (
    PasswordChange,
    PasswordReset,
    UserCreate,
    UserListParams,
    UserRead,
    UserUpdate,
)
from pydantic import Field

from app.modules.users.service import (
    InvalidCurrentPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserPolicyError,
    change_own_password,
    create_managed_user,
    get_managed_user,
    list_users,
    reset_managed_user_password,
    update_managed_user,
)

# 用户路由：/me 下的自查自改对任意已登录用户开放；用户管理(列表/创建/更新/
# 重置密码)仅 ADMIN。业务规则在 service 层，路由只做鉴权入口与异常映射。

router = APIRouter(prefix="/users", tags=["users"])


def require_admin(user: User) -> None:
    """管理类端点的鉴权入口，非 ADMIN 返回 403。"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """返回当前登录用户的个人信息。

    Returns:
        UserRead: 当前用户资料.
    """
    return current_user


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_current_user_password(
    payload: PasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """当前用户修改自己的密码，需校验原密码。

    Args:
        payload: 密码变更内容（旧密码/新密码）.

    Returns:
        无响应体（HTTP 204 No Content）.

    Raises:
        APIError: 400 原密码错误.
    """
    try:
        change_own_password(db, user=current_user, payload=payload)
    except InvalidCurrentPasswordError as exc:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_current_password",
            message="当前密码错误",
        ) from exc
    db.commit()


class UserQueryParams(UserListParams):
    """用户列表查询参数：过滤条件继承 UserListParams，附分页约束。"""

    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=200)] = 50


@router.get("", response_model=list[UserRead])
def read_users(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    query: Annotated[UserQueryParams, Depends()],
) -> list[User]:
    """管理员分页查询用户列表，支持多条件过滤。

    Args:
        query: 过滤与分页参数（username/display_name/role/is_active/offset/limit）.

    Returns:
        list[UserRead]: 命中的用户列表.

    Raises:
        HTTPException: 403 非管理员.
    """
    require_admin(current_user)
    return list_users(db, params=query, offset=query.offset, limit=query.limit)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """管理员创建受管理用户。

    Args:
        payload: 用户创建内容（用户名/显示名/角色/密码等）.

    Returns:
        UserRead: 创建成功的用户，HTTP 201.

    Raises:
        HTTPException: 403 非管理员 / 409 用户名已存在.
    """
    require_admin(current_user)
    try:
        user = create_managed_user(db, actor=current_user, payload=payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: str,
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """管理员更新指定用户的资料。

    Args:
        user_id: 目标用户 ID.
        payload: 待更新字段.

    Returns:
        UserRead: 更新后的用户.

    Raises:
        HTTPException: 403 非管理员 / 404 用户不存在 / 400 违反用户策略.
    """
    require_admin(current_user)
    try:
        target = get_managed_user(db, user_id)
        user = update_managed_user(db, actor=current_user, target=target, payload=payload)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from exc
    except UserPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_user_password_endpoint(
    user_id: str,
    payload: PasswordReset,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """管理员重置指定用户的密码。

    Args:
        user_id: 目标用户 ID.
        payload: 重置内容（新密码）.

    Returns:
        无响应体（HTTP 204 No Content）.

    Raises:
        HTTPException: 403 非管理员 / 404 用户不存在 / 400 违反密码策略.
    """
    require_admin(current_user)
    try:
        target = get_managed_user(db, user_id)
        reset_managed_user_password(db, actor=current_user, target=target, payload=payload)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from exc
    except UserPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()

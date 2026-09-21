# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.api_runtime import APIError
from app.core.security import create_access_token
from app.db.session import get_db
from app.modules.audit.service import record_audit_log
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.users.service import authenticate_user, mark_login_success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """本地账号登录：校验密码后签发 JWT，并记录 auth.login 审计日志。

    凭据错误统一返回 401，不区分用户名是否存在，避免账号枚举。
    """
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise APIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            message="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    mark_login_success(user)
    record_audit_log(
        db,
        actor_user_id=user.id,
        action="auth.login",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))

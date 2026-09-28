# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.feishu import oauth as feishu_oauth
from app.modules.feishu.models import UserIdentity
from app.modules.feishu.schemas import (
    FeishuAppConfigRead,
    FeishuAppConfigUpsert,
    FeishuBindUrlRead,
    FeishuIdentityRead,
)
from app.modules.feishu.service import (
    FeishuIdentityConflictError,
    bind_feishu_identity,
    get_enabled_feishu_app_config,
    get_feishu_app_config,
    get_user_feishu_identity,
    serialize_feishu_app_config,
    upsert_feishu_app_config,
)
from app.modules.users.models import User, UserRole

# 飞书集成路由：应用配置管理(ADMIN)、当前用户身份查询、绑定 URL 与
# OAuth 回调。回调只做身份绑定、不签发会话；结果通过前端 account 页的
# 查询参数(feishu_bind=success/...)回传，故 include_in_schema=False。
router = APIRouter(prefix="/integrations/feishu", tags=["feishu"])


def require_admin(user: User) -> None:
    """仅 ADMIN 可继续的入口鉴权，否则 403。"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


@router.get("/app", response_model=FeishuAppConfigRead | None)
def read_feishu_app_config(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object] | None:
    """获取当前环境飞书应用配置（仅 ADMIN）。

    Returns:
        当前环境飞书应用配置；未配置时为 None.

    Raises:
        HTTPException: 403 非 ADMIN.
    """
    require_admin(current_user)
    config = get_feishu_app_config(db, environment=get_settings().app_env)
    if config is None:
        return None
    return serialize_feishu_app_config(config)


@router.put("/app", response_model=FeishuAppConfigRead)
def upsert_feishu_app_config_endpoint(
    payload: FeishuAppConfigUpsert,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    """新建或更新当前环境飞书应用配置（仅 ADMIN）。

    Args:
        payload: 飞书应用配置表单（App ID、Secret、启用开关等）.

    Returns:
        更新后的飞书应用配置.

    Raises:
        HTTPException: 403 非 ADMIN.
    """
    require_admin(current_user)
    config = upsert_feishu_app_config(
        db,
        actor=current_user,
        environment=get_settings().app_env,
        payload=payload,
    )
    db.commit()
    db.refresh(config)
    return serialize_feishu_app_config(config)


@router.get("/me/identity", response_model=FeishuIdentityRead | None)
def read_my_feishu_identity(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserIdentity | None:
    """查询当前用户已绑定的飞书身份。

    Returns:
        当前用户的飞书身份；未绑定时为 None.
    """
    return get_user_feishu_identity(db, user_id=current_user.id)


@router.get("/me/bind-url", response_model=FeishuBindUrlRead)
def read_my_feishu_bind_url(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    redirect_uri: Annotated[str, Query(min_length=1)],
) -> FeishuBindUrlRead:
    """生成当前用户飞书 OAuth 授权跳转地址。

    Args:
        redirect_uri: 授权完成后回跳的前端地址（须与本站同域）.

    Returns:
        飞书授权页地址.

    Raises:
        HTTPException: 400 redirect_uri 非法 / 404 飞书应用未配置或未启用.
    """
    try:
        validated_redirect_uri = feishu_oauth.validate_redirect_uri(
            redirect_uri,
            allowed_netloc=request.url.netloc,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    config = get_enabled_feishu_app_config(db, environment=get_settings().app_env)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feishu app is not configured or not enabled",
        )
    return FeishuBindUrlRead(
        authorize_url=feishu_oauth.build_authorize_url(
            config=config,
            user_id=current_user.id,
            redirect_uri=validated_redirect_uri,
        )
    )


@router.get("/oauth/callback", include_in_schema=False)
def bind_feishu_oauth_callback(
    db: Annotated[Session, Depends(get_db)],
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """OAuth 回调：解码 state 校验 CSRF/过期，换 identity 后绑定，重定向到前端 account 页。

    各失败分支(error/missing_code/unavailable/conflict/failed/success)以
    查询参数回传前端展示，不在此处抛 HTTP 异常(浏览器直达，需友好跳转)。
    """
    try:
        user_id, redirect_uri = feishu_oauth.decode_oauth_state(state)
    except feishu_oauth.FeishuOAuthStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Feishu OAuth state",
        ) from exc

    def redirect(status_value: str) -> RedirectResponse:
        return RedirectResponse(feishu_oauth.frontend_account_redirect(redirect_uri, status_value))

    if error:
        return redirect("denied")
    if not code:
        return redirect("missing_code")

    config = get_enabled_feishu_app_config(db, environment=get_settings().app_env)
    user = db.get(User, user_id)
    if config is None or user is None or not user.is_active:
        return redirect("unavailable")

    try:
        payload = feishu_oauth.fetch_feishu_identity(
            config=config,
            code=code,
            redirect_uri=redirect_uri,
        )
        bind_feishu_identity(db, actor=user, payload=payload)
    except FeishuIdentityConflictError:
        db.rollback()
        return redirect("conflict")
    except feishu_oauth.FeishuOAuthError:
        db.rollback()
        return redirect("failed")

    db.commit()
    return redirect("success")

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import jwt
from jwt import InvalidTokenError

from app.core.config import get_settings
from app.modules.feishu.models import FeishuAppConfig
from app.modules.feishu.schemas import FeishuIdentityBind

# 飞书 OAuth 绑定流程：state 用 JWT 承载 user_id + redirect_uri + purpose，
# 兼作 CSRF 防护与回调参数锚定(10 分钟过期)。redirect_uri 强制路径为
# /api/v1/integrations/feishu/oauth/callback 且与当前 radiaTest 主机同源，
# 防止开放重定向。回调只绑定身份、不签发 radiaTest 会话。

AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
TOKEN_URL = "https://accounts.feishu.cn/oauth/v3/token"
USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"
STATE_PURPOSE = "feishu_bind"


class FeishuOAuthError(Exception):
    """飞书 OAuth 交互失败(token 交换、用户信息获取、网络错误)。"""


class FeishuOAuthStateError(FeishuOAuthError):
    """OAuth state JWT 无效或过期，或 purpose/redirect_uri 不符。"""


def callback_path() -> str:
    return f"{get_settings().api_v1_prefix}/integrations/feishu/oauth/callback"


def validate_redirect_uri(
    redirect_uri: str,
    *,
    allowed_netloc: str | None = None,
) -> str:
    """校验 redirect_uri：必须是绝对 HTTP(S) URL、路径为回调路径、无 fragment。

    传入 allowed_netloc 时额外要求与当前 radiaTest 主机同源，防止开放重定向。
    校验通过返回原值，否则抛 ValueError(由路由层映射为 400)。
    """
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("redirect_uri must be an absolute HTTP URL")
    if allowed_netloc is not None and parsed.netloc != allowed_netloc:
        raise ValueError("redirect_uri must use the current radiaTest host")
    if parsed.path != callback_path():
        raise ValueError(f"redirect_uri path must be {callback_path()}")
    if parsed.fragment:
        raise ValueError("redirect_uri must not contain fragment")
    return redirect_uri


def frontend_account_redirect(redirect_uri: str, status: str) -> str:
    parsed = urlparse(redirect_uri)
    return f"{parsed.scheme}://{parsed.netloc}/#/account?feishu_bind={status}"


def create_oauth_state(*, user_id: str, redirect_uri: str) -> str:
    """签发 OAuth state JWT：绑定 user_id、校验后的 redirect_uri、purpose，10 分钟过期。"""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=10)
    payload = {
        "sub": user_id,
        "purpose": STATE_PURPOSE,
        "redirect_uri": validate_redirect_uri(redirect_uri),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_oauth_state(state: str) -> tuple[str, str]:
    """校验并解码 state JWT，返回 (user_id, redirect_uri)。

    校验签名、过期、purpose 必须为 feishu_bind、redirect_uri 仍合法。
    任一不符抛 FeishuOAuthStateError(由路由层映射为 400)。
    """
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise FeishuOAuthStateError("Invalid Feishu OAuth state") from exc

    user_id = payload.get("sub")
    purpose = payload.get("purpose")
    redirect_uri = payload.get("redirect_uri")
    if not isinstance(user_id, str) or not user_id:
        raise FeishuOAuthStateError("Invalid Feishu OAuth state subject")
    if purpose != STATE_PURPOSE:
        raise FeishuOAuthStateError("Invalid Feishu OAuth state purpose")
    if not isinstance(redirect_uri, str):
        raise FeishuOAuthStateError("Invalid Feishu OAuth redirect URI")
    try:
        validate_redirect_uri(redirect_uri)
    except ValueError as exc:
        raise FeishuOAuthStateError("Invalid Feishu OAuth redirect URI") from exc
    return user_id, redirect_uri


def build_authorize_url(
    *,
    config: FeishuAppConfig,
    user_id: str,
    redirect_uri: str,
) -> str:
    state = create_oauth_state(user_id=user_id, redirect_uri=redirect_uri)
    query = urlencode(
        {
            "client_id": config.app_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def post_json(url: str, payload: dict[str, str]) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            data = response.read()
    except HTTPError as exc:
        data = exc.read()
    except URLError as exc:
        raise FeishuOAuthError(f"Feishu OAuth request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FeishuOAuthError("Feishu OAuth response is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise FeishuOAuthError("Feishu OAuth response is not an object")
    return parsed


def get_json(url: str, *, access_token: str) -> dict[str, object]:
    request = Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urlopen(request, timeout=10) as response:
            data = response.read()
    except HTTPError as exc:
        data = exc.read()
    except URLError as exc:
        raise FeishuOAuthError(f"Feishu user info request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FeishuOAuthError("Feishu user info response is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise FeishuOAuthError("Feishu user info response is not an object")
    return parsed


def exchange_code_for_access_token(
    *,
    config: FeishuAppConfig,
    code: str,
    redirect_uri: str,
) -> str:
    response = post_json(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": config.app_id,
            "client_secret": config.app_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    if response.get("code") != 0:
        message = response.get("error_description") or response.get("msg") or "unknown error"
        raise FeishuOAuthError(f"Feishu token exchange failed: {message}")
    access_token = response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise FeishuOAuthError("Feishu token response did not include access_token")
    return access_token


def fetch_feishu_identity(
    *,
    config: FeishuAppConfig,
    code: str,
    redirect_uri: str,
) -> FeishuIdentityBind:
    """完成 OAuth code 换 access_token 再取用户 open_id/union_id。

    两次远端调用(token 交换、user_info)均校验返回 code==0 与必要字段，
    失败抛 FeishuOAuthError。union_id 可能为空。
    """
    access_token = exchange_code_for_access_token(
        config=config,
        code=code,
        redirect_uri=redirect_uri,
    )
    response = get_json(USER_INFO_URL, access_token=access_token)
    if response.get("code") != 0:
        raise FeishuOAuthError(f"Feishu user info failed: {response.get('msg')}")

    data = response.get("data")
    if not isinstance(data, dict):
        raise FeishuOAuthError("Feishu user info response did not include data")
    open_id = data.get("open_id")
    union_id = data.get("union_id")
    if not isinstance(open_id, str) or not open_id:
        raise FeishuOAuthError("Feishu user info response did not include open_id")
    return FeishuIdentityBind(
        open_id=open_id,
        union_id=union_id if isinstance(union_id, str) and union_id else None,
    )

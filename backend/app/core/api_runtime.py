# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import logging
from collections.abc import Mapping
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("kronos.api")

# API 运行时：统一错误响应格式、请求追踪(X-Request-ID)和日志关联。
# 所有 /api/v1 请求注入 request_id 并写进响应头与日志，方便跨日志排障；
# 非 /api 请求(如 nginx 托管的前端静态资源)不进入此中间件，保持默认行为。

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_record_factory_installed = False


class ValidationErrorItem(BaseModel):
    field: str
    message: str


class APIErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | list[ValidationErrorItem] | None = None


class APIErrorResponse(BaseModel):
    error: APIErrorBody


class APIError(Exception):
    """业务层抛出的统一 API 错误，由 _api_error_handler 转为标准响应体。

    code 是稳定的机器可读错误码，message 是面向用户的中文提示，
    details 可携带字段级校验信息。headers 用于 401 等需要特定头的场景。
    """

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | list[ValidationErrorItem] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = dict(headers) if headers else None


_STATUS_ERRORS: dict[int, tuple[str, str]] = {
    status.HTTP_400_BAD_REQUEST: ("bad_request", "请求参数错误"),
    status.HTTP_401_UNAUTHORIZED: ("unauthorized", "身份认证失败"),
    status.HTTP_403_FORBIDDEN: ("forbidden", "没有操作权限"),
    status.HTTP_404_NOT_FOUND: ("not_found", "请求的内容不存在"),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("method_not_allowed", "请求方法不允许"),
    status.HTTP_409_CONFLICT: ("conflict", "请求与当前状态冲突"),
    status.HTTP_411_LENGTH_REQUIRED: ("length_required", "需要请求内容长度"),
    status.HTTP_413_CONTENT_TOO_LARGE: ("content_too_large", "上传文件过大"),
    status.HTTP_422_UNPROCESSABLE_CONTENT: ("validation_error", "请求参数校验失败"),
    status.HTTP_503_SERVICE_UNAVAILABLE: ("service_unavailable", "服务暂不可用"),
    status.HTTP_507_INSUFFICIENT_STORAGE: ("insufficient_storage", "存储空间不足"),
}

_ERROR_RESPONSE_DESCRIPTIONS = {
    400: "请求参数错误",
    401: "身份认证失败",
    403: "没有操作权限",
    404: "请求的内容不存在",
    405: "请求方法不允许",
    409: "请求与当前状态冲突",
    411: "需要请求内容长度",
    413: "上传文件过大",
    422: "请求参数校验失败",
    500: "服务器内部错误",
    503: "服务暂不可用",
    507: "存储空间不足",
}

_VALIDATION_MESSAGES = {
    "bool_parsing": "必须是布尔值",
    "date_from_datetime_parsing": "必须是有效日期",
    "datetime_from_date_parsing": "必须是有效日期时间",
    "enum": "必须是允许的选项",
    "float_parsing": "必须是数字",
    "int_parsing": "必须是整数",
    "json_invalid": "必须是有效 JSON",
    "list_type": "必须是列表",
    "missing": "不能为空",
    "string_too_long": "长度超过限制",
    "string_too_short": "长度不足",
    "string_type": "必须是文本",
    "uuid_parsing": "必须是有效 UUID",
    "value_error": "值不符合要求",
}


def _get_request_id() -> str | None:
    return _request_id.get()


def _install_record_factory() -> None:
    global _record_factory_installed
    if _record_factory_installed:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous_factory(*args, **kwargs)
        request_id = _get_request_id()
        record.request_id = request_id
        if request_id and (
            record.name == "uvicorn.access"
            or record.name.startswith(("app.", "kronos."))
        ):
            record.msg = f"request_id={request_id} {record.msg}"
        return record

    logging.setLogRecordFactory(record_factory)
    _record_factory_installed = True


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[ValidationErrorItem] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    content = APIErrorResponse(
        error=APIErrorBody(code=code, message=message, details=details),
    ).model_dump(mode="json")
    return JSONResponse(content=content, status_code=status_code, headers=headers)


def _status_error(status_code: int) -> tuple[str, str]:
    specific = _STATUS_ERRORS.get(status_code)
    if specific is not None:
        return specific
    if status_code >= 500:
        return "internal_error", "服务器内部错误"
    return ("bad_request", "请求失败")


def _http_error_message(detail: Any, fallback: str) -> str:
    """选一条面向终端用户的错误消息。

    detail 已含 CJK 时视为已本地化，原样使用；否则返回 fallback，避免把
    后端原始英文错误直接泄露给终端用户。
    """
    if not isinstance(detail, str) or not detail.strip():
        return fallback
    if any("\u4e00" <= character <= "\u9fff" for character in detail):
        return detail
    return fallback


def _field_name(location: tuple[str | int, ...]) -> str:
    parts = [str(part) for part in location]
    if parts and parts[0] in {"body", "cookie", "header", "path", "query"}:
        parts = parts[1:]
    return ".".join(parts) or "request"


def _validation_message(error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))
    context = error.get("ctx")

    if error_type == "greater_than" and isinstance(context, dict):
        return f"必须大于 {context.get('gt')}"
    if error_type == "greater_than_equal" and isinstance(context, dict):
        return f"必须大于或等于 {context.get('ge')}"
    if error_type == "less_than" and isinstance(context, dict):
        return f"必须小于 {context.get('lt')}"
    if error_type == "less_than_equal" and isinstance(context, dict):
        return f"必须小于或等于 {context.get('le')}"

    message = str(error.get("msg", ""))
    if any("\u4e00" <= character <= "\u9fff" for character in message):
        return message.removeprefix("Value error, ")
    return _VALIDATION_MESSAGES.get(error_type, "值不符合要求")


def _validation_details(exc: RequestValidationError) -> list[ValidationErrorItem]:
    return [
        ValidationErrorItem(
            field=_field_name(tuple(error.get("loc", ()))),
            message=_validation_message(error),
        )
        for error in exc.errors()
    ]


async def _api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=exc.headers,
    )


async def _http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    if not _is_api_request(request.scope, request.app.state.api_v1_prefix):
        return await http_exception_handler(request, exc)

    code, fallback_message = _status_error(exc.status_code)
    if exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=fallback_message,
            details={"request_id": _get_request_id()},
            headers=exc.headers,
        )
    return _error_response(
        status_code=exc.status_code,
        code=code,
        message=_http_error_message(exc.detail, fallback_message),
        headers=exc.headers,
    )


async def _request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    if not _is_api_request(request.scope, request.app.state.api_v1_prefix):
        return await request_validation_exception_handler(request, exc)

    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message="请求参数校验失败",
        details=_validation_details(exc),
    )


def _is_api_request(scope: Scope, api_prefix: str) -> bool:
    path = scope.get("path", "")
    return path == api_prefix or path.startswith(f"{api_prefix}/")


class _RequestTraceMiddleware:
    """为 /api 请求注入 X-Request-ID 并捕获未处理异常转为 500 响应。

    request_id 经 ContextVar 贯穿整个请求，日志记录工厂会把它写进 app.*/kronos.*
    的日志行，实现请求级可追溯。响应已开始后才抛的异常不再兜底(无法再写响应)。
    """

    def __init__(self, app: ASGIApp, *, api_prefix: str) -> None:
        self.app = app
        self.api_prefix = api_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not _is_api_request(scope, self.api_prefix):
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        token = _request_id.set(request_id)
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception:
                if response_started:
                    raise
                logger.exception("Unhandled API exception")
                response = _error_response(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    code="internal_error",
                    message="服务器内部错误",
                    details={"request_id": request_id},
                )
                await response(scope, receive, send_with_request_id)
        finally:
            _request_id.reset(token)


def _common_error_responses() -> dict[int, dict[str, Any]]:
    return {
        status_code: {
            "description": description,
            "model": APIErrorResponse,
        }
        for status_code, description in _ERROR_RESPONSE_DESCRIPTIONS.items()
    }


def install_api_runtime(
    app: FastAPI,
    *,
    router: APIRouter,
    prefix: str,
) -> None:
    """装配 API 运行时：注册路由、统一错误处理器和请求追踪中间件。

    统一错误响应格式为 {error: {code, message, details}}，把 FastAPI/Starlette
    的原生异常和校验异常都归一到该格式，前端只需处理一种错误结构。
    """
    app.state.api_v1_prefix = prefix
    _install_record_factory()
    app.add_exception_handler(APIError, _api_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _request_validation_error_handler)
    app.add_middleware(_RequestTraceMiddleware, api_prefix=prefix)
    app.include_router(router, prefix=prefix, responses=_common_error_responses())

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import logging
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.api_runtime import APIError, install_api_runtime
from app.main import create_app

business_logger = logging.getLogger("kronos.test.business")
external_logger = logging.getLogger("external.test")


class RuntimeNestedInput(BaseModel):
    name: Annotated[str, Field(min_length=2)]
    count: Annotated[int, Field(gt=0)]


class RuntimeValidationInput(BaseModel):
    config: RuntimeNestedInput


def runtime_test_app() -> FastAPI:
    app = create_app()

    @app.get("/api/v1/_runtime/domain-error")
    def domain_error() -> None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="resource_not_found",
            message="资源不存在",
        )

    @app.post("/api/v1/_runtime/validation")
    def validation(payload: RuntimeValidationInput) -> RuntimeValidationInput:
        return payload

    @app.get("/api/v1/_runtime/unexpected")
    def unexpected() -> None:
        raise RuntimeError("secret implementation detail")

    @app.get("/api/v1/_runtime/explicit-500")
    def explicit_500() -> None:
        raise HTTPException(status_code=500, detail="secret implementation detail")

    @app.get("/api/v1/_runtime/insufficient-storage")
    def insufficient_storage() -> None:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="ISO upload would exceed storage safety limits",
        )

    @app.get("/api/v1/_runtime/business-log")
    def business_log() -> None:
        business_logger.info("Business operation completed")
        external_logger.info("Third party log")

    return app


def assert_request_id(response_header: str | None) -> str:
    assert response_header is not None
    return str(UUID(response_header))


def test_normal_response_has_server_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        with TestClient(runtime_test_app()) as client:
            response = client.get(
                "/api/v1/_runtime/business-log",
                headers={"X-Request-ID": "client-provided"},
            )

    assert response.status_code == 200
    request_id = assert_request_id(response.headers.get("X-Request-ID"))
    assert request_id != "client-provided"
    assert request_id in caplog.text
    assert "Business operation completed" in caplog.text
    external_record = next(record for record in caplog.records if record.name == "external.test")
    assert external_record.getMessage() == "Third party log"
    assert external_record.request_id == request_id


def test_domain_and_framework_errors_use_the_error_envelope() -> None:
    with TestClient(runtime_test_app()) as client:
        domain_response = client.get("/api/v1/_runtime/domain-error")
        missing_response = client.get("/api/v1/missing")
        method_response = client.post("/api/v1/health")

    assert domain_response.json() == {
        "error": {
            "code": "resource_not_found",
            "message": "资源不存在",
            "details": None,
        }
    }
    assert missing_response.json() == {
        "error": {
            "code": "not_found",
            "message": "请求的内容不存在",
            "details": None,
        }
    }
    assert method_response.json() == {
        "error": {
            "code": "method_not_allowed",
            "message": "请求方法不允许",
            "details": None,
        }
    }
    for response in (domain_response, missing_response, method_response):
        assert "detail" not in response.json()
        assert_request_id(response.headers.get("X-Request-ID"))
    assert method_response.headers["Allow"] == "GET"


def test_authentication_error_preserves_challenge_header() -> None:
    with TestClient(runtime_test_app()) as client:
        response = client.get("/api/v1/users")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_validation_error_hides_framework_details() -> None:
    with TestClient(runtime_test_app()) as client:
        response = client.post(
            "/api/v1/_runtime/validation",
            json={"config": {"name": "", "count": 0}},
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "请求参数校验失败",
            "details": [
                {"field": "config.name", "message": "长度不足"},
                {"field": "config.count", "message": "必须大于 0"},
            ],
        }
    }
    body = str(response.json())
    assert "greater_than" not in body
    assert "input" not in body


def test_unexpected_error_returns_request_id_and_logs_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="kronos.api"):
        with TestClient(runtime_test_app(), raise_server_exceptions=False) as client:
            response = client.get("/api/v1/_runtime/unexpected")

    request_id = assert_request_id(response.headers.get("X-Request-ID"))
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "服务器内部错误",
            "details": {"request_id": request_id},
        }
    }
    assert "secret implementation detail" not in str(response.json())
    assert request_id in caplog.text
    assert "secret implementation detail" in caplog.text


def test_explicit_500_hides_detail_and_returns_request_id() -> None:
    with TestClient(runtime_test_app()) as client:
        response = client.get("/api/v1/_runtime/explicit-500")

    request_id = assert_request_id(response.headers.get("X-Request-ID"))
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "服务器内部错误",
            "details": {"request_id": request_id},
        }
    }
    assert "secret implementation detail" not in str(response.json())


def test_non_500_server_errors_show_specific_message() -> None:
    with TestClient(runtime_test_app()) as client:
        response = client.get("/api/v1/_runtime/insufficient-storage")

    assert_request_id(response.headers.get("X-Request-ID"))
    assert response.status_code == 507
    assert response.json() == {
        "error": {
            "code": "insufficient_storage",
            "message": "存储空间不足",
            "details": None,
        }
    }
    assert "服务器内部错误" not in str(response.json())


def test_unexpected_error_keeps_cors_headers() -> None:
    app = FastAPI()
    router = APIRouter()

    @router.get("/unexpected")
    def unexpected() -> None:
        raise RuntimeError("boom")

    install_api_runtime(app, router=router, prefix="/api/v1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://kronos.example"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/unexpected",
            headers={"Origin": "https://kronos.example"},
        )

    assert response.status_code == 500
    assert response.headers["Access-Control-Allow-Origin"] == "https://kronos.example"


def test_openapi_uses_the_common_error_schema() -> None:
    schema = create_app().openapi()
    health_responses = schema["paths"]["/api/v1/health"]["get"]["responses"]

    assert "APIErrorResponse" in schema["components"]["schemas"]
    for status_code in ("400", "401", "403", "404", "405", "409", "422", "500"):
        assert health_responses[status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/APIErrorResponse"
        }
    assert "HTTPValidationError" not in schema["components"]["schemas"]

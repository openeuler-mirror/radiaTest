# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "kronos"


@pytest.fixture()
def database_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with Session(engine) as db:

        def _override_get_db() -> Session:
            return db

        app = create_app()
        app.dependency_overrides[get_db] = _override_get_db
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()


def test_database_health_endpoint(database_client: TestClient) -> None:
    response = database_client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "reachable",
    }


def test_database_health_endpoint_reports_unavailable() -> None:
    class UnavailableDatabase:
        @staticmethod
        def execute(statement: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("database unavailable"))

    def _unavailable_override() -> UnavailableDatabase:
        return UnavailableDatabase()

    app = create_app()
    app.dependency_overrides[get_db] = _unavailable_override
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/database")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "数据库不可用",
            "details": None,
        }
    }

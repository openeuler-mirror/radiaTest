# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.api_runtime import APIError
from app.db.session import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def read_health() -> dict[str, str]:
    """进程存活探针，不依赖数据库，供负载均衡/容器健康检查。"""
    return {
        "status": "ok",
        "service": "kronos",
        "time": datetime.now(UTC).isoformat(),
    }


@router.get("/health/database")
def read_database_health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """数据库连通探针：SELECT 1 失败返回 503，供深度健康检查和部署后校验。"""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="database_unavailable",
            message="数据库不可用",
        ) from exc

    return {
        "status": "ok",
        "database": "reachable",
    }

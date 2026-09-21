# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.api_runtime import APIError
from app.modules.idempotency.models import IdempotencyRecord
from app.modules.idempotency.service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotentRequest,
    begin_idempotent_request,
    hash_request_body,
)
from app.modules.users.models import User


@dataclass(frozen=True)
class HTTPIdempotencyDecision:
    """HTTP 层幂等判定：replay 非空时直接返回历史 JSONResponse，否则持有新领取的记录。"""

    record: IdempotencyRecord | None
    replay: JSONResponse | None


def begin_http_idempotent_request(
    db: Session,
    *,
    actor: User,
    request: Request,
    key: str | None,
    payload: dict[str, Any],
) -> HTTPIdempotencyDecision:
    """路由端幂等入口：把 service 的判定适配为 HTTP 响应和 APIError。

    把 IdempotencyConflict 的三个子类映射为对应的 4xx：
    - 键缺失/格式错 → 400
    - 仍在处理中 → 409 idempotency_in_progress
    - 键复用或记录冲突 → 409 idempotency_key_conflict
    """
    try:
        decision = begin_idempotent_request(
            db,
            request=IdempotentRequest(
                actor=actor,
                method=request.method,
                path=request.url.path,
                key=key,
                request_hash=hash_request_body(payload),
            ),
        )
    except ValueError:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="bad_request",
            message="幂等键缺失或格式不正确",
        ) from None
    except IdempotencyInProgressError:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_in_progress",
            message="相同幂等键的请求仍在处理中",
        ) from None
    except IdempotencyConflictError:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_key_conflict",
            message="幂等键与已有请求冲突",
        ) from None

    replay = None
    if decision.replay is not None:
        body, status_code = decision.replay
        replay = JSONResponse(content=body, status_code=status_code)
    return HTTPIdempotencyDecision(record=decision.record, replay=replay)

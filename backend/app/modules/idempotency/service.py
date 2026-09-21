# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.idempotency.models import IdempotencyRecord
from app.modules.users.models import User

# 幂等基础设施：按 (actor, method, path, idempotency_key) 维度保证同一请求
# 重复提交时只执行一次副作用，并原样重放首次响应。处理中记录失败会废弃，
# 让客户端可用相同 Key 安全重试；已完成的记录保留 7 天后由清理任务回收。

IDEMPOTENCY_KEY_MAX_LENGTH = 255
IDEMPOTENCY_PROCESSING = "processing"
IDEMPOTENCY_COMPLETED = "completed"


class IdempotencyConflictError(Exception):
    """幂等键冲突：Key 被不同请求体复用，或记录不完整无法重放。"""


@dataclass(frozen=True)
class IdempotentRequest:
    """一次待判定的幂等请求：操作者身份与请求身份四元组。"""

    actor: User
    method: str
    path: str
    key: str | None
    request_hash: str


class IdempotencyInProgressError(IdempotencyConflictError):
    """相同幂等键的请求仍在处理中，拒绝并发重入。"""


@dataclass(frozen=True)
class IdempotencyDecision:
    """幂等判定结果：replay 非空时直接重放历史响应，否则 record 持有新领取的处理中记录。"""

    record: IdempotencyRecord | None
    replay: tuple[dict[str, object], int] | None


def validate_idempotency_key(key: str | None) -> str:
    """校验 Idempotency-Key 非空且不超长，无效则抛 ValueError(由 HTTP 层转 400)。"""
    if not key:
        raise ValueError("Idempotency-Key header is required")
    if len(key) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ValueError(
            f"Idempotency-Key must not exceed {IDEMPOTENCY_KEY_MAX_LENGTH} characters"
        )
    return key


def hash_request_body(payload: dict[str, Any]) -> str:
    """对请求体做稳定 SHA-256，用于检测同一 Key 是否被不同请求体复用。"""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def get_idempotency_record(
    db: Session,
    *,
    actor: User,
    method: str,
    path: str,
    key: str,
) -> IdempotencyRecord | None:
    """按幂等四元组(actor, method, path, key)查唯一记录，找不到返回 None。"""
    statement = select(IdempotencyRecord).where(
        and_(
            IdempotencyRecord.actor_user_id == actor.id,
            IdempotencyRecord.method == method,
            IdempotencyRecord.path == path,
            IdempotencyRecord.idempotency_key == key,
        )
    )
    return db.execute(statement).scalar_one_or_none()


def replay_idempotency_record(
    record: IdempotencyRecord | None,
    *,
    request_hash: str,
) -> tuple[dict[str, object], int] | None:
    """决定是否重放已有记录的响应。

    - 记录不存在：返回 None，交由调用方创建新记录。
    - request_hash 不一致：同一 Key 携带了不同请求体，视为误用，抛冲突。
    - 仍在 processing：前一次请求尚未完成，拒绝并发重入。
    - response 不完整：记录损坏，抛冲突而非返回脏数据。
    """
    if record is None:
        return None
    if record.request_hash != request_hash:
        raise IdempotencyConflictError("Idempotency-Key was reused with a different request")
    if record.state == IDEMPOTENCY_PROCESSING:
        raise IdempotencyInProgressError("A request with this Idempotency-Key is still processing")
    if record.response_body is None or record.status_code is None:
        raise IdempotencyConflictError("Idempotency record is incomplete")
    return record.response_body, record.status_code


def begin_idempotent_request(
    db: Session,
    *,
    request: IdempotentRequest,
) -> IdempotencyDecision:
    """幂等入口：先查历史记录决定重放，否则领取一条 processing 记录。

    并发处理：两个相同 Key 的请求同时到达时，唯一约束让其中一个在 commit 时
    抛 IntegrityError；失败方回滚后重新查记录并重放胜出方的结果，从而保证
    副作用只执行一次。返回 IdempotencyDecision，replay 非空即重放。
    """
    actor = request.actor
    method = request.method
    path = request.path
    key = request.key
    request_hash = request.request_hash
    key = validate_idempotency_key(key)
    existing = get_idempotency_record(
        db,
        actor=actor,
        method=method,
        path=path,
        key=key,
    )
    replay = replay_idempotency_record(existing, request_hash=request_hash)
    if replay is not None:
        return IdempotencyDecision(record=None, replay=replay)

    record = IdempotencyRecord(
        actor_user_id=actor.id,
        method=method,
        path=path,
        idempotency_key=key,
        request_hash=request_hash,
        state=IDEMPOTENCY_PROCESSING,
        status_code=None,
        response_body=None,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # 并发下另一请求先领取了同一 Key：回滚后重查并重放其结果。
        db.rollback()
        existing = get_idempotency_record(
            db,
            actor=actor,
            method=method,
            path=path,
            key=key,
        )
        replay = replay_idempotency_record(existing, request_hash=request_hash)
        if replay is not None:
            return IdempotencyDecision(record=None, replay=replay)
        raise IdempotencyConflictError("Failed to claim Idempotency-Key") from None
    return IdempotencyDecision(record=record, replay=None)


@contextmanager
def abandon_idempotency_on_error(
    db: Session,
    record: IdempotencyRecord | None,
) -> Iterator[None]:
    """包裹副作用逻辑：抛异常时废弃 processing 记录，使相同 Key 可安全重试。

    已完成记录不会被删除，避免误删可重放的历史响应。
    """
    try:
        yield
    except Exception:
        abandon_idempotency_record(db, record)
        raise


def abandon_idempotency_record(
    db: Session,
    record: IdempotencyRecord | None,
) -> None:
    """删除一条 processing 记录并回滚事务，仅在请求失败时调用以释放 Key。"""
    db.rollback()
    if record is None:
        return
    db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.id == record.id,
            IdempotencyRecord.state == IDEMPOTENCY_PROCESSING,
        )
    )
    db.commit()


def record_idempotency_response(
    db: Session,
    *,
    record: IdempotencyRecord,
    response_body: dict[str, object],
    status_code: int,
) -> IdempotencyRecord:
    """把处理中记录置为 completed 并写入响应，供后续相同 Key 重放。

    不可破坏约束：仅 processing 态可转 completed，避免覆盖已废弃或已完成的记录。
    """
    current = db.get(IdempotencyRecord, record.id)
    if current is None or current.state != IDEMPOTENCY_PROCESSING:
        raise IdempotencyConflictError("Idempotency claim is no longer processing")
    current.state = IDEMPOTENCY_COMPLETED
    current.response_body = response_body
    current.status_code = status_code
    db.flush()
    return current


def cleanup_idempotency_records(db: Session, *, days: int) -> int:
    """清理超过 days 天的已完成幂等记录，返回删除行数。

    只删 completed，不删 processing——处理中记录可能属于正在执行的请求，
    删除会破坏并发安全和重放语义。
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.created_at < cutoff,
            IdempotencyRecord.state == IDEMPOTENCY_COMPLETED,
        )
    )
    return result.rowcount or 0

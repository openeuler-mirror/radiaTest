# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.idempotency.models import IdempotencyRecord
from app.modules.idempotency.service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    abandon_idempotency_on_error,
    IdempotentRequest,
    begin_idempotent_request,
    cleanup_idempotency_records,
    record_idempotency_response,
)
from app.modules.users.models import User, UserRole


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


def make_record(*, created_at: datetime, key: str) -> IdempotencyRecord:
    return IdempotencyRecord(
        actor_user_id="00000000-0000-0000-0000-000000000001",
        method="POST",
        path="/api/v1/resources/imports/confirm",
        idempotency_key=key,
        request_hash="0" * 64,
        status_code=200,
        response_body={"ok": True},
        created_at=created_at,
    )


def make_actor(db: Session) -> User:
    actor = User(
        username="admin",
        role=UserRole.ADMIN.value,
        password_hash="not-used",
    )
    db.add(actor)
    db.commit()
    return actor


def test_cleanup_idempotency_records_deletes_only_expired_records(
    db_session: Session,
) -> None:
    db = db_session
    old_record = make_record(
        created_at=datetime.now(UTC) - timedelta(days=8),
        key="old-key",
    )
    recent_record = make_record(
        created_at=datetime.now(UTC) - timedelta(days=1),
        key="recent-key",
    )
    processing_record = make_record(
        created_at=datetime.now(UTC) - timedelta(days=8),
        key="processing-key",
    )
    processing_record.state = "processing"
    processing_record.status_code = None
    processing_record.response_body = None
    db.add_all([old_record, recent_record, processing_record])
    db.commit()

    deleted = cleanup_idempotency_records(db, days=7)
    db.commit()

    remaining = list(db.execute(select(IdempotencyRecord.idempotency_key)).scalars())
    assert deleted == 1
    assert set(remaining) == {"recent-key", "processing-key"}


def test_concurrent_caller_observes_processing_claim(db_session: Session) -> None:
    actor = make_actor(db_session)
    first = begin_idempotent_request(
        db_session,
        request=IdempotentRequest(
            actor=actor,
            method="POST",
            path="/api/v1/vm-requests",
            key="concurrent-key",
            request_hash="1" * 64,
        ),
    )
    assert first.record is not None

    competing_session = Session(bind=db_session.get_bind())
    competing_actor = competing_session.get(User, actor.id)
    assert competing_actor is not None
    try:
        with pytest.raises(IdempotencyInProgressError):
            begin_idempotent_request(
                competing_session,
                request=IdempotentRequest(
                    actor=competing_actor,
                    method="POST",
                    path="/api/v1/vm-requests",
                    key="concurrent-key",
                    request_hash="1" * 64,
                ),
            )
    finally:
        competing_session.close()


def test_unique_constraint_race_reloads_the_winning_processing_claim(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = make_actor(db_session)
    original_commit = db_session.commit
    commit_calls = 0

    def lose_claim_race() -> None:
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls != 1:
            original_commit()
            return

        db_session.rollback()
        db_session.add(
            IdempotencyRecord(
                actor_user_id=actor.id,
                method="POST",
                path="/api/v1/vm-requests",
                idempotency_key="racing-key",
                request_hash="6" * 64,
                state="processing",
            )
        )
        original_commit()
        raise IntegrityError("INSERT", {}, Exception("unique constraint"))

    monkeypatch.setattr(db_session, "commit", lose_claim_race)

    with pytest.raises(IdempotencyInProgressError):
        begin_idempotent_request(
            db_session,
            request=IdempotentRequest(
                actor=actor,
                method="POST",
                path="/api/v1/vm-requests",
                key="racing-key",
                request_hash="6" * 64,
            ),
        )


def test_completed_claim_replays_response_and_rejects_changed_payload(
    db_session: Session,
) -> None:
    actor = make_actor(db_session)
    first = begin_idempotent_request(
        db_session,
        request=IdempotentRequest(
            actor=actor,
            method="POST",
            path="/api/v1/resources/imports",
            key="replay-key",
            request_hash="2" * 64,
        ),
    )
    assert first.record is not None
    record_idempotency_response(
        db_session,
        record=first.record,
        response_body={"created": 2},
        status_code=200,
    )
    db_session.commit()

    replay = begin_idempotent_request(
        db_session,
        request=IdempotentRequest(
            actor=actor,
            method="POST",
            path="/api/v1/resources/imports",
            key="replay-key",
            request_hash="2" * 64,
        ),
    )
    assert replay.record is None
    assert replay.replay == ({"created": 2}, 200)

    with pytest.raises(IdempotencyConflictError):
        begin_idempotent_request(
            db_session,
            request=IdempotentRequest(
                actor=actor,
                method="POST",
                path="/api/v1/resources/imports",
                key="replay-key",
                request_hash="3" * 64,
            ),
        )


def test_processing_claim_is_abandoned_after_error(db_session: Session) -> None:
    actor = make_actor(db_session)
    decision = begin_idempotent_request(
        db_session,
        request=IdempotentRequest(
            actor=actor,
            method="POST",
            path="/api/v1/leases/imports",
            key="retryable-key",
            request_hash="4" * 64,
        ),
    )
    assert decision.record is not None

    with pytest.raises(RuntimeError, match="business failed"):
        with abandon_idempotency_on_error(db_session, decision.record):
            raise RuntimeError("business failed")

    retry = begin_idempotent_request(
        db_session,
        request=IdempotentRequest(
            actor=actor,
            method="POST",
            path="/api/v1/leases/imports",
            key="retryable-key",
            request_hash="4" * 64,
        ),
    )
    assert retry.record is not None


@pytest.mark.parametrize("key", [None, "", "x" * 256])
def test_idempotency_key_must_be_between_1_and_255_characters(
    db_session: Session,
    key: str | None,
) -> None:
    actor = make_actor(db_session)

    with pytest.raises(ValueError):
        begin_idempotent_request(
            db_session,
            request=IdempotentRequest(
                actor=actor,
                method="POST",
                path="/api/v1/vm-requests",
                key=key,
                request_hash="5" * 64,
            ),
        )


def test_idempotency_key_accepts_255_characters(db_session: Session) -> None:
    actor = make_actor(db_session)

    decision = begin_idempotent_request(
        db_session,
        request=IdempotentRequest(
            actor=actor,
            method="POST",
            path="/api/v1/vm-requests",
            key="x" * 255,
            request_hash="7" * 64,
        ),
    )

    assert decision.record is not None

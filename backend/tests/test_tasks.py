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
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.tasks.models import TaskEvent
from app.modules.tasks.service import cleanup_task_events


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


def make_event(*, created_at: datetime, message: str) -> TaskEvent:
    return TaskEvent(
        task_type="vm_create",
        subject_type="vm_request",
        subject_id="00000000-0000-0000-0000-000000000001",
        phase="host_command",
        message=message,
        created_at=created_at,
    )


def test_cleanup_task_events_deletes_only_expired_events(db_session: Session) -> None:
    db = db_session
    old_event = make_event(
        created_at=datetime.now(UTC) - timedelta(days=31),
        message="old",
    )
    recent_event = make_event(
        created_at=datetime.now(UTC) - timedelta(days=1),
        message="recent",
    )
    db.add_all([old_event, recent_event])
    db.commit()

    deleted = cleanup_task_events(db, days=30)
    db.commit()

    remaining = list(db.execute(select(TaskEvent.message)).scalars())
    assert deleted == 1
    assert remaining == ["recent"]

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskEvent(Base):
    """任务事件：追加写入的执行轨迹，用于详情页展示与中断恢复定位。

    不可破坏约束：事件只追加不覆盖，保留原始执行事实；subject_type+subject_id
    定位被跟踪对象(如 vm_request/test_job)，celery_task_id 关联具体 Celery
    任务，phase 标记执行阶段(started/failed/succeeded 等)。
    """

    __tablename__ = "task_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    subject_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    phase: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    host_resource_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    host_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )

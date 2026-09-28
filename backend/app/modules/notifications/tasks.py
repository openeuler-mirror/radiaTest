# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import logging

from celery import Task

from app.db.session import SessionLocal
from app.modules.notifications.delivery import (
    deliver_feishu_notification,
    mark_feishu_delivery_failed,
)
from app.modules.notifications.service import run_daily_maintenance
from app.worker import celery_app

logger = logging.getLogger("kronos.notifications")


@celery_app.task(name="app.modules.notifications.tasks.daily_maintenance")
def daily_notification_maintenance() -> None:
    """每日维护任务：生成到期提醒 + 清理过期通知，并把需飞书投递的通知入队。

    入队失败时把对应通知标记为 feishu FAILED，避免一直挂 PENDING。
    """
    with SessionLocal() as db:
        pending_feishu_ids = run_daily_maintenance(db)
        db.commit()

    for notification_id in pending_feishu_ids:
        try:
            deliver_feishu_notification_task.delay(notification_id)
        except Exception as exc:
            logger.exception(
                "Failed to enqueue Feishu notification: notification_id=%s",
                notification_id,
            )
            with SessionLocal() as db:
                mark_feishu_delivery_failed(
                    db,
                    notification_id=notification_id,
                    error=f"Failed to enqueue delivery task: {exc}",
                )


@celery_app.task(
    bind=True,
    name="app.modules.notifications.tasks.deliver_feishu",
    max_retries=3,
)
def deliver_feishu_notification_task(task: Task, notification_id: str) -> None:
    """投递单条通知到飞书。失败重试最多 3 次(间隔 30s)，重试耗尽后标记 FAILED。"""
    try:
        with SessionLocal() as db:
            deliver_feishu_notification(db, notification_id=notification_id)
    except Exception as exc:
        if task.request.retries >= task.max_retries:
            with SessionLocal() as db:
                mark_feishu_delivery_failed(
                    db,
                    notification_id=notification_id,
                    error=str(exc),
                )
            raise
        raise task.retry(exc=exc, countdown=30) from exc

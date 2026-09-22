# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.tasks.recovery import RecoveryTrigger, recover_interrupted_tasks

logger = logging.getLogger("kronos.worker")

settings = get_settings()

celery_app = Celery(
    "kronos",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend or settings.celery_broker_url,
    # 声明所有任务模块，让 Celery 启动时自动发现任务函数注册到 worker。
    include=[
        "app.modules.vms.tasks",
        "app.modules.vms.pxe_install",
        "app.modules.test_management.tasks",
        "app.modules.notifications.tasks",
        "app.modules.pipelines.tasks",
        "app.modules.rc_management.tasks",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.display_timezone,
    beat_cron_starting_deadline=60,
    beat_schedule={
        "daily-notification-maintenance": {
            "task": "app.modules.notifications.tasks.daily_maintenance",
            # 每日 09:00 执行通知维护(资源到期提醒、通知清理)。
            "schedule": crontab(hour=9, minute=0),
        }
    },
)


@worker_ready.connect
def recover_worker_tasks(**_: object) -> None:
    """worker 启动时恢复中断的异步任务。

    进程崩溃或容器重启会留下 creating/未完成的任务事件；此处按
    WORKER_STARTUP 触发器把它们标记为失败并收敛状态，避免永久卡在
    中间态。失败不阻断 worker 启动——恢复出错只记日志，保证主循环可用。
    """
    try:
        with SessionLocal() as db:
            summary = recover_interrupted_tasks(
                db,
                trigger=RecoveryTrigger.WORKER_STARTUP,
            )
    except Exception:  # noqa: BLE001
        logger.exception("Worker startup recovery failed")
        return

    if summary.failed_task_types:
        logger.error(
            "Worker startup recovery completed with failures: task_types=%s",
            ",".join(task_type.value for task_type in summary.failed_task_types),
        )
        return
    logger.info("Worker startup recovery completed: recovered=%s", summary.total)

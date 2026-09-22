# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""RC 比对 Celery 任务：抓清单→比较→落库。

从触发器创建的 PENDING 实例执行 compute_compare，成功置 succeeded，异常置 failed
并记录 error_msg。celery broker 配置了 redis 时用 SETNX 防同对并发（best-effort），
未配置（本地/测试）时跳过——DB 状态已是第一道并发防线。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.modules.rc_management.compare_service import compute_compare
from app.modules.rc_management.models import CompareStatus, MilestoneCompare
from app.worker import celery_app

logger = logging.getLogger("kronos.rc_management")


def utc_now() -> datetime:
    return datetime.now(UTC)


# 并发防重入由触发端 DB 状态守卫承担（同对 pending/running 时 409）；
# redis 锁曾在任务失败路径泄漏（仅靠 TTL 过期），导致后续比对空转 30 分钟，已移除。
@celery_app.task(name="app.modules.rc_management.tasks.run_rc_compare_task")
def run_rc_compare_task(compare_id: str) -> int:
    with SessionLocal() as db:
        compare = db.get(MilestoneCompare, compare_id)
        if compare is None:
            logger.warning("compare %s not found", compare_id)
            return 0
        if compare.status != CompareStatus.PENDING.value:
            return compare.total_changed or 0
        compare.status = CompareStatus.RUNNING.value
        db.commit()
        try:
            total, _summary = compute_compare(db, compare)
            db.refresh(compare)
            return total
        except Exception as exc:  # noqa: BLE001
            logger.exception("compare %s failed", compare_id)
            db.rollback()
            compare = db.get(MilestoneCompare, compare_id)
            compare.status = CompareStatus.FAILED.value
            compare.error_msg = str(exc)[:2000]
            compare.completed_at = utc_now()
            db.commit()
            raise

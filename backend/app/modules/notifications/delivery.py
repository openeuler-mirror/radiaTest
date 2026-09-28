# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.feishu.cards import action_block, button, card, text_block
from app.modules.feishu.messaging import LarkMessageSender
from app.modules.feishu.models import ExternalIdentityProvider, UserIdentity
from app.modules.feishu.service import get_enabled_feishu_app_config
from app.modules.notifications.models import (
    FeishuDeliveryStatus,
    Notification,
    NotificationTargetType,
    NotificationType,
)
from app.modules.notifications.service import now_utc

FEISHU_ERROR_MAX_LENGTH = 1000


def _expiration_card(notification: Notification) -> dict[str, object]:
    """组装到期提醒的飞书交互卡片，带"查看资源详情"和"返回首页"按钮。"""
    kind = (
        "vm"
        if notification.target_type == NotificationTargetType.VIRTUAL_MACHINE.value
        else "physical"
    )
    return card(
        notification.title,
        [
            text_block(notification.body),
            action_block(
                [
                    button(
                        "查看资源详情",
                        "resource_detail",
                        value={
                            "resource_id": notification.target_id,
                            "kind": kind,
                            "return_action": "home",
                            "page": 0,
                        },
                    ),
                    button("返回首页", "home"),
                ]
            ),
        ],
        template="orange",
    )


def deliver_feishu_notification(db: Session, *, notification_id: str) -> None:
    """投递单条通知到飞书私聊。

    幂等守卫：已投递(SENT)或非到期提醒类型直接返回，避免重复发卡片；配置或
    身份绑定缺失时标 FAILED 而非重试。投递成功后置 SENT。
    """
    notification = db.get(Notification, notification_id)
    if notification is None:
        return
    if notification.feishu_status == FeishuDeliveryStatus.SENT.value:
        return
    if notification.notification_type != NotificationType.LEASE_EXPIRING.value:
        return

    settings = get_settings()
    config = get_enabled_feishu_app_config(db, environment=settings.app_env)
    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == ExternalIdentityProvider.FEISHU.value,
            UserIdentity.user_id == notification.recipient_user_id,
        )
    )
    if config is None or identity is None:
        notification.feishu_status = FeishuDeliveryStatus.FAILED.value
        notification.feishu_error = "Feishu app or user binding is unavailable"
        db.commit()
        return

    sender = LarkMessageSender(app_id=config.app_id, app_secret=config.app_secret)
    sender.send_card_to_open_id(identity.open_id, _expiration_card(notification))

    notification.feishu_status = FeishuDeliveryStatus.SENT.value
    notification.feishu_error = None
    notification.feishu_sent_at = now_utc()
    db.commit()


def mark_feishu_delivery_failed(
    db: Session,
    *,
    notification_id: str,
    error: str,
) -> None:
    """
    把仍处于 PENDING 的通知标为 FAILED 并截断错误信息。非 PENDING 则跳过，
    避免覆盖已 SENT 的成功状态。
    """
    notification = db.get(Notification, notification_id)
    if (
        notification is None
        or notification.feishu_status != FeishuDeliveryStatus.PENDING.value
    ):
        return
    notification.feishu_status = FeishuDeliveryStatus.FAILED.value
    notification.feishu_error = error[:FEISHU_ERROR_MAX_LENGTH]
    db.commit()

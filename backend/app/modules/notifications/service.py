# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.pagination import PAGE_SIZE, PageParams
from app.modules.feishu.models import ExternalIdentityProvider, UserIdentity
from app.modules.feishu.service import get_enabled_feishu_app_config
from app.modules.leases.models import ResourceLease
from app.modules.notifications.models import (
    FeishuDeliveryStatus,
    Notification,
    NotificationTargetType,
    NotificationType,
)
from app.modules.resources.models import Resource, ResourceType
from app.modules.tickets.models import Ticket, TicketComment, TicketStatus
from app.modules.users.models import User

# 通知领域服务：工单变更/评论通知、租约到期提醒与每日维护。
# 幂等性靠 Notification.deduplication_key 唯一约束保证：同一事件+接收人
# 只产一条通知，重复触发(如重试)不会造成重复消息。

NOTIFICATION_RETENTION_DAYS = 90
COMMENT_PREVIEW_LENGTH = 200


class NotificationNotFoundError(Exception):
    """按 ID 未找到通知或通知不属于该接收人。"""


@dataclass(frozen=True)
class TicketNotificationState:
    """工单状态快照，在状态转换前 capture，转换后用于 diff 决定通知类型与收件人。"""

    status: str
    priority: str | None
    assignee_user_id: str | None
    planned_completion_at: datetime | None

    @classmethod
    def capture(cls, ticket: Ticket) -> "TicketNotificationState":
        return cls(
            status=ticket.status,
            priority=ticket.priority,
            assignee_user_id=ticket.assignee_user_id,
            planned_completion_at=ticket.planned_completion_at,
        )


def now_utc() -> datetime:
    return datetime.now(UTC)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _display_datetime(value: datetime | None) -> str:
    if value is None:
        return "未设置"
    timezone = ZoneInfo(get_settings().display_timezone)
    return _aware_utc(value).astimezone(timezone).strftime("%Y-%m-%d %H:%M")


def _user_label(db: Session, user_id: str | None) -> str:
    if user_id is None:
        return "未设置"
    user = db.get(User, user_id)
    if user is None:
        return user_id
    return user.display_name or user.username


@dataclass(frozen=True)
class NotificationDraft:
    """一条通知的创建草稿：接收人、内容与跳转目标。"""

    recipient_user_ids: set[str | None]
    actor_user_id: str
    notification_type: NotificationType
    title: str
    body: str
    target_type: NotificationTargetType
    target_id: str
    target_url: str
    event_key: str


def _create_notifications(
    db: Session,
    *,
    draft: NotificationDraft,
) -> list[Notification]:
    recipient_user_ids = draft.recipient_user_ids
    actor_user_id = draft.actor_user_id
    notification_type = draft.notification_type
    title = draft.title
    body = draft.body
    target_type = draft.target_type
    target_id = draft.target_id
    target_url = draft.target_url
    event_key = draft.event_key
    """为每个接收人创建一条通知，发送人本人排除，避免自己触发自己。

    deduplication_key = event_key:recipient_user_id，由数据库唯一约束保证幂等，
    重复插入会因唯一冲突而在调用方层面体现，不会产生重复通知。
    """
    notifications: list[Notification] = []
    for recipient_user_id in sorted(recipient_user_ids - {None, actor_user_id}):
        notification = Notification(
            recipient_user_id=recipient_user_id,
            notification_type=notification_type.value,
            title=title,
            body=body,
            target_type=target_type.value,
            target_id=target_id,
            target_url=target_url,
            deduplication_key=f"{event_key}:{recipient_user_id}",
        )
        db.add(notification)
        notifications.append(notification)
    if notifications:
        db.flush()
    return notifications


def notify_ticket_change(
    db: Session,
    *,
    ticket: Ticket,
    actor: User,
    before: TicketNotificationState,
) -> list[Notification]:
    """对比工单转换前后的状态快照，按变化类型生成通知。

    判定优先级：责任人首次指派 > 责任人变更 > 拒绝 > 完成 > 优先级/计划时间
    更新；同一转换只产一种通知类型，收件人随类型变化(如重新指派要通知新旧
    两任责任人)。无变化则返回空。
    """
    notification_type: NotificationType | None = None
    recipients: set[str | None] = set()
    changes: list[str] = []

    assignee_changed = before.assignee_user_id != ticket.assignee_user_id
    if assignee_changed and before.assignee_user_id is None:
        notification_type = NotificationType.TICKET_ASSIGNED
        recipients = {ticket.submitter_user_id, ticket.assignee_user_id}
        changes.append(f"责任人：{_user_label(db, ticket.assignee_user_id)}")
    elif assignee_changed:
        notification_type = NotificationType.TICKET_REASSIGNED
        recipients = {
            ticket.submitter_user_id,
            before.assignee_user_id,
            ticket.assignee_user_id,
        }
        changes.append(
            "责任人："
            f"{_user_label(db, before.assignee_user_id)} -> "
            f"{_user_label(db, ticket.assignee_user_id)}"
        )
    elif before.status != ticket.status and ticket.status == TicketStatus.REJECTED.value:
        notification_type = NotificationType.TICKET_REJECTED
        recipients = {ticket.submitter_user_id}
        changes.append("状态：已拒绝")
        if ticket.rejection_reason:
            changes.append(f"拒绝理由：{ticket.rejection_reason}")
    elif before.status != ticket.status and ticket.status == TicketStatus.COMPLETED.value:
        notification_type = NotificationType.TICKET_COMPLETED
        recipients = {ticket.submitter_user_id}
        changes.append("状态：已完成")
    elif (
        before.priority != ticket.priority
        or before.planned_completion_at != ticket.planned_completion_at
    ):
        notification_type = NotificationType.TICKET_UPDATED
        recipients = {ticket.submitter_user_id}

    if before.priority != ticket.priority:
        changes.append(f"优先级：{before.priority or '未设置'} -> {ticket.priority or '未设置'}")
    if before.planned_completion_at != ticket.planned_completion_at:
        changes.append(
            "计划完成时间："
            f"{_display_datetime(before.planned_completion_at)} -> "
            f"{_display_datetime(ticket.planned_completion_at)}"
        )
    if notification_type is None:
        return []

    title = {
        NotificationType.TICKET_ASSIGNED: f"工单 #{ticket.id} 已接受并指派",
        NotificationType.TICKET_REASSIGNED: f"工单 #{ticket.id} 已重新指派",
        NotificationType.TICKET_REJECTED: f"工单 #{ticket.id} 已拒绝",
        NotificationType.TICKET_COMPLETED: f"工单 #{ticket.id} 已完成",
        NotificationType.TICKET_UPDATED: f"工单 #{ticket.id} 处理信息已更新",
    }[notification_type]

    return _create_notifications(
        db,
        draft=NotificationDraft(
            recipient_user_ids=recipients,
            actor_user_id=actor.id,
            notification_type=notification_type,
            title=title,
            body=f"{ticket.title}\n" + "；".join(changes),
            target_type=NotificationTargetType.TICKET,
            target_id=str(ticket.id),
            target_url=f"/tickets/{ticket.id}",
            event_key=f"ticket:{ticket.id}:change:{uuid4()}",
        ),
    )


def notify_ticket_comment(
    db: Session,
    *,
    ticket: Ticket,
    comment: TicketComment,
    actor: User,
) -> list[Notification]:
    preview = comment.body[:COMMENT_PREVIEW_LENGTH]
    if len(comment.body) > COMMENT_PREVIEW_LENGTH:
        preview += "..."
    return _create_notifications(
        db,
        draft=NotificationDraft(
            recipient_user_ids={ticket.submitter_user_id, ticket.assignee_user_id},
            actor_user_id=actor.id,
            notification_type=NotificationType.TICKET_COMMENTED,
            title=f"工单 #{ticket.id} 有新评论",
            body=f"{ticket.title}\n{actor.display_name or actor.username}：{preview}",
            target_type=NotificationTargetType.TICKET,
            target_id=str(ticket.id),
            target_url=f"/tickets/{ticket.id}",
            event_key=f"ticket:{ticket.id}:comment:{comment.id}",
        ),
    )


def _reminder_window(now: datetime, timezone: ZoneInfo) -> tuple[date, datetime]:
    """计算到期提醒窗口：返回(本地今天, 未来4天对应的 UTC 上界)。

    窗口宽 4 天覆盖剩余 1~3 天的到期租约(今天+1/2/3)，上界用本地零点换算
    回 UTC，保证跨时区下不漏不重。
    """
    local_today = now.astimezone(timezone).date()
    upper_local = datetime.combine(local_today + timedelta(days=4), time.min, timezone)
    return local_today, upper_local.astimezone(UTC)


def create_expiration_reminders(
    db: Session,
    *,
    current_time: datetime | None = None,
) -> list[str]:
    """扫描未来 1~3 天到期的未释放租约，为每个租约人生成到期提醒。

    幂等：deduplication_key 含租约/到期日/提醒日/用户，同一天对同一租约
    只产一条，重复执行(每日调度)不会刷屏。仅当接收人绑定了飞书身份时
    feishu_status 置 PENDING 并返回其通知 ID，由投递任务异步发飞书卡片。
    """
    now = current_time or now_utc()
    settings = get_settings()
    timezone = ZoneInfo(settings.display_timezone)
    local_today, upper_time = _reminder_window(now, timezone)
    feishu_config = get_enabled_feishu_app_config(db, environment=settings.app_env)
    statement = (
        select(ResourceLease, Resource)
        .join(Resource, Resource.id == ResourceLease.resource_id)
        .where(
            ResourceLease.released_at.is_(None),
            ResourceLease.expected_ends_at.is_not(None),
            ResourceLease.expected_ends_at > now,
            ResourceLease.expected_ends_at < upper_time,
            Resource.deleted_at.is_(None),
        )
    )
    pending_feishu_ids: list[str] = []
    for lease, resource in db.execute(statement).all():
        expected_ends_at = lease.expected_ends_at
        if expected_ends_at is None:
            continue
        expected_ends_at = _aware_utc(expected_ends_at)
        days_left = (expected_ends_at.astimezone(timezone).date() - local_today).days
        if days_left not in {1, 2, 3}:
            continue
        reminder_date = local_today.isoformat()
        deduplication_key = (
            f"lease:{lease.id}:ends:{expected_ends_at.isoformat()}:"
            f"reminder:{reminder_date}:user:{lease.user_id}"
        )
        existing = db.scalar(
            select(Notification.id).where(
                Notification.deduplication_key == deduplication_key
            )
        )
        if existing is not None:
            continue

        is_vm = resource.resource_type == ResourceType.VIRTUAL.value
        resource_label = (
            resource.virtual_spec.vm_name
            if is_vm and resource.virtual_spec and resource.virtual_spec.vm_name
            else resource.primary_ip or "未设置"
        )
        kind_label = "VM" if is_vm else "物理机"
        identity = None
        if feishu_config is not None:
            identity = db.scalar(
                select(UserIdentity).where(
                    UserIdentity.provider == ExternalIdentityProvider.FEISHU.value,
                    UserIdentity.user_id == lease.user_id,
                )
            )
        notification = Notification(
            recipient_user_id=lease.user_id,
            notification_type=NotificationType.LEASE_EXPIRING.value,
            title=f"{kind_label}将在 {days_left} 天后到期",
            body=(
                f"{kind_label}：{resource_label}\n"
                f"到期时间：{_display_datetime(expected_ends_at)}\n"
                f"剩余：{days_left} 天"
            ),
            target_type=(
                NotificationTargetType.VIRTUAL_MACHINE.value
                if is_vm
                else NotificationTargetType.PHYSICAL_RESOURCE.value
            ),
            target_id=resource.id,
            target_url=(
                f"/virtual-machines?vm_id={resource.id}"
                if is_vm
                else f"/resources?resource_id={resource.id}"
            ),
            deduplication_key=deduplication_key,
            feishu_status=(
                FeishuDeliveryStatus.PENDING.value if identity is not None else None
            ),
        )
        db.add(notification)
        db.flush()
        if notification.feishu_status == FeishuDeliveryStatus.PENDING.value:
            pending_feishu_ids.append(notification.id)
    return pending_feishu_ids


def cleanup_expired_notifications(
    db: Session,
    *,
    current_time: datetime | None = None,
) -> int:
    """删除超过 NOTIFICATION_RETENTION_DAYS 的通知，返回删除条数。"""
    cutoff = (current_time or now_utc()) - timedelta(days=NOTIFICATION_RETENTION_DAYS)
    statement = delete(Notification).where(Notification.created_at < cutoff)
    result = db.execute(statement.execution_options(synchronize_session=False))
    return result.rowcount or 0


def run_daily_maintenance(
    db: Session,
    *,
    current_time: datetime | None = None,
) -> list[str]:
    """每日维护：先生成到期提醒，再清理过期通知。返回需投递飞书的通知 ID。"""
    pending_feishu_ids = create_expiration_reminders(db, current_time=current_time)
    cleanup_expired_notifications(db, current_time=current_time)
    return pending_feishu_ids


def paginate_notifications(
    db: Session,
    *,
    user_id: str,
    pagination: PageParams,
) -> tuple[list[Notification], int]:
    base = select(Notification).where(Notification.recipient_user_id == user_id)
    total = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.recipient_user_id == user_id
        )
    ) or 0
    statement = (
        base.order_by(
            Notification.read_at.is_(None).desc(),
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .offset(pagination.offset)
        .limit(PAGE_SIZE)
    )
    return list(db.scalars(statement).all()), total


def unread_notification_count(db: Session, *, user_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.recipient_user_id == user_id,
            Notification.read_at.is_(None),
        )
    ) or 0


def mark_notification_read(
    db: Session,
    *,
    user_id: str,
    notification_id: str,
) -> Notification:
    """标记单条通知已读。按 (notification_id, user_id) 定位，防止越权读他人通知。"""
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
        )
    )
    if notification is None:
        raise NotificationNotFoundError
    if notification.read_at is None:
        notification.read_at = now_utc()
        db.flush()
    return notification


def mark_all_notifications_read(db: Session, *, user_id: str) -> int:
    result = db.execute(
        update(Notification)
        .where(
            Notification.recipient_user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now_utc())
    )
    return result.rowcount or 0

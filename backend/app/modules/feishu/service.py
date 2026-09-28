# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.audit.service import record_audit_log
from app.modules.feishu.models import (
    ExternalIdentityProvider,
    FeishuAppConfig,
    UserIdentity,
)
from app.modules.feishu.schemas import FeishuAppConfigUpsert, FeishuIdentityBind
from app.modules.users.models import User

# 飞书集成服务：应用配置(每环境一套)与用户身份绑定(open_id/union_id)。
# 身份查找优先匹配 union_id，其次 open_id，保证飞书账号在 open_id 变化后
# 仍能稳定关联到同一 radiaTest 用户。


class FeishuIdentityConflictError(Exception):
    """飞书身份已被其他 radiaTest 用户绑定，拒绝重复绑定。"""


def get_feishu_app_config(db: Session, *, environment: str) -> FeishuAppConfig | None:
    statement = select(FeishuAppConfig).where(FeishuAppConfig.environment == environment)
    return db.execute(statement).scalar_one_or_none()


def get_enabled_feishu_app_config(
    db: Session,
    *,
    environment: str,
) -> FeishuAppConfig | None:
    config = get_feishu_app_config(db, environment=environment)
    if config is None or not config.is_enabled:
        return None
    return config


def serialize_feishu_app_config(config: FeishuAppConfig) -> dict[str, object]:
    return {
        "id": config.id,
        "environment": config.environment,
        "app_id": config.app_id,
        "is_enabled": config.is_enabled,
        "has_app_secret": bool(config.app_secret),
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


def upsert_feishu_app_config(
    db: Session,
    *,
    actor: User,
    environment: str,
    payload: FeishuAppConfigUpsert,
) -> FeishuAppConfig:
    config = get_feishu_app_config(db, environment=environment)
    before = None
    if config is None:
        config = FeishuAppConfig(
            environment=environment,
            app_id=payload.app_id,
            app_secret=payload.app_secret,
            is_enabled=payload.is_enabled,
            created_by_user_id=actor.id,
        )
        db.add(config)
    else:
        before = {
            "app_id": config.app_id,
            "is_enabled": config.is_enabled,
            "has_app_secret": bool(config.app_secret),
        }
        config.app_id = payload.app_id
        config.app_secret = payload.app_secret
        config.is_enabled = payload.is_enabled

    db.flush()
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="feishu_app_config.upsert",
        target_type="feishu_app_config",
        target_id=config.id,
        detail={
            "environment": config.environment,
            "before": before,
            "after": {
                "app_id": config.app_id,
                "is_enabled": config.is_enabled,
                "has_app_secret": bool(config.app_secret),
            },
        },
    )
    return config


def get_user_feishu_identity(db: Session, *, user_id: str) -> UserIdentity | None:
    statement = select(UserIdentity).where(
        UserIdentity.provider == ExternalIdentityProvider.FEISHU.value,
        UserIdentity.user_id == user_id,
    )
    return db.execute(statement).scalar_one_or_none()


def find_feishu_identity(
    db: Session,
    *,
    open_id: str,
    union_id: str | None = None,
) -> UserIdentity | None:
    """按 open_id/union_id 查找飞书身份记录。

    优先按 union_id 匹配(更稳定，open_id 可变)，故 union_id 条件插到列表
    头部被 or_ 先求值。结果按 union_id 非空优先、再按创建时间排序，确保
    多个历史记录时取最确定的那条。
    """
    conditions = [UserIdentity.open_id == open_id]
    if union_id:
        conditions.insert(0, UserIdentity.union_id == union_id)
    statement = (
        select(UserIdentity)
        .where(
            UserIdentity.provider == ExternalIdentityProvider.FEISHU.value,
            or_(*conditions),
        )
        .order_by(UserIdentity.union_id.is_(None), UserIdentity.created_at)
    )
    return db.execute(statement).scalars().first()


def get_bound_user_for_feishu_actor(
    db: Session,
    *,
    open_id: str,
    union_id: str | None = None,
) -> User | None:
    """把飞书消息发起者解析为已绑定的 radiaTest 用户。未绑定或用户已禁用返回 None。"""
    identity = find_feishu_identity(db, open_id=open_id, union_id=union_id)
    if identity is None:
        return None
    user = db.get(User, identity.user_id)
    if user is None or not user.is_active:
        return None
    return user


def bind_feishu_identity(
    db: Session,
    *,
    actor: User,
    payload: FeishuIdentityBind,
) -> UserIdentity:
    """把当前 radiaTest 用户与飞书身份绑定，同一身份不能绑到别的用户。

    已被其他用户绑定时抛 FeishuIdentityConflictError；同一用户重复绑定则
    更新 open_id/union_id。绑定前后状态写入审计日志。
    """
    existing = find_feishu_identity(db, open_id=payload.open_id, union_id=payload.union_id)
    if existing is not None and existing.user_id != actor.id:
        raise FeishuIdentityConflictError("Feishu identity is already bound")

    identity = get_user_feishu_identity(db, user_id=actor.id)
    before = None
    if identity is None:
        identity = UserIdentity(
            user_id=actor.id,
            provider=ExternalIdentityProvider.FEISHU.value,
            open_id=payload.open_id,
            union_id=payload.union_id,
        )
        db.add(identity)
    else:
        before = {
            "open_id": identity.open_id,
            "union_id": identity.union_id,
        }
        identity.open_id = payload.open_id
        identity.union_id = payload.union_id

    db.flush()
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="user_identity.bind",
        target_type="user_identity",
        target_id=identity.id,
        detail={
            "provider": identity.provider,
            "before": before,
            "after": {
                "open_id": identity.open_id,
                "union_id": identity.union_id,
            },
        },
    )
    return identity

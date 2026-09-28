# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.users.models import User

# 飞书集成数据模型：每环境一套应用配置 + 用户外部身份绑定 + 消息幂等回执。


class ExternalIdentityProvider(StrEnum):
    """外部身份提供方，当前仅飞书。"""

    FEISHU = "feishu"


def utc_now() -> datetime:
    return datetime.now(UTC)


class FeishuAppConfig(Base):
    """飞书应用配置，按环境唯一(dev/prod 各一套 app_id/app_secret)。"""

    __tablename__ = "feishu_app_configs"
    __table_args__ = (
        UniqueConstraint("environment", name="uq_feishu_app_configs_environment"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    environment: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    app_id: Mapped[str] = mapped_column(String(128), nullable=False)
    app_secret: Mapped[str] = mapped_column(String(512), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class UserIdentity(Base):
    """用户外部身份绑定记录，一个 radiaTest 用户可绑定一个飞书身份。

    不可破坏约束(provider,user)、(provider,open_id)、(provider,union_id)
    三重唯一，分别保证：一个用户一种身份类型只绑一条、一个 open_id/union_id
    不能绑到多个用户。union_id 可空(应用未返回时)。
    """

    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "user_id", name="uq_user_identities_provider_user"),
        UniqueConstraint("provider", "open_id", name="uq_user_identities_provider_open_id"),
        UniqueConstraint("provider", "union_id", name="uq_user_identities_provider_union_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    open_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    union_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped[User] = relationship()


class FeishuMessageReceipt(Base):
    """飞书消息幂等回执，message_id 作主键，保证一条消息只处理一次。"""

    __tablename__ = "feishu_message_receipts"

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )

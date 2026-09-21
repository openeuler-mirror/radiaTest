# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import UTC, datetime

from pwdlib import PasswordHash
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.modules.audit.service import record_audit_log
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import (
    PasswordChange,
    PasswordReset,
    UserCreate,
    UserListParams,
    UserUpdate,
    normalize_display_name,
    validate_display_name,
    validate_password,
    validate_username,
)

password_hash = PasswordHash.recommended()

# 用户领域服务：创建/更新/重置密码、鉴权与最后管理员守卫。
# 角色权限(ADMIN/TSE/TE)的最终边界在此判定，前端可见性仅用于体验。


class UserAlreadyExistsError(Exception):
    """用户名已存在。"""


class UserNotFoundError(Exception):
    """按 ID 未找到用户。"""


class UserPolicyError(Exception):
    """用户管理策略被拒(禁用最后管理员、自降级等)。"""


class InvalidCurrentPasswordError(Exception):
    """修改密码时当前密码不正确。"""


def hash_password(password: str) -> str:
    """用 argon2 哈希密码，只存哈希不存明文。"""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """校验明文密码与 argon2 哈希是否匹配。"""
    return password_hash.verify(password, hashed_password)


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.execute(statement).scalar_one_or_none()


def count_active_admins(db: Session) -> int:
    """统计启用状态的管理员数量，用于最后管理员守卫。"""
    statement = select(func.count()).select_from(User).where(
        User.role == UserRole.ADMIN.value,
        User.is_active.is_(True),
    )
    return db.execute(statement).scalar_one()


def list_users(
    db: Session,
    *,
    params: UserListParams,
    offset: int = 0,
    limit: int = 50,
) -> list[User]:
    conditions = []
    if params.username:
        conditions.append(User.username.ilike(f"%{params.username}%"))
    if params.display_name:
        conditions.append(User.display_name.ilike(f"%{params.display_name}%"))
    if params.role:
        conditions.append(User.role == params.role.value)
    if params.is_active is not None:
        conditions.append(User.is_active.is_(params.is_active))

    statement = select(User)
    if conditions:
        statement = statement.where(and_(*conditions))
    statement = statement.order_by(User.created_at.desc(), User.id).offset(offset).limit(limit)
    return list(db.execute(statement).scalars().all())


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: UserRole,
    display_name: str | None = None,
) -> User:
    """创建用户：校验用户名/密码/显示名合法性，重名校验后建用户。不提交，由调用方控制事务。"""
    username = validate_username(username)
    password = validate_password(password)
    display_name = validate_display_name(display_name)
    if get_user_by_username(db, username) is not None:
        raise UserAlreadyExistsError(username)

    user = User(
        username=username,
        display_name=display_name,
        role=role.value,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.flush()
    return user


def create_managed_user(db: Session, *, actor: User, payload: UserCreate) -> User:
    user = create_user(
        db,
        username=payload.username,
        password=payload.password,
        role=payload.role,
        display_name=payload.display_name,
    )
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="user.create",
        target_type="user",
        target_id=user.id,
        detail={
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "is_active": user.is_active,
        },
    )
    return user


def get_managed_user(db: Session, user_id: str) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


def ensure_user_update_allowed(
    db: Session,
    *,
    actor: User,
    target: User,
    payload: UserUpdate,
) -> None:
    """更新用户的鉴权与策略守卫(最终边界)。

    不可破坏约束：
    - 管理员不能禁用或降级自己(避免把自己锁死)。
    - 不能禁用或降级最后一个启用状态的管理员(避免无管理员可用)。
    """
    target_will_be_disabled = payload.is_active is False and target.is_active
    target_will_be_demoted = (
        payload.role is not None
        and payload.role != UserRole.ADMIN
        and target.role == UserRole.ADMIN.value
    )

    if target.id == actor.id:
        if target_will_be_disabled:
            raise UserPolicyError("Admin cannot disable self")
        if target_will_be_demoted:
            raise UserPolicyError("Admin cannot demote self")

    if target.role == UserRole.ADMIN.value and target.is_active:
        if target_will_be_disabled or target_will_be_demoted:
            if count_active_admins(db) <= 1:
                raise UserPolicyError("Cannot disable or demote the last active admin")


def update_managed_user(
    db: Session,
    *,
    actor: User,
    target: User,
    payload: UserUpdate,
) -> User:
    ensure_user_update_allowed(db, actor=actor, target=target, payload=payload)
    before = {
        "display_name": target.display_name,
        "role": target.role,
        "is_active": target.is_active,
    }

    if "display_name" in payload.model_fields_set:
        target.display_name = normalize_display_name(payload.display_name)
    if payload.role is not None:
        target.role = payload.role.value
    if payload.is_active is not None:
        target.is_active = payload.is_active

    db.flush()
    after = {
        "display_name": target.display_name,
        "role": target.role,
        "is_active": target.is_active,
    }
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="user.update",
        target_type="user",
        target_id=target.id,
        detail={"before": before, "after": after},
    )
    return target


def reset_managed_user_password(
    db: Session,
    *,
    actor: User,
    target: User,
    payload: PasswordReset,
) -> None:
    """管理员重置他人密码。策略：不能通过此入口重置自己(自改走 change_own_password)。"""
    if actor.id == target.id:
        raise UserPolicyError("Admin cannot reset own password through user management")
    target.password_hash = hash_password(validate_password(payload.password))
    db.flush()
    record_audit_log(
        db,
        actor_user_id=actor.id,
        action="user.reset_password",
        target_type="user",
        target_id=target.id,
        detail={"username": target.username},
    )


def change_own_password(
    db: Session,
    *,
    user: User,
    payload: PasswordChange,
) -> None:
    """用户自行修改密码：须校验当前密码正确后再设新密码。"""
    if not verify_password(payload.old_password, user.password_hash):
        raise InvalidCurrentPasswordError()
    user.password_hash = hash_password(validate_password(payload.password))
    db.flush()
    record_audit_log(
        db,
        actor_user_id=user.id,
        action="user.change_own_password",
        target_type="user",
        target_id=user.id,
        detail={"username": user.username},
    )


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    用户名+密码登录校验。用户不存在、被禁用或密码不符均返回 None
    (不区分，避免枚举用户名)。
    """
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def mark_login_success(user: User) -> None:
    user.last_login_at = datetime.now(UTC)

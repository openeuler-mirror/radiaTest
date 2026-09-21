# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.modules.users.models import UserRole

USERNAME_PATTERN = re.compile(r"^[a-z0-9]{3,64}$")
MIN_PASSWORD_LENGTH = 8
MAX_DISPLAY_NAME_LENGTH = 128


def normalize_display_name(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def validate_username(value: str) -> str:
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError("username must be 3-64 lowercase letters or digits")
    return value


def validate_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError("password must be at least 8 characters")
    return value


def validate_display_name(value: str | None) -> str | None:
    normalized = normalize_display_name(value)
    if normalized is not None and len(normalized) > MAX_DISPLAY_NAME_LENGTH:
        raise ValueError("display_name must be at most 128 characters")
    return normalized


class UserRead(BaseModel):
    id: str
    username: str
    display_name: str | None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str
    display_name: str | None = None
    role: UserRole
    password: str

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, value: str) -> str:
        return validate_username(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name_field(cls, value: str | None) -> str | None:
        return validate_display_name(value)

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: str) -> str:
        return validate_password(value)


class UserListParams(BaseModel):
    username: str | None = None
    display_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("username", "display_name")
    @classmethod
    def normalize_filter_value(cls, value: str | None) -> str | None:
        return normalize_display_name(value)


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name_field(cls, value: str | None) -> str | None:
        return validate_display_name(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be set")
        return self


class PasswordReset(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: str) -> str:
        return validate_password(value)


class PasswordChange(BaseModel):
    old_password: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: str) -> str:
        return validate_password(value)

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

# 飞书集成 Pydantic 模型：应用配置读写、身份绑定、绑定 URL。

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_required_token(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("value must not be empty")
    return stripped


def normalize_optional_token(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class FeishuAppConfigUpsert(BaseModel):
    app_id: str = Field(min_length=1, max_length=128)
    app_secret: str = Field(min_length=1, max_length=512)
    is_enabled: bool = True

    @field_validator("app_id", "app_secret")
    @classmethod
    def normalize_required_field(cls, value: str) -> str:
        return normalize_required_token(value)


class FeishuAppConfigRead(BaseModel):
    id: str
    environment: str
    app_id: str
    is_enabled: bool
    has_app_secret: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeishuIdentityRead(BaseModel):
    id: str
    user_id: str
    provider: str
    open_id: str
    union_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeishuBindUrlRead(BaseModel):
    authorize_url: str


class FeishuIdentityBind(BaseModel):
    open_id: str = Field(min_length=1, max_length=128)
    union_id: str | None = Field(default=None, max_length=128)

    @field_validator("open_id")
    @classmethod
    def normalize_open_id(cls, value: str) -> str:
        return normalize_required_token(value)

    @field_validator("union_id")
    @classmethod
    def normalize_union_id(cls, value: str | None) -> str | None:
        return normalize_optional_token(value)

    @model_validator(mode="after")
    def require_distinct_ids(self) -> "FeishuIdentityBind":
        if self.union_id is not None and self.union_id == self.open_id:
            raise ValueError("union_id must be different from open_id")
        return self

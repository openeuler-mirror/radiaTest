# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


def normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class AuditLogListParams(BaseModel):
    action: str | None = None
    actor_username: str | None = None
    target_type: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None

    @field_validator("action", "actor_username", "target_type")
    @classmethod
    def normalize_text_filter(cls, value: str | None) -> str | None:
        return normalize_filter(value)


class AuditLogRead(BaseModel):
    id: str
    actor_user_id: str | None
    actor_username: str | None
    action: str
    target_type: str
    target_id: str | None
    detail: dict[str, object]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

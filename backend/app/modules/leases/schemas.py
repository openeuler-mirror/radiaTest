# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LeaseCreate(BaseModel):
    purpose: str = Field(min_length=1, max_length=512)
    expected_ends_at: datetime | None = None


class LeaseRelease(BaseModel):
    reason: str | None = Field(default=None, max_length=512)


class LeaseExtend(BaseModel):
    expected_ends_at: datetime


class LeaseRead(BaseModel):
    id: str
    resource_id: str
    user_id: str
    username: str | None
    purpose: str
    starts_at: datetime
    expected_ends_at: datetime | None
    released_at: datetime | None
    released_by_user_id: str | None
    release_reason: str | None


class LeaseEventListParams(BaseModel):
    event_type: str | None = None
    actor_username: str | None = None
    resource_code: str | None = None
    resource_type: str | None = None
    primary_ip: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None

    @field_validator(
        "event_type",
        "actor_username",
        "resource_code",
        "resource_type",
        "primary_ip",
    )
    @classmethod
    def normalize_text_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class LeaseEventRead(BaseModel):
    id: str
    lease_id: str
    resource_id: str
    resource_code: str | None
    primary_ip: str | None
    resource_type: str | None
    actor_user_id: str | None
    actor_username: str | None
    event_type: str
    detail: dict[str, object]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IdempotentResponse(BaseModel):
    body: dict[str, object]
    status_code: int


class ResourceCredentialRead(BaseModel):
    ssh_username: str
    ssh_password: str | None
    bmc_username: str | None = None
    bmc_password: str | None = None


class ResourceSshCredentialRead(BaseModel):
    ssh_username: str
    ssh_password: str | None


class LeaseCreateForRole(LeaseCreate):
    @model_validator(mode="after")
    def normalize_purpose(self) -> "LeaseCreateForRole":
        self.purpose = self.purpose.strip()
        return self


class LeaseReleaseNormalized(LeaseRelease):
    @model_validator(mode="after")
    def normalize_reason(self) -> "LeaseReleaseNormalized":
        if self.reason is not None:
            self.reason = self.reason.strip() or None
        return self


class LeaseImportRequest(BaseModel):
    filename: str | None = None
    content: str = Field(min_length=1)
    dry_run: bool = False


class LeaseImportRowResult(BaseModel):
    row_number: int
    resource_code: str | None = None
    primary_ip: str | None = None
    status: Literal["created", "error", "validated"]
    errors: list[str] = Field(default_factory=list)


class LeaseImportResult(BaseModel):
    dry_run: bool
    total_rows: int
    success_count: int
    error_count: int
    rows: list[LeaseImportRowResult]

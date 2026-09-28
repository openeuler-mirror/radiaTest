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

from app.modules.tickets.models import TicketPriority, TicketStatus, TicketType

MAX_TITLE_LENGTH = 120
MAX_BODY_LENGTH = 10_000
MAX_REASON_LENGTH = 2_000
MAX_COMMENT_LENGTH = 5_000


def validate_required_text(value: str, *, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


class TicketCreate(BaseModel):
    ticket_type: TicketType = TicketType.REQ
    title: str = Field(max_length=MAX_TITLE_LENGTH)
    body: str = Field(max_length=MAX_BODY_LENGTH)

    @field_validator("title", "body")
    @classmethod
    def require_text(cls, value: str, info) -> str:
        return validate_required_text(value, field_name=info.field_name)


class TicketContentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    body: str | None = Field(default=None, max_length=MAX_BODY_LENGTH)

    @field_validator("title", "body")
    @classmethod
    def require_text(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return validate_required_text(value, field_name=info.field_name)

    @model_validator(mode="after")
    def require_update(self) -> "TicketContentUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be set")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("ticket content fields must not be null")
        return self


class TicketAccept(BaseModel):
    priority: TicketPriority
    assignee_user_id: str
    planned_completion_at: datetime


class TicketReject(BaseModel):
    reason: str = Field(max_length=MAX_REASON_LENGTH)

    @field_validator("reason")
    @classmethod
    def require_reason(cls, value: str) -> str:
        return validate_required_text(value, field_name="reason")


class TicketHandlingUpdate(BaseModel):
    priority: TicketPriority | None = None
    assignee_user_id: str | None = None
    planned_completion_at: datetime | None = None

    @model_validator(mode="after")
    def require_update(self) -> "TicketHandlingUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be set")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("handling fields must not be null")
        return self


class TicketCommentCreate(BaseModel):
    body: str = Field(max_length=MAX_COMMENT_LENGTH)

    @field_validator("body")
    @classmethod
    def require_body(cls, value: str) -> str:
        return validate_required_text(value, field_name="body")


class TicketListParams(BaseModel):
    match: Literal["and", "or"] = "and"
    ticket_id: int | None = Field(default=None, ge=1)
    submitter: str | None = None
    title: str | None = None
    ticket_type: TicketType | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | Literal["UNSET"] | None = None
    assignee: str | None = None

    @field_validator("submitter", "title", "assignee")
    @classmethod
    def normalize_text_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class TicketCommentRead(BaseModel):
    id: str
    author_user_id: str
    author_username: str
    author_display_name: str | None
    body: str
    created_at: datetime


class TicketRead(BaseModel):
    id: int
    submitter_user_id: str
    submitter_username: str
    submitter_display_name: str | None
    ticket_type: TicketType
    title: str
    body: str
    status: TicketStatus
    priority: TicketPriority | None
    assignee_user_id: str | None
    assignee_username: str | None
    assignee_display_name: str | None
    planned_completion_at: datetime | None
    completed_at: datetime | None
    rejection_reason: str | None
    is_overdue: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketDetailRead(TicketRead):
    comments: list[TicketCommentRead]

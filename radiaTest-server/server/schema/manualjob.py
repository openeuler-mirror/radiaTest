from typing import Optional
from pydantic import BaseModel, root_validator
from server.schema.base import PageBaseSchema, PermissionBase


class ManualJobCreate(PermissionBase):
    cases: str
    name: str
    milestone_id: int


class ManualJobQuery(PageBaseSchema):
    status: int
    case_id: Optional[int]
    name: Optional[str]


class ManualJobLogModify(BaseModel):
    step: int
    content: Optional[str]
    passed: Optional[bool]


class ManualJobLogDelete(BaseModel):
    step: Optional[int]

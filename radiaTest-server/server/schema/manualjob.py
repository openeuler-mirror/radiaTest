from typing import Optional
from pydantic import BaseModel

from server.schema.base import PageBaseSchema


class ManualJobCreate(BaseModel):
    case_id: int
    name: str
    milestone_id: int


class ManualJobQuery(PageBaseSchema):
    status: int


class ManualJobStatusModify(BaseModel):
    status: int


class ManualJobResultModify(BaseModel):
    result: Optional[str]


class ManualJobLogModify(BaseModel):
    step: int
    content: Optional[str]
    passed: Optional[bool]


class ManualJobLogDelete(BaseModel):
    step: Optional[int]

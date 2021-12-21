from typing import List, Optional

from pydantic import BaseModel, constr

from server.schema.base import UpdateBaseModel


class TemplateBase(BaseModel):
    name: constr(max_length=128)
    description: Optional[constr(max_length=255)]
    cases: List[str]
    milestone_id: int
    author: Optional[str]
    owner: Optional[str]
    template_type: Optional[str]


class TemplateUpdate(TemplateBase, UpdateBaseModel):
    name: Optional[constr(max_length=128)]
    milestone_id: Optional[int]
    cases: Optional[List[str]]

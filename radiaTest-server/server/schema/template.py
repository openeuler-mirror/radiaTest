from typing import List, Optional

from pydantic import BaseModel, constr

from server.schema.base import PermissionBase


class TemplateBase(BaseModel):
    name: constr(max_length=128)
    description: Optional[constr(max_length=255)]
    cases: List[str]
    milestone_id: int
    git_repo_id: int = 1


class TemplateUpdate(TemplateBase):
    name: Optional[constr(max_length=128)]
    milestone_id: Optional[int]
    git_repo_id: Optional[int]
    cases: Optional[List[str]]
    description: Optional[constr(max_length=255)]


class TemplateCloneBase(PermissionBase):
    id: int


class TemplateCreateBase(PermissionBase):
    name: constr(max_length=128)
    description: Optional[constr(max_length=255)]
    cases: List[str]
    milestone_id: int
    git_repo_id: int = 1


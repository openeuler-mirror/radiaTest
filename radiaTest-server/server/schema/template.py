from typing import List, Optional

from pydantic import BaseModel, constr

from server.schema.base import PermissionBase


class TemplateUpdate(BaseModel):
    name: Optional[constr(max_length=128)]
    milestone_id: Optional[int]
    git_repo_id: Optional[int]
    description: Optional[constr(max_length=255)]


class TemplateCloneBase(PermissionBase):
    id: int


class TemplateCreateByimportFile(PermissionBase):
    name: constr(max_length=128)
    description: Optional[constr(max_length=255)]
    milestone_id: int
    git_repo_id: int


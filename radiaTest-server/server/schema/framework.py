from typing import Optional

from pydantic import BaseModel, validator
from pydantic.networks import HttpUrl
from server.schema.base import PermissionBase
from server.schema import PermissionType


class FrameworkBase(PermissionBase):
    name: str
    url: HttpUrl
    logs_path: str
    adaptive: bool = False

    @validator("permission_type")
    def check_permission_type(cls, v):
        if v != "group":
            raise ValueError("framework's permission_type must be group.")
        return v


class FrameworkQuery(BaseModel):
    name: Optional[str]
    url: Optional[HttpUrl]
    logs_path: Optional[str]
    adaptive: Optional[bool]


class GitRepoBase(PermissionBase):
    name: str
    git_url: HttpUrl
    sync_rule: bool = True
    framework_id: int

    @validator("permission_type")
    def check_permission_type(cls, v):
        if v != "group":
            raise ValueError("gitrepo's permission_type must be group.")
        return v

class GitRepoQuery(BaseModel):
    name: Optional[str]
    git_url: Optional[HttpUrl]
    sync_rule: Optional[bool]
    framework_id: Optional[int]
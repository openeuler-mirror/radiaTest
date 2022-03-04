import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic.networks import HttpUrl


class FrameworkBase(BaseModel):
    name: str
    url: HttpUrl
    logs_path: str
    adaptive: bool


class FrameworkQuery(BaseModel):
    name: Optional[str]
    url: Optional[HttpUrl]
    logs_path: Optional[str]
    adaptive: Optional[bool]


class GitRepoBase(BaseModel):
    name: str
    git_url: HttpUrl
    sync_rule: bool = True
    framework_id: int


class GitRepoQuery(BaseModel):
    name: Optional[str]
    git_url: Optional[HttpUrl]
    sync_rule: Optional[bool]
    framework_id: Optional[int]
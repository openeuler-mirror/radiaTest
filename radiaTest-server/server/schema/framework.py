# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from typing import Optional
from typing_extensions import Literal

from pydantic import BaseModel, root_validator, validator
from pydantic.networks import HttpUrl
from server.schema.base import PermissionBase


class FrameworkBase(PermissionBase):
    name: str
    url: HttpUrl
    logs_path: str
    adaptive: bool = False

    @validator("permission_type")
    def check_permission_type(cls, v):
        if v != "public":
            raise ValueError("framework's permission_type must be public.")
        return v


class FrameworkQuery(BaseModel):
    name: Optional[str]
    url: Optional[HttpUrl]
    logs_path: Optional[str]
    adaptive: Optional[bool]
    org_id: int = None


class GitRepoBase(PermissionBase):
    name: str
    git_url: HttpUrl
    branch: str
    sync_rule: bool = True
    framework_id: int


class GitRepoQuery(BaseModel):
    name: Optional[str]
    git_url: Optional[HttpUrl]
    branch: Optional[str]
    sync_rule: Optional[bool]
    framework_id: Optional[int]


class GitRepoScopedQuery(GitRepoQuery):
    type: Literal["group", "org"]
    group_id: Optional[int]
    org_id: Optional[int]

    @root_validator
    def check_id(cls, values):
        if values.get("type") == "group" and not values.get("group_id"):
            raise ValueError("could not query git repos for unknown group")
        elif values.get("type") == "org" and not values.get("org_id"):
            raise ValueError("could not query git repos for unknown organization")
        
        return values

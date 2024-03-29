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

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from .base import PageBaseSchema


class ReUserGroupSchema(BaseModel):
    re_user_group_id: int = Field(alias='id')
    user_add_group_flag: bool = Field(alias='user_add_group_flag')
    re_user_group_is_delete: bool = Field(alias="is_delete")
    re_user_group_role_type: int = Field(alias="role_type")
    re_user_group_create_time: str = Field(alias="create_time")
    role: dict = None

    @validator("re_user_group_create_time")
    def check_time_format(cls, v):
        try:
            v = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            raise RuntimeError("the format of create_time is not valid, the valid type is: %Y-%m-%d %H:%M:%S") from e

        return v


class AddGroupSchema(BaseModel):
    name: str
    description: Optional[str]


class UpdateGroupSchema(BaseModel):
    name: str
    description: Optional[str]
    avatar_url: Optional[str]


class GroupInfoSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    is_delete: Optional[bool]
    create_time: Optional[str]


class AddGroupUserSchema(BaseModel):
    user_ids: list


class UpdateGroupUserSchema(BaseModel):
    user_ids: list
    is_delete: Optional[bool] = False
    flag: Optional[bool] = True
    role_type: Optional[int]


class QueryGroupUserSchema(PageBaseSchema):
    except_list: str = None

    @validator('except_list')
    def v_except_list(cls, v):
        if v:
            return [item for item in v.split(',')]
        else:
            return None


class GroupsQuerySchema(PageBaseSchema):
    is_delete: bool = False
    name: Optional[str]
    description: Optional[str]


class GroupInstance:
    def __init__(self, name, description=None, avatar_url=None, creator_id=None, org_id=None, permission_type=None):
        self.name = name
        self.description = description
        self.avatar_url = avatar_url
        self.creator_id = creator_id
        self.org_id = org_id
        self.permission_type = permission_type

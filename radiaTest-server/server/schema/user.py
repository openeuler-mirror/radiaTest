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

from flask import current_app
from typing import Optional
from pydantic import BaseModel, validator


class OauthLoginSchema(BaseModel):
    org_id: int


class LoginSchema(OauthLoginSchema):
    code: str
    privacy_version: str


class UserBaseSchema(BaseModel):
    user_id: str
    user_login: str
    user_name: str
    avatar_url: str


class UserQuerySchema(BaseModel):
    user_id: Optional[str]
    user_login: Optional[str]
    user_name: Optional[str]
    avatar_url: Optional[str]
    page_num: int
    page_size: int


class UserTaskSchema(BaseModel):
    task_title: str = None
    task_type: str
    page_num: int
    page_size: int


class UserInfoSchema(UserBaseSchema):
    orgs: Optional[list]
    groups: Optional[list]
    rank: Optional[int]
    influence: Optional[int]
    like: Optional[int]
    behavior: Optional[float]


class JoinGroupSchema(BaseModel):
    msg_id: int
    access: bool


class PrivacySchema(BaseModel):
    is_sign: bool = False
    privacy_version: str

    @validator("privacy_version")
    def check_privacy_version(cls, v):
        if v and v == current_app.config.get("PRIVACY_VERSION"):
            return v
        else:
            raise RuntimeError("unknown privacy version")

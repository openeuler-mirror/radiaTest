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

import json
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, root_validator, validator

from .base import PageBaseSchema
from server.schema import Authority
from server.model import User


class OrgUserInfoSchema(BaseModel):
    org_id: int = Field(alias="id")
    org_name: str = Field(alias="name")
    org_description: Optional[str] = Field(alias="description")
    org_avatar_url: Optional[str] = Field(alias="avatar_url")
    org_enterprise: Optional[str] = Field(alias="enterprise_id")
    is_delete: Optional[bool] = False


class AddSchema(BaseModel):
    name: str
    description: Optional[str]
    avatar_url: Optional[str]

    authority: Optional[Authority]
    oauth_login_url: Optional[str]
    oauth_get_token_url: Optional[str]
    oauth_get_user_info_url: Optional[str]
    enterprise_id: Optional[str]
    enterprise_token: Optional[str]
    enterprise_join_url: Optional[str]
    oauth_client_id: Optional[str]
    oauth_client_secret: Optional[str]
    oauth_scope: Optional[str]

    cla_verify_url: Optional[str]
    cla_verify_params: Optional[str]
    cla_verify_body: Optional[str]
    cla_sign_url: Optional[str]
    cla_request_type: Optional[str]
    cla_pass_flag: Optional[str]

    @root_validator
    def validate_enterpise(cls, values):
        if not values["oauth_client_id"] or not values["oauth_client_secret"] or not values["oauth_login_url"] \
                or not values["oauth_get_token_url"] or not values["oauth_get_user_info_url"]:
            raise TypeError("lack of oauth info to create this organization")

        if values.get("enterprise_id"):
            if not values["oauth_scope"]:
                raise TypeError("lack of enterprise info to create this organization")

            try:
                scope_list = values["oauth_scope"].split(',')
                for scope in scope_list:
                    if not isinstance(scope, str):
                        raise TypeError(
                            "the format of oauth_scope is not valid"
                        )
            except AttributeError as e:
                raise TypeError(str(e)) from e

        if values.get("cla_verify_url"):
            if not values["cla_sign_url"] or not values["cla_request_type"] or not values["cla_pass_flag"]:
                raise TypeError("lack of cla info to create this organization")

        return values


class UpdateSchema(AddSchema):
    name: Optional[str]


class OrgBaseSchema(AddSchema):
    id: int


class UpdateSchema(BaseModel):
    name: Optional[str]
    description: Optional[str]
    avatar_url: Optional[str]

    authority: Optional[Authority]
    oauth_login_url: Optional[str]
    oauth_get_token_url: Optional[str]
    oauth_get_user_info_url: Optional[str]
    enterprise_id: Optional[str]
    enterprise_token: Optional[str]
    enterprise_join_url: Optional[str]
    oauth_client_id: Optional[str]
    oauth_client_secret: Optional[str]
    oauth_scope: Optional[str]

    cla_verify_url: Optional[str]
    cla_verify_params: Optional[str]
    cla_verify_body: Optional[str]
    cla_sign_url: Optional[str]
    cla_request_type: Optional[str]
    cla_pass_flag: Optional[str]
    is_delete: bool = None


class ReUserOrgSchema(BaseModel):
    re_user_org_id: int = Field(alias='id')
    re_user_org_cla_info: str = Field(alias="cla_info")
    re_user_org_is_delete: bool = Field(alias="is_delete")
    re_user_org_role_type: int = Field(alias="role_type")
    re_user_org_create_time: datetime = Field(alias="create_time")
    re_user_org_default: bool = Field(alias="default")
    role: dict = None

    @validator("re_user_org_cla_info")
    def validator_cla_info(cls, v):
        try:
            data = json.loads(v)
            if "email" in data:
                data["email"] = User.mask_cla_email(data["email"])
            return data
        except:
            return None


class OrgQuerySchema(PageBaseSchema):
    is_delete: bool = False
    org_name: Optional[str] = Field(alias="name")
    org_description: Optional[str] = Field(alias="description")

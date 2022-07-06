import json
from typing import Optional
from datetime import datetime

from flask import current_app
from pydantic import BaseModel, Field, root_validator, validator

from .base import PageBaseSchema


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

    enterprise_id: Optional[int]
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
        if values.get("enterprise_id"):
            if not values["oauth_client_id"] or not values["oauth_client_secret"] or not values["oauth_scope"]:
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

    enterprise_id: Optional[int]
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
            return json.loads(v)
        except:
            return None


class OrgQuerySchema(PageBaseSchema):
    is_delete: bool = False
    org_name: Optional[str] = Field(alias="name")
    org_description: Optional[str] = Field(alias="description")

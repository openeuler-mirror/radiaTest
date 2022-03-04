import json
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

from .base import PageBaseSchema


class OrgUserInfoSchema(BaseModel):
    org_id: int = Field(alias="id")
    org_name: str = Field(alias="name")
    org_description: Optional[str] = Field(alias="description")
    org_avatar_url: Optional[str] = Field(alias="avatar_url")


class AddSchema(BaseModel):
    name: str
    enterprise: str
    description: Optional[str]
    avatar_url: Optional[str]
    cla_verify_url: str
    cla_verify_params: Optional[str]
    cla_verify_body: Optional[str]
    cla_sign_url: str
    cla_request_type: str
    cla_pass_flag: str


class OrgBaseSchema(AddSchema):
    id: int


class UpdateSchema(BaseModel):
    org_id: int
    name: str = None
    enterprise: str = None
    description: Optional[str]
    avatar_url: Optional[str]
    cla_verify_url: str = None
    cla_verify_params: Optional[str]
    cla_verify_body: Optional[str]
    cla_sign_url: str = None
    cla_request_type: str = None
    cla_pass_flag: str = None
    is_delete: bool = None


class ReUserOrgSchema(BaseModel):
    re_user_org_id: int = Field(alias='id')
    re_user_org_cla_info: str = Field(alias="cla_info")
    re_user_org_is_delete: bool = Field(alias="is_delete")
    re_user_org_role_type: int = Field(alias="role_type")
    re_user_org_create_time: datetime = Field(alias="create_time")
    re_user_org_default: bool = Field(alias="default")

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

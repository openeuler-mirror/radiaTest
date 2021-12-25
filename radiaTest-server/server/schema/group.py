from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from .base import PageBaseSchema


class ReUserGroupSchema(BaseModel):
    re_user_group_id: int = Field(alias='id')
    user_add_group_flag: bool = Field(alias='user_add_group_flag')
    re_user_group_is_delete: bool = Field(alias="is_delete")
    re_user_group_role_type: int = Field(alias="role_type")
    re_user_group_create_time: datetime = Field(alias="create_time")


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


class AddGroupUserSchema(BaseModel):
    gitee_ids: list


class UpdateGroupUserSchema(BaseModel):
    gitee_ids: list
    is_delete: Optional[bool] = False
    flag: Optional[bool] = True
    role_type: Optional[int]


class QueryGroupUserSchema(PageBaseSchema):
    is_admin: bool = False
    except_list: str = None

    @validator('except_list')
    def v_except_list(cls, v):
        if v:
            return [int(item) for item in v.split(',')]
        else:
            return None

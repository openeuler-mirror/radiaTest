from pydantic import BaseModel
from typing import Optional


class UserBaseSchema(BaseModel):
    gitee_id: int
    gitee_login: str
    gitee_name: str
    phone: Optional[str]
    avatar_url: str
    cla_email: Optional[str]


class UpdateUserSchema(BaseModel):
    phone: str


class UserInfoSchema(UserBaseSchema):
    orgs: Optional[list]
    groups: Optional[list]


class JoinGroupSchema(BaseModel):
    msg_id: int
    access: bool

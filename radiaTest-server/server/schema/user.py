from pydantic import BaseModel
from typing import List, Optional, Literal
from server.schema.base import PageBaseSchema


class OauthLoginSchema(BaseModel):
    org_id: int


class LoginSchema(OauthLoginSchema):
    code: str


class UserBaseSchema(BaseModel):
    user_id: str
    user_login: str
    user_name: str
    phone: Optional[str]
    avatar_url: str
    cla_email: Optional[str]


class UserQuerySchema(BaseModel):
    user_id: Optional[str]
    user_login: Optional[str]
    user_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    cla_email: Optional[str]
    page_num: int
    page_size: int


class UpdateUserSchema(BaseModel):
    phone: str


class UserTaskSchema(BaseModel):
    task_title: str = None
    task_type: str
    page_num: int
    page_size: int


class UserMachineSchema(BaseModel):
    machine_name: str = None
    machine_type: str
    page_num: int
    page_size: int
    user_id: str = None


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


class UserCaseCommitSchema(PageBaseSchema):
    title: str = None
    status: Literal['all', 'open', 'accepted', 'rejected']

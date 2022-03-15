from pydantic import BaseModel
from typing import List, Optional


class UserBaseSchema(BaseModel):
    gitee_id: int
    gitee_login: str
    gitee_name: str
    phone: Optional[str]
    avatar_url: str
    cla_email: Optional[str]


class UserQuerySchema(BaseModel):
    gitee_id: Optional[int]
    gitee_login: Optional[str]
    gitee_name: Optional[str]
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
    gitee_id: int = None


class UserInfoSchema(UserBaseSchema):
    orgs: Optional[list]
    groups: Optional[list]


class JoinGroupSchema(BaseModel):
    msg_id: int
    access: bool

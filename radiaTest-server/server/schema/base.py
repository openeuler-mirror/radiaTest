from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, root_validator
from flask import g
from server import redis_client
from server.utils.redis_util import RedisKey
from . import PermissionType
from server.utils.db import Precise
from server.model import User, Group, ReUserGroup

class DeleteBaseModel(BaseModel):
    id: List[int]


class UpdateBaseModel(BaseModel):
    id: int


class PageBaseSchema(BaseModel):
    page_size: int = 10
    page_num: int = 1
    paged: bool = True

    @root_validator
    def _validate(cls, values):
        if values["page_size"] < 1 or values["page_num"] < 1:
            raise ValueError("page_size or page_num must be more then zero")
        
        return values


class BaseEnum(Enum):
    @classmethod
    def code(cls, attr):
        if hasattr(cls, attr):
            return getattr(cls, attr).value
        else:
            return None


class TimeBaseSchema(BaseModel):
    start_time: Optional[str]
    end_time: Optional[str]

    @root_validator
    def check_time_format(cls, values):
        try:
            if values.get("start_time"):
                values["start_time"] = datetime.strptime(
                    values["start_time"], 
                    "%Y-%m-%d %H:%M:%S"
                )
            if values.get("end_time"):
                values["end_time"] = datetime.strptime(
                    values["end_time"],
                    "%Y-%m-%d %H:%M:%S"
                )
                
        except:
            raise ValueError(
                "the format of start_time/end_time is not valid, the valid type is: %Y-%m-%d %H:%M:%S"
            )

        if values.get("start_time") and values.get("end_time"):
            start_time = values.get("start_time").strftime("%Y-%m-%d")
            end_time = values.get("end_time").strftime("%Y-%m-%d")
            if start_time >= end_time:
                raise ValueError("end_time is earlier than start_time.")
        
        return values


class PermissionBase(BaseModel):
    creator_id: int
    permission_type: PermissionType
    group_id: Optional[int] = None
    org_id: int

    @root_validator
    def check_exist(cls, values):
        user = Precise(
            User, {"gitee_id": values.get("creator_id")}
        ).first()
        if not user:
            raise ValueError("The user does not exist.")
        
        if values.get("creator_id") != int(g.gitee_id):
            raise ValueError("The user is not current login user.")
        
        if values.get("org_id") != int(redis_client.hget(RedisKey.user(g.gitee_id), "current_org_id")):
            raise ValueError("The org is not current login org.")

        if values.get("permission_type") == "group":
            if not values.get("group_id"):
                raise ValueError("Lack of group_id for a role of group")
            else:
                re_user_group = Precise(
                    ReUserGroup, {"group_id": values.get("group_id"), "org_id": values.get("org_id"), "user_gitee_id": values.get("creator_id")}
                ).first()
                if not re_user_group:
                    raise ValueError("The group does not exist or does not belong to current org.")
        return values

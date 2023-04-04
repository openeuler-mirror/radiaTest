from typing import Optional

from pydantic import BaseModel

from server.schema import PermissionType


class CeleryTaskQuerySchema(BaseModel):
    tid: Optional[str]
    status: Optional[str]
    object_type: Optional[str]
    page_num: int
    page_size: int


class CeleryTaskCreateSchema(BaseModel):
    tid: str
    status: Optional[str]
    object_type: str
    vmachine_id: Optional[int]
    user_id: Optional[str]


class CeleryTaskUserInfoSchema(BaseModel):
    auth: str
    user_id: str
    group_id: Optional[int]
    org_id: Optional[int]
    permission_type: PermissionType = "person"

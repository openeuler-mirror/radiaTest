from typing import Optional

from pydantic import BaseModel


class CeleryTaskQuerySchema(BaseModel):
    tid: Optional[str]
    status: Optional[str]
    object_type: Optional[str]
    page_num: int
    page_size: int


class CeleryTaskUserInfoSchema(BaseModel):
    auth: str
    user_id: int
    group_id: int
    org_id: int

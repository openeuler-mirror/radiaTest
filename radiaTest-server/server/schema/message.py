import json

from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class MessageModel(BaseModel):
    id: Optional[int]
    data: str
    level: int
    from_id: str
    to_id: str
    is_delete: bool
    has_read: bool
    type: int
    create_time: datetime

    @validator('data')
    def validate_data(cls, v):
        try:
            return json.loads(v)
        except:
            return None


class MessageCallBack(BaseModel):
    msg_id: int
    access: bool

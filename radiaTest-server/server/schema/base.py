from typing import List
from enum import Enum
from pydantic import BaseModel


class DeleteBaseModel(BaseModel):
    id: List[int]


class UpdateBaseModel(BaseModel):
    id: int


class PageBaseSchema(BaseModel):
    page_size: int = 10
    page_num: int = 1


class BaseEnum(Enum):
    @classmethod
    def code(cls, attr):
        if hasattr(cls, attr):
            return getattr(cls, attr).value
        else:
            return None

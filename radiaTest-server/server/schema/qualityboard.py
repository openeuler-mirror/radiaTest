from typing import Optional
from pydantic import BaseModel

from server.schema import SortOrder


from server.schema.base import PageBaseSchema


class QualityBoardUpdateSchema(BaseModel):
    milestone_id: int


class QualityBoardSchema(BaseModel):
    product_id: int


class ATOverviewSchema(PageBaseSchema):
    build_name: Optional[str]
    build_order: Optional[SortOrder] = "descend"
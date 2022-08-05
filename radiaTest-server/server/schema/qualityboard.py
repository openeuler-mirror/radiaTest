from typing import Optional
from pydantic import BaseModel


class QualityBoardUpdateSchema(BaseModel):
    milestone_id: int


class QualityBoardSchema(BaseModel):
    product_id: int


class ATOverviewSchema(BaseModel):
    build_name: Optional[str]
    tests_overview_url: Optional[str]
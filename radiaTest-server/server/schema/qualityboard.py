from pydantic import BaseModel


class QualityBoardUpdateSchema(BaseModel):
    milestone_id: int


class QualityBoardSchema(BaseModel):
    product_id: int

import re
from typing import Optional

from pydantic import BaseModel, validator

from server.schema import SortOrder


from server.schema.base import PageBaseSchema


class QualityBoardUpdateSchema(BaseModel):
    milestone_id: int


class QualityBoardSchema(BaseModel):
    product_id: int


class CheckRound(BaseModel):
    rounds: dict = None

    @validator("rounds")
    def check_rounds(cls, rounds):
        if rounds:
            for key, value in rounds.items():
                pattern = re.compile(r"^R[1-9]\d*$")
                if not pattern.findall(key):
                    raise ValueError("rounds key error! key should be like Rx")
                if value not in [0, 1]:
                    raise ValueError("rounds value error! value should be 0 or 1")
            round_keys = list(rounds.keys())

            for i in range(0, len(round_keys) - 1):
                if int(round_keys[i + 1].strip('R')) - int(round_keys[i].strip('R')) != 1:
                    raise ValueError("rounds not in correct order!")

        return str(rounds)


class CheckBaseline(BaseModel):
    baseline: str = None

    @validator("baseline")
    def check_ratio(cls, baseline):
        if baseline and '%' in baseline:
            _baseline = float(baseline.strip('%')) / 100.0
            if not 0 <= _baseline <= 1:
                raise ValueError("ratio baseline must be around 0-100%")
        else:
            try:
                _ = int(baseline)
            except ValueError as e:
                raise ValueError("baseline must be a ratio or a number") from e

        return baseline


class AddChecklistSchema(CheckRound, CheckBaseline):
    check_item: str
    rounds: dict
    lts: bool = False
    lts_spx: bool = False
    innovation: bool = False


class UpdateChecklistSchema(CheckRound, CheckBaseline):
    check_item: str = None
    lts: bool = None
    lts_spx: bool = None
    innovation: bool = None


class QueryChecklistSchema(PageBaseSchema):
    check_item: str = None


class ATOverviewSchema(PageBaseSchema):
    build_name: Optional[str]
    build_order: Optional[SortOrder] = "descend"
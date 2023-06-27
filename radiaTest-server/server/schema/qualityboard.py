# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

import json
import re
from typing import List, Optional, Literal

from pydantic import BaseModel, HttpUrl, validator, root_validator, constr

from server.schema import Operator, SortOrder, MilestoneState


from server.schema.base import PageBaseSchema


class QualityBoardUpdateSchema(BaseModel):
    released: bool = False


class QualityBoardSchema(BaseModel):
    product_id: int


class CheckRound(BaseModel):
    rounds: str

    @validator("rounds")
    def check_rounds(cls, rounds):
        if rounds:
            pattern = re.compile(r"[0,1]*")
            if not pattern.findall(rounds):
                raise ValueError(
                    "rounds can only contain 1 and 0."
                )
            if rounds.count("1") != 1:
                raise ValueError(
                    "rounds must contain one digit 1."
                )
        return rounds


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


class AddChecklistSchema(BaseModel):
    checkitem_id: int
    rounds: str = "0"
    baseline: str
    product_id: int
    operation: str

    @root_validator
    def check_values(cls, values):
        rounds = values.get("rounds")
        baseline = values.get("baseline")
        operation = values.get("operation")
        if rounds:
            pattern = re.compile(r"^[0,1]*1$")
            if len(rounds) == 1:
                pattern = re.compile(r"^[0,1]$")
            if not pattern.findall(rounds):
                raise ValueError(
                    "rounds can only contain 1 and 0, when length of round is bigger than 1, rounds must ends with 1."
                )
            _r_len = len(rounds)
            _bls = baseline.split(",")
            _bls_len = len(_bls)
            _ops = operation.split(",")
            _ops_len = len(_ops)
            if _r_len != _bls_len or _r_len != _ops_len:
                raise ValueError(
                    "rounds, baseline, operation must correspond to each other."
                )
            for bl in _bls:
                if '%' in bl:
                    _baseline = float(bl.strip('%')) / 100.0
                    if not 0 <= _baseline <= 1:
                        raise ValueError(
                            "ratio baseline must be around 0-100%"
                        )
                else:
                    try:
                        _ = int(baseline)
                    except ValueError as e:
                        raise ValueError(
                            "baseline must be a ratio or a number") from e
            for op in _ops:
                if op not in set(["<", ">", "=", "<=", ">="]):
                    raise ValueError(
                        "operation must be in ['<', '>', '=', '<=', '>=']"
                    )
            if values.get("baseline") is not None and values.get("operation") is not None:
                if values.get("baseline") == "100%" and values.get("operation") == ">":
                    raise ValueError("operation can't be '>', when baseline is 100%.")
                if values.get("baseline") in ["0", "0%"] and values.get("operation") == "<":
                    raise ValueError("operation can't be '<', when baseline is 0 or 0%.")
        return values


class UpdateChecklistSchema(CheckBaseline):
    checkitem_id: int = None
    released: bool = None
    operation: Optional[Operator] = None
    rounds: str

    @validator("rounds")
    def check_rounds(cls, rounds):
        if rounds:
            pattern = re.compile(r"[0,1]*")
            if not pattern.findall(rounds):
                raise ValueError(
                    "rounds can only contain 1 and 0."
                )
        return rounds

    @root_validator
    def check_validation(cls, values):
        if values.get("baseline") is not None and values.get("operation") is not None:
            if values.get("baseline") == "100%" and values.get("operation") == ">":
                raise ValueError("operation can't be '>', when baseline is 100%.")
            if values.get("baseline") in ["0", "0%"] and values.get("operation") == "<":
                raise ValueError("operation can't be '<', when baseline is 0 or 0%.")
        return values


class DeselectChecklistSchema(CheckRound):
    rounds: str


class QueryChecklistSchema(PageBaseSchema):
    product_id: int = None


class ATOverviewSchema(PageBaseSchema):
    build_name: Optional[str]
    build_order: Optional[SortOrder] = "descend"


class QueryRpmCheckSchema(PageBaseSchema):
    name: str


class CheckItemSchema(BaseModel):
    field_name: str
    title: str
    type: Literal["issue", "at"]


class QueryCheckItemSchema(PageBaseSchema):
    field_name: Optional[str]
    title: Optional[str]


class FeatureCreateSchema(BaseModel):
    no: str
    url: Optional[HttpUrl]
    feature: str
    sig: str
    owner: str
    release_to: str
    pkgs: str


class FeatureQuerySchema(BaseModel):
    new: bool = True


class PackageListQuerySchema(BaseModel):
    summary: bool = False
    refresh: bool = False
    repo_path: Optional[Literal["everything", "EPOL", "update"]]
    arch: Optional[Literal["x86_64", "aarch64", "all"]]


class PackageCompareSchema(BaseModel):
    repo_path: Literal["everything", "EPOL", "update"]


class DailyBuildBaseSchema(BaseModel):
    daily_name: str


class DailyBuildSchema(DailyBuildBaseSchema):
    repo_url: str


class DailyBuildPackageCompareSchema(DailyBuildBaseSchema):
    repo_path: Literal["everything", "EPOL"]


class DailyBuildPackageCompareResultSchema(BaseModel):
    compare_name: str


class DailyBuildPackageCompareQuerySchema(PageBaseSchema):
    repo_path: Literal["everything", "EPOL"]


class SamePackageCompareQuerySchema(PageBaseSchema):
    summary: bool = False
    search: Optional[str]
    compare_result_list: Optional[str]
    desc: bool = False
    repo_path: Literal["everything", "EPOL", "update"]

    @validator("compare_result_list")
    def validate_status(cls, v):
        if isinstance(v, str):
            return json.loads(v)

        raise ValueError("the format of compare status list is not valid")


class PackageCompareQuerySchema(SamePackageCompareQuerySchema):
    arches: Optional[str]

    @validator("arches")
    def validate_arches(cls, v):
        if isinstance(v, str):
            return json.loads(v)

        raise ValueError("the format of arches is not valid")


class SamePackageCompareResult(BaseModel):
    repo_path: Literal["everything", "EPOL", "update"]
    new_result: bool = False


class PackageCompareResult(SamePackageCompareResult):
    arches: Optional[str]

    @validator("arches")
    def validate_arches(cls, v):
        if isinstance(v, str):
            return json.loads(v)

        raise ValueError("the format of arches is not valid")


class QueryQualityResultSchema(BaseModel):
    type: Literal["issue", "AT"]
    obj_type: Literal["product", "round", "milestone"]
    obj_id: int
    field: Literal["serious_resolved_rate", "main_resolved_rate",
                   "serious_main_resolved_rate", "current_resolved_rate", "left_issues_cnt"]


class QueryRound(BaseModel):
    product_id: int


class RoundToMilestone(BaseModel):
    milestone_id: str
    isbind: bool


class RoundUpdateSchema(BaseModel):
    buildname: Optional[str]


class CompareRoundUpdateSchema(BaseModel):
    comparee_round_ids: List[int]


class RoundIssueQueryV8(BaseModel):
    state: Optional[MilestoneState]
    only_related_me: Optional[str]
    assignee_id: Optional[str]
    author_id: Optional[str]
    collaborator_ids: Optional[str]
    created_at: Optional[str]
    finished_at: Optional[str]
    plan_started_at: Optional[str]
    deadline: Optional[str]
    filter_child: Optional[str]
    issue_type_id: int
    priority: Optional[str]
    sort: Optional[str]
    direction: Optional[str]
    page: int = 1
    per_page: int = 10


class QueryRepeatRpmSchema(PageBaseSchema):
    repo_path: Literal["everything", "EPOL", "update"]

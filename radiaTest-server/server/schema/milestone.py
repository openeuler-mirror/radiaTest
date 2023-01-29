# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang,凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2023/01/29
# @License : Mulan PSL v2
#####################################

from datetime import datetime
from typing import Literal, Optional
import pytz

from pydantic import BaseModel, Field, constr, root_validator
from sqlalchemy import func
from server import db


from server.model import Product, Milestone
from server.utils.db import Precise
from server.schema import MilestoneType, MilestoneState, SortOrder
from server.schema.base import TimeBaseSchema, PermissionBase, UpdateBaseModel, PageBaseSchema


class MilestoneBaseSchema(BaseModel):
    description: Optional[constr(max_length=255)]
    name: Optional[constr(max_length=64)]
    product_id: Optional[int]
    type: Optional[MilestoneType]
    state: Optional[MilestoneState]
    is_sync: Optional[bool]


class MilestoneQuerySchema(MilestoneBaseSchema, PageBaseSchema):
    round_id: Optional[int]
    page_num: int = 1
    page_size: int = 10
    create_time_order: Optional[SortOrder] = None


class MilestoneUpdateSchema(UpdateBaseModel, TimeBaseSchema):
    name: Optional[constr(max_length=64)]

    @root_validator
    def check_values(cls, values):
        cur_milestone = Milestone.query.filter_by(id=values.get("id")).first()
        if not cur_milestone:
            raise ValueError("The milestone doesn't existed.")
        start_time = cur_milestone.start_time.strftime("%Y-%m-%d")
        end_time = cur_milestone.end_time.strftime("%Y-%m-%d")
        if values.get("start_time"):
            start_time = values.get("start_time").strftime("%Y-%m-%d")
        if values.get("end_time"):
            end_time = values.get("end_time").strftime("%Y-%m-%d")

        if start_time >= end_time:
            raise ValueError("end_time is earlier than start_time.")
        milestones = (
            Milestone.query.filter(
                Milestone.product_id == cur_milestone.product_id,
                Milestone.permission_type == cur_milestone.permission_type,
                Milestone.id != values.get("id"),
            )
            .all()
        )
        for milestone in milestones:
            if (
                start_time >= milestone.start_time.strftime("%Y-%m-%d")
                and
                start_time <= milestone.end_time.strftime("%Y-%m-%d")
            ) or (
                end_time >= milestone.start_time.strftime("%Y-%m-%d")
                and
                end_time <= milestone.end_time.strftime("%Y-%m-%d")
            ):
                raise ValueError(
                    "the period  of milestone overlaps period of milestone existed."
                )
            if (
                milestone.start_time.strftime("%Y-%m-%d") >= start_time
                and
                milestone.start_time.strftime("%Y-%m-%d") <= end_time
            ) or (
                milestone.end_time.strftime("%Y-%m-%d") >= start_time
                and
                milestone.end_time.strftime("%Y-%m-%d") <= end_time
            ):
                raise ValueError(
                    "the period  of milestone overlaps period of milestone existed."
                )

        if not values.get("name"):
            return values
        milestone = Precise(Milestone, {"name": values.get("name")}).first()
        if milestone and milestone.id != values.get("id"):
            raise ValueError("The milestone has existed.")
        return values


class MilestoneCreateSchema(MilestoneBaseSchema, PermissionBase):
    product_id: int
    type: MilestoneType
    end_time: str
    start_time: Optional[str]
    is_sync: Optional[bool]

    @root_validator
    def assign_name(cls, values):
        product = Precise(
            Product,
            {
                "id": values.get("product_id"),
                "org_id": values.get("org_id"),
            }
        ).first()
        if not product:
            raise ValueError("The bound product version does not exist.")
        if not values.get("start_time"):
            values["start_time"] = datetime.now(tz=pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        if values.get("start_time") >= values.get("end_time"):
            raise ValueError("end_time is earlier than start_time.")
        milestones = (
            Milestone.query.filter_by(
                product_id=values.get("product_id"), permission_type=values.get("permission_type")
            )
            .all()
        )
        for milestone in milestones:
            if (
                values.get("start_time") >= milestone.start_time.strftime(
                    "%Y-%m-%d")
                and
                values.get("start_time") <= milestone.end_time.strftime(
                    "%Y-%m-%d")
            ) or (
                values.get("end_time") >= milestone.start_time.strftime(
                    "%Y-%m-%d")
                and
                values.get("end_time") <= milestone.end_time.strftime(
                    "%Y-%m-%d")
            ):
                raise ValueError(
                    "the period  of new milestone overlaps period of milestone existed."
                )
            if (
                milestone.start_time.strftime(
                    "%Y-%m-%d") >= values.get("start_time")
                and
                milestone.start_time.strftime(
                    "%Y-%m-%d") <= values.get("end_time")
            ) or (
                milestone.end_time.strftime(
                    "%Y-%m-%d") >= values.get("start_time")
                and
                milestone.end_time.strftime(
                    "%Y-%m-%d") <= values.get("end_time")
            ):
                raise ValueError(
                    "the period  of milestone overlaps period of milestone existed."
                )

        if not values.get("name"):
            milestone_type = values.get("type")
            prefix = product.name + "-" + product.version
            if milestone_type == "update":
                values["name"] = (
                    prefix
                    + "-update_"
                    + datetime.now(tz=pytz.timezone("Asia/Shanghai")
                                   ).strftime("%Y%m%d")
                )
            elif milestone_type == "round":
                prefix = prefix + "-round-"
                _max_round = (
                    db.session.query(
                        func.max(func.cast(func.replace(Milestone.name, prefix, ""), db.Integer))
                    )
                    .filter(
                        Milestone.name.op("regexp")(prefix + "[1-9][0-9]*")
                    )
                    .scalar()
                )
                if not _max_round:
                    _max_round = "1"
                else:
                    _max_round = str(
                        int(_max_round) + 1)
                values["name"] = prefix + _max_round
            elif milestone_type == "release":
                values["name"] = prefix + " release"
        milestone = Precise(Milestone, {"name": values.get("name")}).first()
        if milestone:
            raise ValueError("The milestone  %s has existed." %
                             values.get("name"))
        return values


class GiteeTimeBaseModel(BaseModel):
    due_date: Optional[str] = Field(alias="end_time")
    start_date: Optional[str] = Field(alias="start_time")


class GiteeMilestoneBase(GiteeTimeBaseModel):
    access_token: str
    title: str = Field(alias="name")
    due_date: str = Field(alias="end_time")


class GiteeMilestoneEdit(GiteeMilestoneBase):
    title: Optional[str] = Field(alias="name")


class GiteeIssueQueryV8(BaseModel):
    milestone_id: str
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


class GenerateTestReport(BaseModel):
    uri: str


class QueryTestReportFile(BaseModel):
    file_type: Literal["md", "html"]


class GiteeIssueQueryV5(BaseModel):
    state: Optional[MilestoneState]
    sort: Optional[str]
    direction: Optional[str]
    since: Optional[str]
    schedule: Optional[str]
    deadline: Optional[str]
    created_at: Optional[str]
    finished_at: Optional[str]
    milestone: Optional[str]
    assignee: Optional[str]
    creator: Optional[str]
    page: int = 1
    per_page: int = 10


class IssueQuerySchema(BaseModel):
    is_live: bool = False


class GiteeMilestoneQuerySchema(BaseModel):
    search: str


class SyncMilestoneSchema(BaseModel):
    gitee_milestone_id: int


class MilestoneStateEventSchema(BaseModel):
    state_event: Literal["activate", "close"]


class IssueRateFieldSchema(BaseModel):
    field: Literal["serious_resolved_rate", "main_resolved_rate",
                   "serious_main_resolved_rate", "current_resolved_rate", "left_issues_cnt", "invalid_issues_cnt"]

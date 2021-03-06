from datetime import datetime
from typing import Literal, Optional
import pytz

from pydantic import BaseModel, Field, constr, root_validator, validator


from server.model import Product, Milestone
from server.utils.db import Precise
from server.schema import MilestoneType, MilestoneState, MilestoneStateEvent
from server.schema.base import TimeBaseSchema, PermissionBase, UpdateBaseModel


class MilestoneBaseSchema(BaseModel):
    description: Optional[constr(max_length=255)]
    name: Optional[constr(max_length=64)]
    product_id: Optional[int]
    type: Optional[MilestoneType]
    state: Optional[MilestoneState]
    is_sync: Optional[bool]


class MilestoneQuerySchema(MilestoneBaseSchema):
    is_sync: Optional[bool]
    page_num: int = 1
    page_size: int = 10


class MilestoneUpdateSchema(UpdateBaseModel, TimeBaseSchema):
    name: Optional[constr(max_length=64)]
    state_event: Optional[MilestoneStateEvent]

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
        milestone = (
            Milestone.query.filter(
                Milestone.product_id == cur_milestone.product_id,
                Milestone.type == cur_milestone.type,
                Milestone.id != values.get("id"),
            )
            .order_by(Milestone.end_time.desc())
            .first()
        )
        if milestone and start_time <= milestone.end_time.strftime("%Y-%m-%d"):
            raise ValueError(
                "start_time of modifying milestone is earlier than end_time of milestone existed."
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
    start_time: Optional[str] = datetime.now(
        tz=pytz.timezone("Asia/Shanghai")
    ).strftime("%Y-%m-%d %H:%M:%S")
    is_sync: Optional[bool]

    @root_validator
    def assign_name(cls, values):
        product = Precise(Product, {"id": values.get("product_id")}).first()
        if not product:
            raise ValueError("The bound product version does not exist.")
        if values.get("start_time") >= values.get("end_time"):
            raise ValueError("end_time is earlier than start_time.")
        milestone = (
            Milestone.query.filter_by(
                product_id=values.get("product_id"), type=values.get("type")
            )
            .order_by(Milestone.end_time.desc())
            .first()
        )
        if milestone and values.get("start_time") <= milestone.end_time.strftime(
            "%Y-%m-%d"
        ):
            raise ValueError(
                "start_time of new milestone is earlier than end_time of milestone existed."
            )
        if not values.get("name"):
            milestone_type = values.get("type")
            prefix = product.name + " " + product.version
            if milestone_type == "update":
                values["name"] = (
                    prefix
                    + " update_"
                    + datetime.now(tz=pytz.timezone("Asia/Shanghai")).strftime("%Y%m%d")
                )
            elif milestone_type == "round":
                prefix = prefix + " round-"
                _max_round = (
                    Milestone.query.filter(
                        Milestone.name.op("regexp")(prefix + "[1-9]*")
                    )
                    .order_by(Milestone.name.desc())
                    .first()
                )
                if not _max_round:
                    _max_round = "1"
                else:
                    _max_round = str(int(_max_round.name.replace(prefix, "")) + 1)
                values["name"] = prefix + _max_round
            elif milestone_type == "release":
                values["name"] = prefix + " release"
        milestone = Precise(Milestone, {"name": values.get("name")}).first()
        if milestone:
            raise ValueError("The milestone  %s has existed." % values.get("name"))
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
    state_event: Optional[Literal["activate", "close"]]


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

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, constr, root_validator, validator


from server.model import Product, Milestone
from server.utils.db import Precise
from server.schema import MilestoneType, MilestoneState, MilestoneStateEvent
from server.schema.base import TimeBaseSchema, PermissionBase


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


class MilestoneUpdateSchema(TimeBaseSchema):
    description: Optional[constr(max_length=255)]
    name: Optional[constr(max_length=64)]
    state_event: Optional[MilestoneStateEvent]
    

class MilestoneCreateSchema(MilestoneBaseSchema, PermissionBase):
    product_id: int
    type: MilestoneType
    end_time: str
    start_time: Optional[str] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_sync: Optional[bool]

    @root_validator
    def assign_name(cls, values):
        if not values.get("name"):
            try:
                if not values.get("product_id"):
                    milestone = Precise(Milestone, {"id": values.get("id")}).first()
                    if not milestone:
                        raise ValueError("The milestone no longer exists.")
                    product = milestone.product
                    milestone_type = milestone.type
                else:
                    milestone_type = values.get("type")
                    product = Precise(Product, {"id": values.get("product_id")}).first()
                    if not product:
                        raise ValueError("The bound product version does not exist.")
            except RuntimeError as e:
                raise RuntimeError(e)

            prefix = product.name + " " + product.version

            if milestone_type == "update":
                values["name"] = (
                    prefix + " update_" + datetime.now().strftime("%Y%m%d")
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
                raise ValueError("The milestone has existed.")

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
    state_event:  Optional[Literal["activate", "close"]]


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



import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, constr, root_validator


from server.model import Product, Milestone

from server.utils.db import Precise

from server.schema import MilestoneType


class MilestoneBaseSchema(BaseModel):
    start_time: Optional[datetime.datetime]
    description: Optional[constr(max_length=255)]
    name: Optional[constr(max_length=64)]
    end_time: Optional[datetime.datetime]
    product_id: Optional[int]
    type: Optional[MilestoneType]
    state: Optional[Literal["open", "closed"]]
    is_sync: Optional[bool]


class MilestoneUpdateSchema(MilestoneBaseSchema):
    state_event: Optional[Literal["activate", "close"]]


class MilestoneCreateSchema(MilestoneBaseSchema):
    product_id: int
    type: MilestoneType
    end_time: datetime.datetime
    start_time: Optional[datetime.datetime] = datetime.datetime.now()
    
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
                    prefix + " update_" + datetime.datetime.now().strftime("%Y%m%d")
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

        return values


class GiteeMilestoneBase(BaseModel):
    access_token: str
    title: str = Field(alias="name")
    due_date: str = Field(alias="end_time")
    start_date: Optional[str] = Field(alias="start_time")


class GiteeMilestoneEdit(GiteeMilestoneBase):
    title: Optional[str] = Field(alias="name")
    due_date: Optional[str] = Field(alias="end_time")
    state_event: Optional[Literal["activate", "close"]]


class GiteeIssueQueryV8(BaseModel):
    milestone_id: Optional[str]
    state: Optional[str]
    only_related_me: Optional[str]
    assignee_id: Optional[str]
    author_id: Optional[str]
    collaborator_ids: Optional[str]
    created_at: Optional[str]
    finished_at: Optional[str]
    plan_started_at: Optional[str]
    deadline: Optional[str]
    filter_child: Optional[str]
    # TODO 建立新表存储issue_state_id信息，关联org表， 等待gitee v8接口可用
    issue_type_id: int = 118738
    priority: Optional[str]
    sort: Optional[str]
    direction: Optional[str]
    page: int = 1
    per_page: int = 10


class GiteeIssueQueryV5(BaseModel):
    state: Optional[str]
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



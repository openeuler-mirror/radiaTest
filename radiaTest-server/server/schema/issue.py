# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
# @Date    : 2023/03/15
# # @License : Mulan PSL v2
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
from server.schema.base import PageBaseSchema


class IssueBaseSchema(BaseModel):
    description: Optional[constr(max_length=255)]
    name: Optional[constr(max_length=64)]
    product_id: Optional[int]
    type: Optional[MilestoneType]
    state: Optional[MilestoneState]
    is_sync: Optional[bool]


class CreateIssueSchema(BaseModel):
    title: str
    description: str
    priority: int
    milestone_id: int
    task_id: int
    case_id: int
    project_name: str
    issue_type_id: int


class GiteeCreateIssueSchema(BaseModel):
    title: str
    description: str
    priority: int
    milestone_id: int
    project_id: Optional[int]
    issue_type_id: int


class QueryIssueSchema(PageBaseSchema):
    title: Optional[str]
    description: Optional[str]
    priority: Optional[int]
    milestone_id: Optional[int]
    task_id: Optional[int]
    case_id: Optional[int]
    project_name: Optional[str]


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


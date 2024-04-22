# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Date    :
# @License : Mulan PSL v2
#####################################

import json
from typing import List
from enum import Enum
from datetime import datetime, time
from dateutil import parser

from pydantic import BaseModel, validator, root_validator, Field
from typing_extensions import Literal

from server.schema.base import PageBaseSchema, BaseEnum
from server.schema import Frame
from server.utils.text_utils import check_illegal_lables


class AddTaskStatusSchema(BaseModel):
    name: str


class UpdateTaskStatusSchema(BaseModel):
    name: str


class TaskStatusOrder(BaseModel):
    name: str
    order: int


class UpdateTaskStatusOrderSchema(BaseModel):
    order_list: List[TaskStatusOrder]


class EnumsTaskExecutorType(str, Enum):
    """Another Enums class"""

    PERSON = "PERSON"
    GROUP = "GROUP"


class EnumsTaskType(str, Enum):
    """Another Enums class"""

    PERSON = "PERSON"
    GROUP = "GROUP"
    ORGANIZATION = "ORGANIZATION"
    VERSION = "VERSION"


class PriorityEnum(BaseEnum):
    GENERAL = 1
    URGENCY = 2
    VERY_URGENCY = 3


class AddTaskSchema(BaseModel):
    title: str
    type: EnumsTaskType
    status_id: int
    group_id: int = None
    executor_type: EnumsTaskExecutorType
    executor_id: str
    start_time: str
    deadline: str
    is_version_task: bool = False
    parent_id: List[int] = None
    child_id: List[int] = None
    keywords: str = None
    abstract: str = None
    abbreviation: str = None
    content: str = None
    milestone_id: int = None
    case_id: int = None
    is_single_case: bool = False
    is_manage_task: bool = False
    case_node_id: int = None

    @root_validator
    def check(cls, values):
        check_version_res = (values.get("type") == "VERSION" and not values.get("milestone_id"))
        check_not_version_res = (
                values.get("milestone_id") and (not values.get("type") or values.get("type") != "VERSION")
        )
        if check_version_res or check_not_version_res:
            raise ValueError("when type of task is VERSION, milestone_id must be not None.")
        try:
            datetime.strptime(
                values.get("start_time"), 
                "%Y-%m-%d"
            )
            datetime.strptime(
                values.get("deadline"),
                "%Y-%m-%d"
            )  
        except ValueError as e:
            raise RuntimeError("the format of time is not valid, the valid type is: %Y-%m-%d") from e
        if values.get("deadline") < values.get("start_time"):
            raise ValueError("start time must be earlier than deadline.")
        return values


class OutAddTaskSchema(BaseModel):
    title: str
    cases: List[int]
    milestone_id: int
    group_id: int
    frame: Frame


class QueryTaskByTimeSchema(BaseModel):
    task_time: str
    type: Literal['organization', 'group', 'version', 'all'] = "all"
    group_id: int = None
    org_id: int = None

    @validator('task_time')
    def validate(cls, v):
        if isinstance(v, str):
            v = json.loads(v)
            try:
                v[0] = datetime.strptime(
                    v[0], 
                    "%Y-%m-%d"
                )
                v[1] = datetime.strptime(
                    v[1],
                    "%Y-%m-%d"
                )  
            except ValueError as e:
                raise RuntimeError("the format of time is not valid, the valid type is: %Y-%m-%d") from e

            v[0] = v[0].strftime("%Y-%m-%d")
            v[1] = v[1].strftime("%Y-%m-%d")
            if v[0] >= v[1]:
                raise ValueError("the first time must be earlier than second time.")
        return v


class QueryTaskSchema(PageBaseSchema):
    title: str = None
    type: EnumsTaskType = None
    executor_id: str = None
    creator_id: str = None
    participant_id: str = None
    status_id: int = None
    deadline: str = None
    start_time: str = None
    is_delete: bool = False
    milestone_id: str = None
    gantt: bool = False
    org_id: int = None

    @validator('participant_id')
    def validate_participant_id(cls, v):
        if v:
            return [int(item) for item in v.split(',')]
        else:
            return None

    @validator('milestone_id')
    def validate_milestone_id(cls, v):
        if v:
            return [int(item) for item in v.split(',')]
        else:
            return None


class TaskBaseSchema(BaseModel):
    id: int
    title: str
    type: EnumsTaskType = None
    deadline: datetime = None

    @validator('deadline')
    def validate(cls, v):
        if v:
            return v.strftime("%Y-%m-%d")
        else:
            return str()


class TaskInfoSchema(TaskBaseSchema):
    creator_id: str = None
    start_time: datetime = None
    content: str = None
    executor_type: EnumsTaskExecutorType = None
    status_id: int = None
    org_id: int = None
    group_id: int = None
    priority: Literal[1, 2, 3] = 1
    is_version_task: bool = False
    keywords: str = None
    abstract: str = None
    abbreviation: str = None
    frame: str = None
    automatic_finish: bool = False
    is_single_case: bool = False
    accomplish_time: datetime = None
    is_manage_task: bool = False
    percentage: int = 0

    @validator('priority')
    def validate_priority(cls, v):
        return PriorityEnum(v).name

    @validator('start_time')
    def validate_start_time(cls, v):
        if v:
            return v.strftime("%Y-%m-%d")
        else:
            return str()

    @validator('accomplish_time')
    def validate_accomplish_time(cls, v):
        if v:
            return v.strftime("%Y-%m-%d")
        else:
            return str()


class TaskRecycleBinInfo(TaskInfoSchema):
    update_time: datetime = None

    @validator('update_time')
    def validate_update_time(cls, v):
        if v:
            return v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return str()


class ParticipantSchema(BaseModel):
    participant_id: int
    type: EnumsTaskExecutorType


class UpdateTaskExecutorSchema(BaseModel):
    executor_type: EnumsTaskExecutorType
    executor_id: str


class UpdateTaskSchema(BaseModel):
    title: str = None
    start_time: str = None
    deadline: str = None
    status_id: int = None
    status_name: str = None
    group_id: int = None
    content: str = None
    is_delete: bool = None
    frame: Frame = None
    priority: Literal['GENERAL', 'URGENCY', 'VERY_URGENCY'] = None
    milestone_id: int = None
    milestones: List[int] = None
    automatic_finish: bool = None
    is_manage_task: bool = None

    @validator('priority')
    def validate(cls, v):
        return PriorityEnum.code(v).value


class UpdateTaskPercentageSchema(BaseModel):
    percentage: int

    @validator('percentage')
    def validate(cls, v):
        if v < 0 or v > 100:
            raise ValueError("task percentage must be between 0 and 100")
        return v


class DelTaskParticipantSchema(BaseModel):
    participant_id: List[int] = None
    is_all: bool = False


class UpdateTaskParticipantSchema(BaseModel):
    participants: List[ParticipantSchema]


class AddTaskCommentSchema(BaseModel):
    content: str

    @validator("content")
    def validate_content(cls, v):
        if v:
            v = check_illegal_lables(v)
            return v
        else:
            raise RuntimeError("content can't be None")


class DelTaskCommentSchema(BaseModel):
    comment_id: str = None
    is_all: bool = False

    @validator('comment_id')
    def validate_comment_id(cls, v):
        if v:
            return [int(item) for item in v.split(',')]
        else:
            return None


class TagColorEnum(BaseEnum):
    BLUE = 1
    RED = 2
    ORANGE = 3
    YELLOW = 4
    GREEN = 5
    CYAN = 6
    PURPLE = 7


class TagInfoSchema(BaseModel):
    id: int
    name: str
    color: Literal[1, 2, 3, 4, 5, 6, 7]

    @validator('color')
    def validate_color(cls, v):
        return TagColorEnum(v).name


class AddTaskTagSchema(BaseModel):
    name: str = None
    color: Literal['BLUE', 'RED', 'ORANGE', 'YELLOW', 'GREEN', 'CYAN', 'PURPLE'] = None
    task_id: int
    id: int = None

    @validator('color')
    def validate_color(cls, v):
        return TagColorEnum.code(v)


class DelTaskTagSchema(BaseModel):
    id: int
    task_id: int = None


class AddFamilyMemberSchema(BaseModel):
    parent_id: int = None
    child_id: int = None


class QueryFamilySchema(BaseModel):
    title: str = None
    not_in: bool = True
    is_parent: bool = True
    org_id: int = None


class DelFamilyMemberSchema(BaseModel):
    parent_id: str = None
    child_id: str = None

    @validator('parent_id')
    def validate_parent_id(cls, v):
        if v:
            return [int(item) for item in v.split(',')]
        else:
            return None

    @validator('child_id')
    def validate_child_id(cls, v):
        if v:
            return [int(item) for item in v.split(',')]
        else:
            return None


class QueryTaskReportSchema(BaseModel):
    is_version_task: bool = False


class TaskReportSchema(BaseModel):
    id: int = None
    title: str
    remark: str = None
    order: int
    is_version_task: bool
    default: str = None


class TaskReportContentSchema(BaseModel):
    title: str
    content: str


class QueryTaskCaseSchema(PageBaseSchema):
    case_name: str = None
    is_contain: bool = False
    suite_id: int = None
    milestone_id: int = None


class AddTaskCaseSchema(BaseModel):
    case_id: List[int]


class DelTaskCaseSchema(BaseModel):
    case_id: str

    @validator('case_id')
    def validate_case_id(cls, v):
        if v:
            return [int(item) for item in v.split(',')]
        else:
            return None


class QueryTaskStatisticsSchema(BaseModel):
    start_time: str = None
    end_time: str = None
    type: str = None
    groups: str = None
    executors: str = None
    milestone_id: str = None
    page: int = 1
    per_page: int = 10
    issue_type_id: int

    @root_validator
    def validate(cls, query):
        for key, value in query.items():
            if not value:
                query[key] = None
                continue
            if key == 'start_time':
                query[key] = parser.parse(value)
            elif key == 'end_time':
                query[key] = datetime.combine(parser.parse(value).date(), time.max)
            elif key == 'groups':
                query[key] = [int(item) for item in value.split(',')]
            elif key == 'executors':
                query[key] = [int(item) for item in value.split(',')]
            elif key == 'type':
                query[key] = EnumsTaskType(value)
            elif key == 'milestone_id':
                query[key] = int(value)
            elif key == 'issue_type_id':
                query[key] = int(value)
        return query


class TaskJobResultSchema(BaseModel):
    job_id: int
    result: Literal['block', 'done']


class TaskCaseResultSchema(BaseModel):
    result: Literal['success', 'failed', 'running']


class DistributeTaskCaseSchema(BaseModel):
    cases: List[int]
    child_task_id: int


class DistributeTemplateTypeSchema(object):
    class Add(BaseModel):
        name: str = Field(..., max_length=32)
        executor_id: str
        suites: List[str] = []
        helpers: List[str] = []
        suite_source: Literal["org", "group"] = "org"

    class Update(BaseModel):
        name: str = Field(None, max_length=32)
        executor_id: str = None
        suites: List[str] = []
        helpers: List[str] = []
        suite_source: Literal["org", "group"] = "org"

        @validator('suites')
        def v_suites(cls, v):
            if v is not None:
                return ','.join(v)
            else:
                return str()

        @validator('helpers')
        def v_helpers(cls, v):
            if v is not None:
                return ','.join(v)
            else:
                return str()

    class Query(PageBaseSchema):
        template_id: int = None
        type_id: int = None


class DistributeTemplate(object):
    class Add(BaseModel):
        name: str = Field(..., max_length=32)
        group_id: int
        types: List[DistributeTemplateTypeSchema.Add] = None

    class Query(PageBaseSchema):
        name: str = None
        group_id: int = None
        type_name: str = None
        simple: bool = False

    class Update(BaseModel):
        group_id: int = None
        name: str = Field(None, max_length=32)

    class Distribute(BaseModel):
        milestone_id: int
        distribute_all_cases: bool = True


class DeleteTaskList(BaseModel):
    task_ids: List[int] = None


class MilestoneTaskSchema(PageBaseSchema):
    title: str = None


class RecycleBinSchema(PageBaseSchema):
    org_id: int = None

import datetime
from typing import Optional, List
import pytz
from dataclasses import dataclass
from pydantic import BaseModel, HttpUrl, constr, root_validator, validator

from server.schema import Frame, JobDefaultStates, JobSortedBy, MachinePolicy
from server.schema.base import PageBaseSchema, TimeBaseSchema, PermissionBase
from server.utils.db import Precise
from server.model import Milestone


class JobUpdateSchema(BaseModel):
    name: Optional[str]
    running_time: Optional[int]
    total: Optional[int]
    success_cases: Optional[int]
    fail_cases: Optional[int]
    result: Optional[str]
    remark: Optional[str]
    multiple: Optional[bool]
    status: Optional[str]
    master: Optional[str]
    frame: Optional[Frame]
    milestone_id: Optional[int]
    tid: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str] = None


class JobCreateSchema(JobUpdateSchema):
    parent_id: Optional[int]
    name: str
    is_suite_job: bool


class RunJobBase(PermissionBase):
    frame: Frame
    pmachine_list: Optional[List[int]] = []
    vmachine_list: Optional[List[int]] = []
    machine_policy: MachinePolicy
    machine_group_id: int

    @validator("machine_policy")
    def validate_policy(cls, v, values):
        if v == "auto" and (len(values["pmachine_list"]) != 0 or len(values["vmachine_list"]) != 0):
            raise RuntimeError(
                "should not select any machine with auto machine policy"
            )
        return v


class RunTemplateBase(RunJobBase):
    template_id: int
    template_name: str
    name: Optional[str]
    taskmilestone_id: Optional[int]

    @root_validator
    def assignment(cls, values):
        if not values.get("name"):
            values["name"] = "Job-%s-%s-%s" % (
                values["template_name"].replace(" ", "-"),
                values.get("frame"),
                datetime.datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d-%H-%M-%S"),
            )
        else:
            values["name"] = values["name"].replace(" ", "-")

        return values


class RunSuiteBase(RunJobBase):
    git_repo_id: int
    name: Optional[constr(max_length=512)]
    suite_id: int
    milestone_id: int

    @root_validator
    def assignment(cls, values):
        if not values.get("name"):
            milestone = Precise(
                Milestone, {"id": values.get("milestone_id")}).first()

            values["name"] = "Job-%s-%s-%s" % (
                milestone.name.replace(" ", "-"),
                values.get("frame"),
                datetime.datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d-%H-%M-%S"),
            )
        return values


class AnalyzedCreateSchema(BaseModel):
    result: str
    job_id: int
    case_id: int
    master: str
    log_url: HttpUrl
    running_time: int


class AnalyzedQueryBase(BaseModel):
    job_id: int


class AnalyzedQueryItem(BaseModel):
    fail_type: Optional[str]
    details: Optional[str]


class AnalyzedUpdateItem(AnalyzedQueryItem):
    logs: Optional[List[int]]


class AnalyzedQueryRecords(BaseModel):
    case_id: int


class JobQuerySchema(PageBaseSchema):
    name: Optional[str]
    sorted_by: JobSortedBy = "create_time"
    status: Optional[JobDefaultStates]


class LogCreateSchema(BaseModel):
    stage: str
    checkpoint: str
    expect_result: int
    actual_result: int
    mode: int
    section_log: str


@dataclass
class PayLoad:
    user_id: str
    user_login: str
    
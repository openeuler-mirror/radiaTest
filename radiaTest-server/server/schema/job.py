import datetime
from typing import Optional, List

from pydantic import BaseModel, constr, root_validator, validator

from server.schema import Frame, JobDefaultStates, JobSortedBy, MachinePolicy
from server.schema.base import PageBaseSchema
from server.utils.db import Precise
from server.model import Milestone


class JobUpdateSchema(BaseModel):
    name: Optional[str]
    start_time: Optional[datetime.datetime]
    running_time: Optional[int]
    end_time: Optional[datetime.datetime]
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


class RunJobBase(BaseModel):
    frame: Frame
    pmachine_list: Optional[List[int]] = []
    vmachine_list: Optional[List[int]] = []
    machine_policy: MachinePolicy

    @validator("machine_policy")
    def validate_policy(cls, v, values):
        if v == "auto" and (values["pmachine_list"] or values["vmachine_list"]):
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
        values["start_time"] = datetime.datetime.now()

        if not values.get("name"):
            values["name"] = "Job-%s-%s-%s" % (
                values["template_name"].replace(" ", "-"),
                values.get("frame"),
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            )
        else:
            values["name"] = values["name"].replace(" ", "-")

        return values


class RunSuiteBase(RunJobBase):
    git_repo_id: int
    name: Optional[constr(max_length=64)]
    suite_id: int
    milestone_id: int

    @root_validator
    def assignment(cls, values):
        values["start_time"] = datetime.datetime.now()

        if not values.get("name"):
            milestone = Precise(
                Milestone, {"id": values.get("milestone_id")}).first()

            values["name"] = "Job-%s-%s-%s" % (
                milestone.name.replace(" ", "-"),
                values.get("frame"),
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            )
        return values

class AnalyzedQueryBase(BaseModel):
    job_id: int


class AnalyzedQueryItem(BaseModel):
    fail_type: Optional[str]
    details: Optional[str]


class AnalyzedQueryRecords(BaseModel):
    case_id: int


class JobQuerySchema(PageBaseSchema):
    name: Optional[str]
    sorted_by: JobSortedBy = "create_time"
    status: Optional[JobDefaultStates]
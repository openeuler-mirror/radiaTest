from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, constr, validator

from messenger.schema import Frame, MachinePolicy, PermissionType


class AuthBaseModel(BaseModel):
    user_id: Optional[str]
    creator_id: str
    permission_type: PermissionType
    group_id: Optional[int] = None
    org_id: int


class JobCreateSchema(BaseModel):
    name: Optional[str]
    start_time: Optional[datetime]
    running_time: Optional[int]
    end_time: Optional[datetime]
    total: Optional[int]
    success_cases: Optional[int]
    fail_cases: Optional[int]
    result: Optional[str]
    remark: Optional[str]
    multiple: Optional[bool]
    is_suite_job: Optional[bool]
    status: Optional[str]
    master: Optional[List[str]]
    frame: Optional[Frame]
    milestone_id: Optional[int]
    tid: Optional[str]

    @validator("master")
    def change_master_format(cls, v):
        return ','.join(v)


class JobUpdateSchema(AuthBaseModel):
    name: Optional[str]
    start_time: Optional[str]
    running_time: Optional[int]
    end_time: Optional[str]
    total: Optional[int]
    success_cases: Optional[int]
    fail_cases: Optional[int]
    result: Optional[str]
    remark: Optional[str]
    multiple: Optional[bool]
    is_suite_job: Optional[bool]
    status: Optional[str]
    master: Optional[str]
    frame: Optional[Frame]
    milestone_id: Optional[int]
    tid: Optional[str]

    @validator("start_time")
    def check_start_time(cls, v):
        try:
            if v:
                v = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            v = datetime.strptime(v, "%Y-%m-%d")
        
        return v

    @validator("end_time")
    def check_end_time(cls, v):
        try:
            if v:
                v = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            v = datetime.strptime(v, "%Y-%m-%d")
        
        return v


class RunJobBase(AuthBaseModel):
    user_id: str
    frame: Frame
    pmachine_list: List[dict]
    vmachine_list: List[dict]
    machine_policy: MachinePolicy
    machine_group_id: int


class RunTemplateBase(RunJobBase):
    template_id: int
    template_name: str
    name: str
    taskmilestone_id: Optional[int]


class RunSuiteBase(RunJobBase):
    git_repo_id: int
    name: constr(max_length=512)
    suite_id: int
    milestone_id: int

from typing import Optional

from pydantic import BaseModel, constr, validator
from pydantic.class_validators import root_validator
from typing_extensions import Literal
from typing import List

from server.model.testcase import Suite, Case
from server.schema.base import PermissionBase, UpdateBaseModel, PageBaseSchema
from server.schema import MachineType, TestType, TestLevel, BaselineType


class BaselineBodySchema(BaseModel):
    title: str
    type: BaselineType
    parent_id: Optional[int]
    group_id: int
    suite_id: Optional[int]
    case_id: Optional[int]
    is_root: bool = True
    in_set: bool = False

    @root_validator
    def validate_suite(cls, values):
        if values["parent_id"]:
            values["is_root"] = False

        if values["is_root"] and values["in_set"]:
            values["title"] = "用例集"

        if not values["in_set"] and values["title"] == "用例集":
            raise ValueError("title is not valid for this type of node")

        if values["type"] == 'suite':
            if not values["suite_id"]:
                raise ValueError("The baseline should relate to one suite")

            suite = Suite.query.filter_by(id=values["suite_id"]).first()
            if not suite:
                raise ValueError("The suite to be related is not exist")

        elif values["type"] == 'case':
            if not values["case_id"]:
                raise ValueError("The baseline should relate to one case")

            case = Case.query.filter_by(id=values["case_id"]).first()
            if not case:
                raise ValueError("The case to be related is not exist")

        return values


class BaselineBodyInternalSchema(BaselineBodySchema):
    org_id: int


class BaselineQuerySchema(BaseModel):
    group_id: int
    title: Optional[str]


class BaselineItemQuerySchema(BaseModel):
    title: Optional[str]


class BaselineUpdateSchema(BaseModel):
    title: Optional[str]


class BaselineBaseSchema(BaseModel):
    id: int
    title: str
    type: str
    group_id: int
    suite_id: int = None
    case_id: int = None
    in_set: bool = False


class SuiteBase(BaseModel):
    name: str
    machine_num: Optional[int] = 1
    machine_type: Optional[MachineType] = "kvm"
    add_network_interface: Optional[int]
    add_disk: Optional[str]
    remark: Optional[str]
    deleted: Optional[bool] = False
    owner: Optional[str]
    git_repo_id: Optional[int]

    @validator("add_disk")
    def check_add_disk(cls, v):
        try:
            if v:
                disks = list(map(int, v.strip().split(",")))
                _ = [int(disk) for disk in disks]
            return v
        except:
            raise ValueError("The type of add_disk is not validate.")

class SuiteCreate(SuiteBase):
    name: str
    group_id: int

class SuiteUpdate(SuiteBase, UpdateBaseModel):
    name: Optional[str]


class SuiteDirectoryUpdate(BaseModel):
    directory_id: int


class CaseBase(SuiteBase):
    suite: str
    description: str
    preset: Optional[str]
    steps: str
    expection: str
    automatic: bool
    usabled: Optional[bool] = False
    code: Optional[str]

class CaseCreate(CaseBase):
    name: str
    group_id: int

class CaseBaselineCommitCreate(CaseBase):
    name: str
    group_id: int
    parent_id: int


class CaseUpdate(CaseBase, UpdateBaseModel):
    name: Optional[str]
    suite: Optional[str]
    description: Optional[str]
    preset: Optional[str]
    steps: Optional[str]
    expection: Optional[str]
    automatic: Optional[bool]


class CaseBaseSchemaWithSuiteId(SuiteBase):
    suite_id: int
    description: str
    preset: Optional[str]
    steps: str
    expection: str
    automatic: bool
    usabled: Optional[bool] = False
    code: Optional[str]


class CaseUpdateSchemaWithSuiteId(CaseBaseSchemaWithSuiteId, UpdateBaseModel):
    name: Optional[str]
    suite_id: Optional[int]
    description: Optional[str]
    preset: Optional[str]
    steps: Optional[str]
    expection: Optional[str]
    automatic: Optional[bool]

class AddCaseCommitSchema(BaseModel):
    title: str
    creator_id: int = None
    description: str = None  # 提交commit时的description
    case_description: str = None  # case本身的description
    case_detail_id: int
    machine_type: str = None
    machine_num: int = None
    preset: str = None
    steps: str = None
    expectation: str = None
    remark: str = None
    status: str = None
    permission_type: str = None
    source: List
    case_mod_type: str

class UpdateCaseCommitSchema(BaseModel):
    title: str = None
    description: str = None
    machine_type: str = None
    machine_num: int = None
    preset: str = None
    steps: str = None
    expectation: str = None
    remark: str = None
    status: str = None
    open_edit: bool = False

class CaseCommitBasic(AddCaseCommitSchema):
    id: int
    reviewer_id: int
    reviewer_name: int
    case_detail_id: int
    creator_name: str


class CommitQuerySchema(PageBaseSchema):
    title: str = None
    user_type: Literal['creator', 'all']
    user_type: str = None
    query_type: str = None


class AddCommitCommentSchema(BaseModel):
    parent_id: int
    content: str

class UpdateCommitCommentSchema(BaseModel):
    content: str

class CaseCommitBatch(BaseModel):
    commit_ids: List[int] = None


class QueryHistorySchema(PageBaseSchema):
    start_time: str = None
    end_time: str = None
    title: str = None

import re
from typing import Optional

from pydantic import BaseModel, constr, validator
from pydantic.class_validators import root_validator
from typing_extensions import Literal
from typing import List

from server.model.testcase import Suite, Case
from server.schema.base import PermissionBase, UpdateBaseModel, PageBaseSchema
from server.schema import MachineType, PermissionType, TestType, TestLevel, CaseNodeType


class CaseNodeBodySchema(BaseModel):
    title: str
    type: CaseNodeType
    parent_id: Optional[int]
    group_id: int
    suite_id: Optional[int]
    case_id: Optional[int]
    is_root: bool = True
    in_set: bool = False
    permission_type: Optional[PermissionType] = "group"
    milestone_id: Optional[int]

    @root_validator
    def validate_suite(cls, values):
        if values["parent_id"]:
            values["is_root"] = False
            if values["in_set"] is True and values["milestone_id"]:
                raise ValueError("the case set can not relate to any milestone")
        else:
            if values["in_set"] is False and not values["milestone_id"]:
                raise ValueError("the testing strategy needs relating to milestone")

        if values["is_root"] is True and values["in_set"] is True:
            values["title"] = "用例集"

        if values["in_set"] is False and values["title"] == "用例集":
            raise ValueError("title is not valid for this type of node")

        if values["type"] == 'suite':
            if not values["suite_id"]:
                raise ValueError("The case_node should relate to one suite")

            suite = Suite.query.filter_by(id=values["suite_id"]).first()
            if not suite:
                raise ValueError("The suite to be related is not exist")

        elif values["type"] == 'case':
            if not values["case_id"]:
                raise ValueError("The case_node should relate to one case")

            case = Case.query.filter_by(id=values["case_id"]).first()
            if not case:
                raise ValueError("The case to be related is not exist")

        return values


class CaseNodeBodyInternalSchema(CaseNodeBodySchema):
    org_id: int


class CaseNodeQuerySchema(BaseModel):
    group_id: int
    title: Optional[str]


class CaseNodeItemQuerySchema(BaseModel):
    title: Optional[str]


class CaseNodeUpdateSchema(BaseModel):
    title: Optional[str]


class CaseNodeBaseSchema(BaseModel):
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
    permission_type: Optional[PermissionType] = "group"

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


class CaseNodeCommitCreate(CaseBase):
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
    automatic: bool
    usabled: Optional[bool] = False
    code: Optional[str]


class CaseUpdateSchemaWithSuiteId(UpdateBaseModel):
    name: Optional[str]
    suite_id: Optional[int]
    automatic: Optional[bool]
    usabled: Optional[bool]
    code: Optional[str]


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


class CheckRound(BaseModel):
    rounds: dict = None

    @validator("rounds")
    def check_rounds(cls, rounds):
        if rounds:
            for key, value in rounds.items():
                pattern = re.compile(r"^R[1-9]\d*$")
                if not pattern.findall(key):
                    raise ValueError("rounds key error! key should be like Rx")
                if value not in [0, 1]:
                    raise ValueError("rounds value error! value should be 0 or 1")
            round_keys = list(rounds.keys())
            if any(int(round_keys[i + 1].strip('R')) - int(round_keys[i].strip('R')) != 1 for i in
                   range(0, len(round_keys) - 1)):
                raise ValueError("rounds not in correct order!")
        return str(rounds)


class CheckRatio(BaseModel):
    ratio: str = None

    @validator("ratio")
    def check_ratio(cls, ratio):
        if ratio:
            _ratio = float(ratio.strip('%')) / 100.0
            if not 0 <= _ratio <= 1:
                raise ValueError("ratio is around 0-100%")
        return ratio


class AddChecklistSchema(CheckRound, CheckRatio):
    check_item: str
    rounds: dict
    lts: bool = False
    lts_spx: bool = False
    innovation: bool = False


class UpdateChecklistSchema(CheckRound, CheckRatio):
    check_item: str = None
    lts: bool = None
    lts_spx: bool = None
    innovation: bool = None


class QueryChecklistSchema(PageBaseSchema):
    check_item: str = None

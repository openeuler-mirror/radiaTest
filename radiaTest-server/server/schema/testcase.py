# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author :
# email :
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################

from typing import Optional, List
from pydantic import BaseModel, validator
from pydantic.class_validators import root_validator
from pydantic.networks import HttpUrl
from typing_extensions import Literal

from server.model.testcase import Suite, Case
from server.schema.base import PermissionBase, UpdateBaseModel, PageBaseSchema
from server.schema import MachineType, PermissionType, CaseNodeType, CommitType
from server.utils.text_utils import check_illegal_lables


class PermissionBaseSchema(BaseModel):
    creator_id: str
    permission_type: PermissionType
    group_id: Optional[int] = None
    org_id: int


class CaseNodeBodySchema(BaseModel):
    title: Optional[str]
    type: CaseNodeType
    parent_id: Optional[int]
    group_id: Optional[int]
    org_id: Optional[int]
    suite_ids: List[int] = None
    case_ids: List[int] = None
    multiselect: bool = False
    suite_id: Optional[int]
    case_id: Optional[int]
    baseline_id: Optional[int]
    is_root: bool = True
    in_set: bool = False
    permission_type: PermissionType = "group"
    milestone_id: Optional[int]

    @root_validator
    def validate_suite(cls, values):
        if values["parent_id"]:
            values["is_root"] = False
            if values["in_set"] is True and values["milestone_id"]:
                raise ValueError("the case set can not relate to any milestone")
        else:
            if values["in_set"] is False and not values["milestone_id"] and values["type"] == "baseline":
                raise ValueError("the testing baseline needs relating to milestone")

        if values["is_root"] is True and values["in_set"] is True:
            values["title"] = "用例集"
            values["type"] = "directory"

        if values["in_set"] is False and values["title"] == "用例集":
            raise ValueError("title is not valid for this type of node")

        if values["type"] == 'suite':
            if not values["parent_id"]:
                raise ValueError("suite must have a parent case-node")

            if values["multiselect"]:
                if not values["suite_ids"]:
                    raise ValueError("The case-node should relate to suite")
            else:
                if not values["suite_id"]:
                    raise ValueError("The case-node should relate to one suite")

                suite = Suite.query.filter_by(id=values["suite_id"]).first()
                if not suite:
                    raise ValueError("The suite to be related is not exist")

        elif values["type"] == 'case':
            if not values["parent_id"]:
                raise ValueError("case must have a parent case-node")

            if values["multiselect"]:
                if not values["case_ids"]:
                    raise ValueError("The case-node should relate to case")
            else:
                if not values["case_id"]:
                    raise ValueError("The case-node should relate to one case")

                case = Case.query.filter_by(id=values["case_id"]).first()
                if not case:
                    raise ValueError("The case to be related is not exist")

        return values


class CaseNodeBodyInternalSchema(CaseNodeBodySchema):
    org_id: int


class CaseNodeQuerySchema(BaseModel):
    group_id: Optional[int]
    org_id: Optional[int]
    title: Optional[str]

    @root_validator
    def validate_query(cls, values):
        if values["org_id"] and values["group_id"]:
            raise ValueError("org_id and group_id should not be provided in same request")
        return values


class CaseNodeItemQuerySchema(BaseModel):
    title: Optional[str]
    org_id: int = None


class CaseSetNodeQueryBySuiteSchema(BaseModel):
    title: Optional[str]
    suite_id: Optional[int]
    org_id: int = None

    @root_validator
    def validate_suite(cls, values):
        if not values["title"] and values["suite_id"]:
            raise ValueError("suite name or suite_id must be set")
        return values


class CaseNodeUpdateSchema(BaseModel):
    title: Optional[str]
    milestone_id: Optional[int]


class CaseNodeBaseSchema(BaseModel):
    id: int
    title: str
    type: str
    group_id: Optional[int]
    org_id: Optional[int]
    suite_id: int = None
    case_id: int = None
    in_set: bool = False


class SuiteQuery(PageBaseSchema):
    name: str = None
    machine_num: int = None
    machine_type: str = None
    owner: str = None
    description: str = None
    deleted: bool = False
    git_repo_id: Optional[int]
    org_id: int = None


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
    permission_type: PermissionType = "group"
    group_id: Optional[int]
    org_id: Optional[int]

    @validator("add_disk")
    def check_add_disk(cls, v):
        if v:
            disks = list(map(int, v.strip().split(",")))
            _ = [int(disk) for disk in disks]
        return v


class SuiteCreate(SuiteBase):
    name: str


class SuiteUpdate(SuiteBase):
    name: Optional[str]


class DeleteSchema(BaseModel):
    case_node_id: Optional[int]


class SuiteBaseUpdate(BaseModel):
    name: Optional[str]
    machine_num: Optional[int]
    machine_type: Optional[MachineType]
    add_network_interface: Optional[int]
    add_disk: Optional[str]
    remark: Optional[str]

    @validator("add_disk")
    def check_add_disk(cls, v):
        if v:
            disks = list(map(int, v.strip().split(",")))
            _ = [int(disk) for disk in disks]
            return v


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


class CaseQuery(PageBaseSchema):
    name: str = None
    test_level: str = None
    test_type: str = None
    machine_num: int = None
    machine_type: str = None
    suite_name: str = None
    owner: str = None
    description: str = None
    automatic: bool = None
    deleted: bool = False
    suite_id: int = None
    org_id: int = None


class CaseCreate(CaseBase):
    name: str
    group_id: Optional[int]
    org_id: Optional[int]


class CaseCreateBody(CaseCreate, CaseNodeBodySchema):
    suite: str = None
    title: Optional[str] = None
    type: Optional[CaseNodeType] = "case"

    @root_validator
    def validate_values(cls, values):
        if not values["title"]:
            values["title"] = values["name"]
        if values["type"] != "case":
            raise ValueError("The case_node type should be case.")
        return values


class CaseNodeCommitCreate(CaseBase):
    name: str
    group_id: int
    parent_id: int


class CaseUpdate(CaseBase):
    name: Optional[str]
    suite: Optional[str]
    description: Optional[str]
    preset: Optional[str]
    steps: Optional[str]
    expection: Optional[str]
    automatic: Optional[bool]


class CaseCaseNodeUpdate(CaseUpdate):
    title: Optional[str] = None

    @root_validator
    def validate_values(cls, values):
        if values["name"] and not values["title"]:
            values["title"] = values["name"]
        return values


class CaseBaseSchemaWithSuiteId(SuiteBase):
    suite_id: int
    automatic: bool
    usabled: Optional[bool] = False
    code: Optional[str]


class CaseUpdateSchemaWithSuiteId(SuiteBase, UpdateBaseModel, PermissionBaseSchema):
    name: Optional[str]
    suite_id: Optional[int]
    automatic: Optional[bool]
    usabled: Optional[bool]
    code: Optional[str]


class AddCaseCommitSchema(BaseModel):
    case_description: str = None  # case本身的description
    case_detail_id: int
    machine_type: str = None
    machine_num: int = None
    preset: str = None
    steps: str = None
    expectation: str = None
    remark: str = None


class SuiteDocumentBodySchema(BaseModel):
    title: str
    url: HttpUrl
    permission_type: Optional[PermissionType] = "group"


class SuiteDocumentQuerySchema(BaseModel):
    org_id: int = None
    title: str = None


class SuiteDocumentUpdateSchema(BaseModel):
    title: str = None
    url: HttpUrl = None
    suite_id: int = None


class BaselineCreateSchema(BaseModel):
    title: str = None
    milestone_id: int = None
    group_id: Optional[int]
    org_id: Optional[int]
    permission_type: Optional[PermissionType] = "group"


class CaseNodeRelateSchema(BaseModel):
    suite_id: int
    case_ids: List[int]
    baseline_id: Optional[int]


class ResourceQuerySchema(BaseModel):
    commit_type: CommitType


class CaseSetQuerySchema(BaseModel):
    commit_type: CommitType = 'week'


class CaseNodeSuitesCreateSchema(PermissionBase):
    suites: List[int]


class OrphanSuitesQuerySchema(PageBaseSchema):
    name: Optional[str]
    owner: Optional[str]
    framework_name: Optional[str]
    git_repo_url: Optional[str]


class CasefileExportSchema(BaseModel):
    filetype: Literal['xlsx', 'md'] = 'xlsx'


class CaseNodeBodyQuerySchema(BaseModel):
    milestone_id: int


class CaseV2Query(PageBaseSchema):
    name: str = None
    baseline_id: int = None
    description: str = None
    automatic: bool = None


class TestResultEventSchemaV2(BaseModel):
    org_id: int
    milestone_id: int
    case_id: int
    result: str
    log_url: Optional[str]
    fail_type: Optional[str]
    details: Optional[str]
    running_time: Optional[int]

    @validator("details")
    def check_details(cls, v):
        if v:
            v = check_illegal_lables(v)

            return v


class TestResultQuerySchema(BaseModel):
    milestone_id: int
    case_id: int


class TestCaseBase:
    def __init__(self, parent_id: int, permission_type: str = 'public', org_id: int = None, group_id: int = None):
        self.parent_id = parent_id  # 被创建case类型节点的父节点
        self.permission_type = permission_type  # 被创建case类型节点的权限类型
        self.org_id = org_id  # 被创建case类型节点的所属组织
        self.group_id = group_id  # 被创建case类型节点的所属团队


class CreateCaseInstance(TestCaseBase):
    def __init__(
            self,
            parent_id: int,
            case_name: str,
            case_id: int,
            permission_type: str = 'public',
            org_id: int = None,
            group_id: int = None
    ):
        super().__init__(parent_id, permission_type, org_id, group_id)
        self.case_name = case_name  # 被创建case类型节点关联的用例名
        self.case_id = case_id  # 被创建case类型节点关联的用例ID


class SuiteNodeInstance(TestCaseBase):
    def __init__(
            self,
            parent_id: int,
            suite_id: int,
            permission_type: str = 'public',
            org_id: int = None,
            group_id: int = None,
            user_id: str = None,
    ):
        super().__init__(parent_id, permission_type, org_id, group_id)
        self.suite_id = suite_id   # 被创建suite类型节点关联的用例ID
        self.user_id = user_id     # 创建异步任务的当前用户id

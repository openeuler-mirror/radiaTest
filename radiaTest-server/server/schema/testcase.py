# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author : MDS_ZHR
# email : 331884949@qq.com
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################
# 用例管理(Testcase)相关接口的schema

from typing import Optional
from typing import List
from pydantic import BaseModel, validator
from pydantic.class_validators import root_validator
from typing_extensions import Literal
from server.model.testcase import Suite, Case
from server.schema.base import UpdateBaseModel, PageBaseSchema
from server.schema import MachineType, PermissionType, CaseNodeType
from server.schema.base import PermissionBase, UpdateBaseModel, PageBaseSchema
from server.schema import MachineType, PermissionType, CaseNodeType, CommitType



class PermissionBaseSchema(BaseModel):
    creator_id: int
    permission_type: PermissionType
    group_id: Optional[int] = None
    org_id: int



class CaseNodeBodySchema(BaseModel):
    title: str
    type: CaseNodeType
    parent_id: Optional[int]
    group_id: Optional[int]
    org_id: Optional[int]
    suite_id: Optional[int]
    case_id: Optional[int]
    baseline_id: Optional[int]
    is_root: bool = True
    in_set: bool = False
    permission_type: PermissionType = "group"
    milestone_id: Optional[int]

    @root_validator
    def validate_suite(cls, values):
        if values["permission_type"] == "org":
            if not values["org_id"]:
                raise ValueError("The case_node should relate to one org")

        if values["permission_type"] == "group":
            if not values["group_id"]:
                raise ValueError("The case_node should relate to one group")

        if values["parent_id"]:
            values["is_root"] = False
            if values["in_set"] is True and values["milestone_id"]:
                raise ValueError("the case set can not relate to any milestone")
        else:
            if values["in_set"] is False and not values["milestone_id"] and  values["type"] == "baseline":
                raise ValueError("the testing baseline needs relating to milestone")

        if values["is_root"] is True and values["in_set"] is True:
            values["title"] = "用例集"
            values["type"] = "directory"

        if values["in_set"] is False and values["title"] == "用例集":
            raise ValueError("title is not valid for this type of node")

        if values["type"] == 'suite':
            if not values["suite_id"]:
                raise ValueError("The case-node should relate to one suite")

            suite = Suite.query.filter_by(id=values["suite_id"]).first()
            if not suite:
                raise ValueError("The suite to be related is not exist")

        elif values["type"] == 'case':
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
        try:
            if v:
                disks = list(map(int, v.strip().split(",")))
                _ = [int(disk) for disk in disks]
            return v
        except (ValueError, AttributeError, TypeError) as e:
            raise ValueError("The type of add_disk is not validate.") from e



class SuiteCreate(SuiteBase):
    name: str
    parent_id: int


class SuiteCreateBody(SuiteCreate, CaseNodeBodySchema):
    parent_id: int
    title: Optional[str] = None
    type: Optional[CaseNodeType] = "suite"


    @root_validator
    def validate_suite(cls, values):
        if not values["title"]:
            values["title"] = values["name"]
        if values["type"] != "suite":
            raise ValueError("The case_node type should be suite.")
        return values


class SuiteUpdate(SuiteBase):
    name: Optional[str]


class DeleteSchema(BaseModel):
    case_node_id:  Optional[int]


class SuiteCaseNodeUpdate(SuiteBase):
    name: Optional[str]
    title: Optional[str]
    

    @root_validator
    def validate_suite(cls, values):
        if values["name"] and not values["title"]:
            values["title"] = values["name"]
        return values


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
    title: str
    creator_id: int = None
    description: str = None  # 提交commit时的description
    case_description: str = None  # case本身的description
    case_detail_id: int# = None
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


class SuiteDocumentBodySchema(BaseModel):
    title: str = None
    url: str = None
    permission_type: Optional[PermissionType] = "group"


class SuiteDocumentQuerySchema(BaseModel):
    id: int = None
    suite_id: int = None


class SuiteDocumentUpdateSchema(BaseModel):
    title: str = None
    url: str = None
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
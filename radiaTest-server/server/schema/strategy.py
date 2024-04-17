# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Date : 2023/2/13 14:00:00
# License : Mulan PSL v2
#####################################
# 测试设计(Strategy)相关接口的schema

from typing import Optional
from pydantic import BaseModel
from pydantic.class_validators import root_validator
from server.schema import StrategyImportFileType, StrategyCommitStatus
from server.schema.testcase import SuiteCreate
from server.schema.base import PageBaseSchema


class FeatureSetBodySchema(BaseModel):
    feature: str
    no: str
    owner: Optional[list]
    pkgs: Optional[str]
    release_to: Optional[str]
    sig: Optional[list]
    task_id: Optional[int]
    url: Optional[str]


class StrategyRelateSchema(BaseModel):
    feature_id: int
    is_new: Optional[bool] = False


class FeatureSetUpdateSchema(BaseModel):
    feature: Optional[str]
    no: Optional[str]
    owner: Optional[list]
    sig: Optional[list]
    pkgs: Optional[str]
    release_to: Optional[str]
    task_id: Optional[int]
    url: Optional[str]


class FeatureQuerySchema(BaseModel):
    feature_id: Optional[int]
    is_new: Optional[bool]


class StrategyTemplateBodySchema(BaseModel):
    title: str
    tree: dict


class StrategyTemplateQuerySchema(BaseModel):
    title: Optional[str]


class FeatureNodeBodySchema(BaseModel):
    title: str
    parent_id: Optional[int]
    is_root: bool = False
    strategy_template_id: Optional[int]

    @root_validator
    def validate_all(cls, values):
        if not values["parent_id"]:
            values["is_root"] = True
        return values


class FeatureNodeUpdateSchema(BaseModel):
    title: Optional[str]


class StrategyBodySchema(BaseModel):
    tree: Optional[dict]
    product_feature_id: Optional[int]
    file_type: Optional[StrategyImportFileType] = "New"


class StrategyCommitBodySchema(BaseModel):
    commit_tree: dict
    commit_status: Optional[StrategyCommitStatus] = "staged"


class StrategyUpdateSchema(BaseModel):
    tree: Optional[dict]


class StrategyCommitUpdateSchema(BaseModel):
    commit_tree: Optional[dict]
    commit_status: Optional[str]


class CommitBodySchema(BaseModel):
    title: str
    body: Optional[str]


class FeatureApplySchema(BaseModel):
    strategy_template_id: Optional[int]
    strategy_node_id: Optional[int]


class StrategyCaseNodeBodySchema(StrategyBodySchema, SuiteCreate):
    parent_id: Optional[int]


class StrategyQuerySchema(PageBaseSchema):
    type: Optional[str] = None
    org_id: Optional[int] = None


class StrategyPermissionBaseSchema(BaseModel):
    org_id: Optional[int]
    user_id: Optional[str]

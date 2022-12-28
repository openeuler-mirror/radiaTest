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
# 基线模板(Baseline_template)相关接口的schema

import re
from typing import Optional, List
from pydantic import BaseModel, constr, validator
from pydantic.class_validators import root_validator
from server.model.group import Group
from server.model.organization import Organization
from server.schema import CaseNodeType, PermissionType, BaselineTemplateType



class BaselineTemplateBaseSchema(BaseModel):
    title: str
    type: BaselineTemplateType
    group_id: int = None
    org_id: int = None
    openable: bool = True



class BaseNodeBaseSchema(BaseModel):
    title: str
    type: BaselineTemplateType
    group_id: int = None
    org_id: int = None
    is_root: bool = False
    baseline_template_id: int = None
    case_node_id: int = None



class BaselineTemplateBodySchema(BaselineTemplateBaseSchema):
    permission_type: Optional[PermissionType] = "group"

    @root_validator
    def validate_type(cls, values):
        if values["type"] == 'org':
            values["permission_type"] = "org"
            if not values["org_id"]:
                raise ValueError("The base_node should relate to one org")
            org = Organization.query.filter_by(id=values["org_id"]).first()
            if not org:
                raise ValueError("The org to be related is not exist")

        elif values["type"] == 'group':
            if not values["group_id"]:
                raise ValueError("The base_node should relate to one group")
            group = Group.query.filter_by(id=values["group_id"]).first()
            if not group:
                raise ValueError("The group to be related is not exist")

        return values



class BaseNodeBodySchema(BaseModel):
    title: str = None
    parent_id: Optional[int]
    is_root: bool = True
    type: Optional[CaseNodeType] = "directory"
    case_node_id :Optional[int]

    @root_validator
    def validate_all(cls, values):        
        if values["parent_id"]:
            values["is_root"] = False
            if values.get("type") == "baseline":
                raise ValueError("type of root node should be baseline")
        elif values.get("is_root"):
            if values.get("type") != "baseline":
                raise ValueError("type of root node shoule be baseline")
        return values



class BaselineTemplateBodySchema(BaseModel):
    title: str
    openable: bool = False
    type: BaselineTemplateType
    org_id: Optional[int]
    group_id: Optional[int]    
    
    @root_validator
    def validate_query(cls, values):
        if values.get("org_id") and values.get("group_id"):
            raise ValueError("org_id and group_id should not be provided in same request")

        if values.get("type") == "group" and not values.get("group_id"):
            raise ValueError("The group_id should be provided.")
        
        if values.get("type") == "org" and not values.get("org_id"):
            raise ValueError("The org_id should be provided.")

        return values



class BaselineTemplateQuerySchema(BaseModel):
    org_id: Optional[int]
    group_id: Optional[int]
    title: Optional[str]

    @root_validator
    def validate_query(cls, values):
        if values["org_id"] and values["group_id"]:
            raise ValueError(
                "org_id and group_id should not be provided in same request"
            )
        return values



class BaselineTemplateItemQuerySchema(BaseModel):
    org_id: Optional[int]
    group_id: Optional[int]
    title: Optional[str]
    openable: bool = True



class BaselineTemplateUpdateSchema(BaseModel):
    title: Optional[str]
    openable: bool = True



class BaselineTemplateCreateSchema(BaseModel):
    title: str = None
    type: BaselineTemplateType = "group"
    group_id: int = None
    permission_type: Optional[PermissionType] = "group"
    openable: bool = True



class BaselineTemplateUpdateSchema(BaseModel):
    title: Optional[str] = None
    openable: bool = None


class BaseNodeUpdateSchema(BaseModel):
    title: str = None



class BaseNodeQuerySchema(BaseModel):
    group_id: Optional[int]
    org_id: Optional[int]
    case_node_id: Optional[int]
    openable: bool = True


   
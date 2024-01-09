# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from typing_extensions import Literal
from typing import Optional
from pydantic import BaseModel
from server.schema.base import PageBaseSchema, PermissionBase


class ManualJobCreate(PermissionBase):
    cases: str
    name: str
    milestone_id: int


class ManualJobQuery(PageBaseSchema):
    status: int
    case_id: Optional[int]
    job_group_id: Optional[int]
    name: Optional[str]


class ManualJobLogModify(BaseModel):
    step: int
    content: Optional[str]
    passed: Optional[bool]


class ManualJobLogDelete(BaseModel):
    step: Optional[int]


class ManualJobGroupQuery(PageBaseSchema):
    milestone_id: Optional[int]
    name: Optional[str]
    status: int = 0  # get请求为str类型，无法自动转换只能指定int  0执行中 、1已完成


class ManualJobGroupStatus(BaseModel):
    status: Literal[0, 1] = 1


class ManualJobGroupReport(BaseModel):
    report: str


class ManualJobModify(BaseModel):
    result: Literal[0, 1, 2] = 1  # 0 失败 1 成功  2 block
    remark: Optional[str]


class ManualJobGroupCopySchema(BaseModel):
    id: int
    milestone_id: Optional[int]

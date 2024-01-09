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

from pydantic import BaseModel, constr

from server.schema.base import PermissionBase, PageBaseSchema


class TemplateQuery(PageBaseSchema):
    name: Optional[constr(max_length=128)]
    milestone_id: Optional[int]
    git_repo_id: Optional[int]
    description: Optional[constr(max_length=255)]
    type: Literal['automatic', 'manual'] = "automatic"


class TemplateUpdate(BaseModel):
    name: Optional[constr(max_length=128)]
    milestone_id: Optional[int]
    git_repo_id: Optional[int]
    description: Optional[constr(max_length=255)]


class TemplateCloneBase(PermissionBase):
    id: int


class TemplateCreateByimportFile(PermissionBase):
    name: constr(max_length=128)
    description: Optional[constr(max_length=255)]
    milestone_id: int
    git_repo_id: Optional[int]
    type: Literal['automatic', 'manual'] = "automatic"
    cases: Optional[str]


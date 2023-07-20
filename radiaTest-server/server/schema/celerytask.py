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

from typing import Optional

from pydantic import BaseModel

from server.schema import PermissionType


class CeleryTaskQuerySchema(BaseModel):
    tid: Optional[str]
    status: Optional[str]
    object_type: Optional[str]
    page_num: int
    page_size: int


class CeleryTaskCreateSchema(BaseModel):
    tid: str
    status: Optional[str]
    object_type: str
    vmachine_id: Optional[int]
    user_id: Optional[str]


class CeleryTaskUserInfoSchema(BaseModel):
    auth: str
    user_id: str
    group_id: Optional[int]
    org_id: Optional[int]
    permission_type: PermissionType = "person"

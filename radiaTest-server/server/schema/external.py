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

import os
from typing_extensions import Literal
from typing import List, Optional
from urllib import request, error

from pydantic import BaseModel, Field, validator
from pydantic.networks import HttpUrl

from server.schema import MachineType
from server.schema.base import UpdateBaseModel


class OpenEulerUpdateTaskBase(BaseModel):
    product: str
    version: str
    pkgs: List[str]
    base_update_url: HttpUrl
    epol_update_url: Optional[HttpUrl]

    @validator("base_update_url")
    def check_base_url(cls, v):
        try:
            request.urlopen(os.path.join(v, 'aarch64/'))
            request.urlopen(os.path.join(v, 'x86_64/'))

        except (error.HTTPError, error.URLError):
            raise ValueError("base_update_url:%s is not available." % v)

        return v

    @validator("epol_update_url")
    def check_epol_url(cls, v):
        if v:
            try:
                request.urlopen(os.path.join(v, 'aarch64/'))
                request.urlopen(os.path.join(v, 'x86_64/'))

            except (error.HTTPError, error.URLError):
                raise ValueError("epol_update_url:%s is not available." % v)

            return v


class RepoCaseUpdateBase(UpdateBaseModel):
    machine_num: Optional[int] = 1
    machine_type: Optional[MachineType] = "kvm"
    add_network_interface: Optional[int]
    add_disk: Optional[str]
    usabled: bool = False
    code: Optional[str]


class LoginOrgListSchema(BaseModel):
    org_id: int = Field(alias="id")
    org_name: str = Field(alias="name")
    org_avatar: Optional[str] = Field(alias="avatar_url")
    cla_sign_url: Optional[str]
    enterprise_join_url: Optional[str]
    authority: Optional[str]


class VmachineExistSchema(BaseModel):
    domain: str


class DeleteCertifiSchema(BaseModel):
    ip: str


class QueryTestReportFileSchema(BaseModel):
    file_type: Literal["md", "html"]
    milestone_name: str

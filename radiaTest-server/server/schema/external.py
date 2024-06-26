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
from urllib import request, error
from urllib.parse import urlparse
from typing import List, Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field, validator
from pydantic.networks import HttpUrl

from flask import current_app


class OpenEulerUpdateTaskBase(BaseModel):
    product: str
    version: str
    pkgs: List[str]
    base_update_url: HttpUrl
    epol_update_url: Optional[HttpUrl]

    @staticmethod
    @validator("base_update_url")
    def check_base_url(v):
        parsed_url = urlparse(v)
        domain = parsed_url.netloc
        if domain != current_app.config.get("REPO_DOMAIN"):
            raise ValueError("repo domain is not correct")
        request.urlopen(os.path.join(v, 'aarch64/'))
        request.urlopen(os.path.join(v, 'x86_64/'))

        return v

    @staticmethod
    @validator("epol_update_url")
    def check_epol_url(v):
        if v:
            parsed_url = urlparse(v)
            domain = parsed_url.netloc
            if domain != current_app.config.get("REPO_DOMAIN"):
                raise ValueError("repo domain is not correct")
            request.urlopen(os.path.join(v, 'aarch64/'))
            request.urlopen(os.path.join(v, 'x86_64/'))

        return v


class LoginOrgListSchema(BaseModel):
    org_id: int = Field(alias="id")
    org_name: str = Field(alias="name")
    org_avatar: Optional[str] = Field(alias="avatar_url")
    enterprise_join_url: Optional[str]
    authority: Optional[str]


class QueryTestReportFileSchema(BaseModel):
    file_type: Literal["md", "html"]
    milestone_name: str


class TestResultEventSchema(BaseModel):
    org: str
    baseline: str
    testsuite: str
    testcase: str
    result: str
    log_url: Optional[str]
    fail_type: Optional[str]
    details: Optional[str]
    running_time: Optional[int]

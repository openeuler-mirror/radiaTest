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

from typing import Optional, Literal
from pydantic import BaseModel, constr, root_validator

from server.model import Product
from server.utils.db import Precise
from server.schema.base import PermissionBase, TimeBaseSchema, PageBaseSchema
from server.schema import PermissionType


class ProductBase(PermissionBase, TimeBaseSchema):
    name: constr(max_length=32)
    version: constr(max_length=32)
    description: Optional[constr(max_length=255)]
    version_type: Literal["LTS", "LTS-SPx", "INNOVATION"]
    is_forced_check: Optional[bool]
    #当前先允许ebs构建
    built_by_ebs: Optional[bool]

    @root_validator
    def check_duplicate(cls, values):
        product = Precise(
            Product, {"name": values.get("name"), "version": values.get("version")}
        ).first()
        if product:
            raise ValueError("The version of product has existed.")
        return values


class ProductUpdate(TimeBaseSchema):
    name: Optional[constr(max_length=32)]
    version: Optional[constr(max_length=32)]
    description: Optional[constr(max_length=255)]


class ProductQueryBase(PageBaseSchema):
    name: Optional[constr(max_length=32)]
    version: Optional[constr(max_length=32)]
    description: Optional[constr(max_length=255)]
    start_time: Optional[str]
    end_time: Optional[str]
    released_time: Optional[str]
    permission_type: Optional[PermissionType]

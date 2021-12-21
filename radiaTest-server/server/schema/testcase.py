# -*- coding: utf-8 -*-
# @Author : Ethan-Zhang
# @Date   : 2021-09-06 20:39:53
# @Email  : ethanzhang55@outlook.com
# @License: Mulan PSL v2
# @Desc   :

from typing import Optional, List

from pydantic import BaseModel, constr, validator

from server.schema.base import UpdateBaseModel
from server.schema import MachineType, TestType, TestLevel


class SuiteBase(BaseModel):
    name: str
    test_type: Optional[TestType]
    test_level: Optional[TestLevel]
    machine_num: Optional[int] = 1
    machine_type: Optional[MachineType] = "kvm"
    add_network_interface: Optional[int]
    add_disk: Optional[str]
    remark: Optional[str]
    deleted: Optional[bool] = False
    owner: Optional[str]

    @validator("add_disk")
    def check_add_disk(cls, v):
        try:
            if v:
                disks = list(map(int, v.strip().split(",")))
                _ = [int(disk) for disk in disks]
            return v
        except:
            raise ValueError("The type of add_disk is not validate.")


class SuiteUpdate(SuiteBase, UpdateBaseModel):
    name: Optional[str]


class CaseBase(SuiteBase):
    suite: str
    description: str
    preset: Optional[str]
    steps: str
    expection: str
    automatic: bool


class CaseUpdate(CaseBase, UpdateBaseModel):
    name: Optional[str]
    suite: Optional[str]
    description: Optional[str]
    preset: Optional[str]
    steps: Optional[str]
    expection: Optional[str]
    automatic: Optional[bool]


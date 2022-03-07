# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-05 11:39:18
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


import shlex
import datetime
from typing import Optional
from ipaddress import IPv4Address
from subprocess import getstatusoutput

from flask import current_app
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, constr, validator, root_validator


from server.schema import Frame, PmachineState, Power, PermissionType
from server.schema.base import UpdateBaseModel

from server.utils.db import Precise
from server.utils.pssh import Connection

from server.model import Pmachine


class PmachineBase(BaseModel):
    mac: constr(max_length=17)
    frame: Frame
    bmc_ip: IPv4Address
    bmc_user: constr(max_length=32)
    bmc_password: constr(min_length=6, max_length=256)
    ip: Optional[IPv4Address]
    user: Optional[constr(max_length=32)]
    port: Optional[int]
    password: Optional[constr(min_length=6, max_length=256)]
    end_time: Optional[datetime.datetime]
    start_time: Optional[datetime.datetime]
    listen: Optional[int]
    description: Optional[str]
    state: Optional[PmachineState]
    occupier: Optional[str]

    @validator("bmc_password")
    def required_bmc_conditions(cls, v, values):
        exitcode, output = getstatusoutput(
            "ipmitool -I lanplus -H %s -U %s  -P %s power status"
            % (values.get("bmc_ip"), values.get("bmc_user"), v)
        )
        if exitcode != 0:
            raise ValueError("The infomation of BMC provided is wrong.")

        values["status"] = output.split()[-1]

        return v

    @validator("start_time")
    def check_start_time(cls, v):
        if v > datetime.datetime.now():
            raise ValueError("start_time invalid.")

        return v

    @root_validator
    def check_description(cls, values):
        if values.get("pmachine"):
            pmachine = values.get("pmachine").to_json()
            for key, value in values.items():
                if value != None:
                    pmachine.update({key: value})
            values = pmachine

        if values.get("state") == "occupied":
            values["start_time"] = datetime.datetime.now()
            if not values.get("description"):
                raise ValueError("The reasons for occupation must be stated.")

            if not values.get("end_time"):
                values["end_time"] = (
                    datetime.datetime.now() + datetime.timedelta(days=1)
                ).strftime("%Y-%m-%d %H:%M:%S")
            elif values.get("end_time") > (
                datetime.datetime.now()
                + datetime.timedelta(days=current_app.config.get("MAX_OCUPY_TIME"))
            ):
                raise ValueError(
                    "The max occupation duration is %s days."
                    % current_app.config.get("MAX_OCUPY_TIME")
                )

        elif values.get("state") == "idle":
            if values.get("pmachine") and values.get(
                "pmachine"
            ).description == current_app.config.get("CI_SIGN"):
                if values.get("pmachine").vmachine:
                    raise ValueError("There are virtual machines used under the host.")
            values["start_time"] = None
            values["end_time"] = None
            values["description"] = None
            values["listen"] = None

        if values.get("description") in [
            current_app.config.get("CI_PURPOSE"),
            current_app.config.get("CI_SIGN"),
        ]:
            values["start_time"] = datetime.datetime.now()
            values["end_time"] = (
                datetime.datetime.now() + relativedelta(years=+99)
            ).strftime("%Y-%m-%d %H:%M:%S")
            values["state"] = "occupied"

            if not all(
                (
                    values.get("ip"),
                    values.get("user"),
                    values.get("port"),
                    values.get("password"),
                )
            ):
                raise ValueError(
                    "As a CI host, ip、user、port、password must be provided."
                )

        if values.get("description") == current_app.config.get("CI_SIGN"):
            if not values.get("listen"):
                raise ValueError("As a CI host, listen must be provided.")

            if (
                getstatusoutput(
                    "ping -nq -c 3 -w 5 {}".format(shlex.quote(str(values.get("ip"))))
                )[0]
                != 0
            ):
                raise ValueError("ip address is not available.")

            conn = Connection(
                str(values.get("ip")),
                str(values.get("password")),
                values.get("port"),
                str(values.get("user")),
            )._conn()
            if not conn:
                raise ValueError(
                    "The information provided cannot be used in normal login using SSH."
                )
            conn.close()

            # TODO 发送消息到worker节点，确保server和worker正常通信 (lemon.higgins)

        return values


class PmachineUpdate(PmachineBase, UpdateBaseModel):
    mac: Optional[constr(max_length=17)]
    frame: Optional[Frame]
    bmc_ip: Optional[IPv4Address]
    bmc_user: Optional[constr(max_length=32)]
    bmc_password: Optional[constr(min_length=6, max_length=256)]

    @validator("id", pre=True)
    def check_id(cls, v, values):
        pmachine = Precise(Pmachine, {"id": v}).first()
        if not pmachine:
            raise ValueError("The selected machine no longer exists.")

        values["pmachine"] = pmachine
        return v

    @validator("description")
    def check_description(cls, v, values):
        desc = values.get("pmachine").description
        if desc == current_app.config.get("CI_SIGN"):
            if desc != v:
                virtual = values.get("pmachine").virtual.query.filter.all()
                if virtual:
                    raise ValueError(
                        "Some virtual machine on the worker, can't be deleted."
                    )

            if values.get("state") == "idle":
                raise ValueError("Worker can't be released.")

        if v == current_app.config.get("CI_SIGN"):
            if not values.get("listen"):
                listen = values.get("pmachine").listen
                if not listen:
                    raise ValueError("As a CI host, listen must be provided.")

        return v


class PmachineInstall(BaseModel):
    id: int
    milestone_id: int


class PmachinePower(BaseModel):
    id: int
    status: Power

# -*- coding: utf-8 -*-
# @Author: Your name
# @Date:   2022-04-12 11:25:48
# @Last Modified by:   Your name
import shlex
import datetime
from typing import Optional
from subprocess import getstatusoutput

from flask import current_app
from dateutil.relativedelta import relativedelta
from pydantic import conint, BaseModel, constr, validator, root_validator

from server.schema.base import PageBaseSchema
from server.schema import (
    Frame, 
    PmachineState, 
    Power, 
    PermissionType,  
    MachineGroupNetworkType
)
from server.utils.db import Precise
from server.utils.pssh import Connection
from server.model import Pmachine, MachineGroup
from server.schema.base import PermissionBase
from server.utils.iptype_util import ip_type

class MachineGroupCreateSchema(PermissionBase):
    """ 
    attr: websockify_listen should in range (1000, 99999)
    """
    name: str
    description: str
    network_type: MachineGroupNetworkType
    ip: str
    messenger_ip: str
    messenger_listen: int
    websockify_ip: Optional[str]
    websockify_listen: Optional[conint(ge=1000, le=99999)]


    @validator("ip")
    def check_ip_exist(cls, v):
        machine_group = MachineGroup.query.filter_by(ip=v).first()
        if machine_group is not None:
            raise ValueError("this ip of machine group is exist, duplication is not allowed")
        
        if not ip_type(v):
            raise ValueError("this ip of machine group format error")
        return v

    @validator("messenger_ip")
    def check_messenger_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this messenger_ip of machine group format error")
        return v

    @validator("websockify_ip")
    def check_websockify_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this websockify_ip of machine group format error")
        return v

class MachineGroupUpdateSchema(BaseModel):
    """ 
    attr: websockify_listen should in range (1000, 99999)
    """
    name: Optional[str]
    description: Optional[str]
    network_type: Optional[MachineGroupNetworkType]
    ip: Optional[str]
    messenger_ip: Optional[str]
    messenger_listen: Optional[int]
    websockify_ip: Optional[str]
    websockify_listen: Optional[conint(ge=1000, le=99999)]

    @validator("ip")
    def check_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this ip of machine group format error")
        return v

    @validator("messenger_ip")
    def check_messenger_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this messenger_ip of machine group format error")
        return v

    @validator("websockify_ip")
    def check_websockify_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this websockify_ip of machine group format error")
        return v

class MachineGroupQuerySchema(PageBaseSchema):
    """ 
    attr: websockify_listen should in range (1000, 99999)
    """
    text: Optional[str]
    network_type: Optional[MachineGroupNetworkType]
    messenger_ip: Optional[str]
    messenger_listen: Optional[int]
    websockify_ip: Optional[str]
    websockify_listen: Optional[conint(ge=1000, le=99999)]

    @validator("messenger_ip")
    def check_messenger_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this messenger_ip of machine group format error")
        return v

    @validator("websockify_ip")
    def check_websockify_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this websockify_ip of machine group format error")
        return v

class HeartbeatUpdateSchema(BaseModel):
    messenger_ip: str
    messenger_alive: bool
    pxe_alive: bool
    dhcp_alive: bool

    @validator("messenger_ip")
    def check_messenger_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this messenger_ip of machine group format error")
        return v


class PmachineQuerySchema(PageBaseSchema):
    machine_group_id: int
    mac: Optional[constr(max_length=17)]
    frame: Optional[Frame]
    bmc_ip: Optional[str]
    ip: Optional[str]
    occupier: Optional[str]
    description: Optional[str]
    state: Optional[PmachineState]


class PmachineBaseSchema(BaseModel):
    mac: constr(max_length=17)
    frame: Frame
    bmc_ip: str
    bmc_user: constr(max_length=32)
    bmc_password: constr(min_length=6, max_length=256)
    ip: Optional[str]
    user: Optional[constr(max_length=32)]
    port: Optional[int]
    password: Optional[constr(min_length=6, max_length=256)]
    end_time: Optional[datetime.datetime]
    start_time: Optional[datetime.datetime]
    listen: Optional[int]
    description: Optional[str]
    state: Optional[PmachineState]
    occupier: Optional[str]
    locked: Optional[bool] = False
    machine_group_id: Optional[int]
    status: Optional[Power]

    @validator("ip")
    def check_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this ip of machine group format error")
        return v

    @validator("bmc_ip")
    def check_bmc_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this bmc_ip of machine group format error")
        return v


    @validator("machine_group_id")
    def check_machine_group_id(cls, v):
        mg = MachineGroup.query.filter_by(id=v).first()
        if not mg:
            raise ValueError("The MachineGroup does not exist.")
        return v

    @validator("start_time")
    def check_start_time(cls, v):
        if v > datetime.datetime.now():
            raise ValueError("start_time invalid.")

        return v

    @root_validator
    def check_description(cls, values):
        if values["description"] == current_app.config.get("CI_HOST"):
            if not values.get("listen"):
                listen = values["listen"]
                if not listen:
                    raise ValueError("As a CI host, listen must be provided.")
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
            values["start_time"] = None
            values["end_time"] = None
            values["description"] = None
            values["listen"] = None
            values["occupier"] = None

        if values.get("description") in [
            current_app.config.get("CI_PURPOSE"),
            current_app.config.get("CI_HOST"),
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

        return values

class PmachineCreateSchema(PmachineBaseSchema, PermissionBase):
    mac: constr(max_length=17)
    frame: Frame
    bmc_ip: str
    bmc_user: constr(max_length=32)
    bmc_password: constr(min_length=6, max_length=256)

    @validator("bmc_ip")
    def check_bmc_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this bmc_ip of machine group format error")
        return v

class PmachineUpdateSchema(PmachineBaseSchema):
    mac: Optional[constr(max_length=17)]
    frame: Optional[Frame]
    bmc_ip: Optional[str]
    bmc_user: Optional[constr(max_length=32)]
    bmc_password: Optional[constr(min_length=6, max_length=256)]

    @validator("bmc_ip")
    def check_bmc_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this bmc_ip of machine group format error")
        return v

class PmachineInstallSchema(BaseModel):
    id: int
    milestone_id: int
    status: Power


class PmachinePowerSchema(BaseModel):
    id: int
    status: Power


class PmachineBriefSchema(BaseModel):
    ip: str
    description: str
    status: str
    bmc_ip: str
    
    @validator("ip")
    def check_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this ip of machine group format error")
        return v

    @validator("bmc_ip")
    def check_bmc_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("this bmc_ip of machine group format error")
        return v

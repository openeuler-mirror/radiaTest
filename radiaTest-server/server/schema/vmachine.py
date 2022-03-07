# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-05 11:39:33
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


import time
import json
import string
import random
from datetime import datetime, timedelta
from typing import List, Optional

from flask import current_app
from pydantic import BaseModel, conint, constr, Field, validator, root_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server.schema import (
    Frame,
    InstallMethod,
    VMStatus,
    CPUMode,
    NetBus,
    NetMode,
    DiskBus,
    DiskCache,
    VideoBus,
    PmSelectMode,
    PermissionType
)
from server.schema.base import UpdateBaseModel

from server.utils.db import Precise

from server.model import Vmachine, Vdisk, Pmachine
from server.config.settings import Config


class VmachineBase(BaseModel):
    method: InstallMethod
    frame: Frame
    description: constr(min_length=10, max_length=255)
    milestone_id: int
    pm_select_mode: Optional[PmSelectMode] = "auto"
    pmachine_id: int = 0
    name: Optional[constr(min_length=10, max_length=255)]
    memory: Optional[conint(ge=2048, le=Config.VM_MAX_MEMEORY)] = 4096
    sockets: Optional[conint(ge=1, le=Config.VM_MAX_SOCKET)] = 1
    cores: Optional[conint(ge=1, le=Config.VM_MAX_CORE)] = 2
    threads: Optional[conint(ge=1, le=Config.VM_MAX_THREAD)] = 4
    cpu_mode: Optional[CPUMode] = "host-passthrough"
    net_bus: Optional[NetBus] = "virtio"
    net_mode: Optional[NetMode] = "bridge"
    disk_bus: Optional[DiskBus] = "virtio"
    capacity: Optional[conint(ge=10, le=Config.VM_MAX_CAPACITY)] = 50
    disk_cache: Optional[DiskCache] = "default"
    video_bus: Optional[VideoBus] = "virtio"
    end_time: Optional[datetime] = datetime.now() + timedelta(
        days=Config.VM_DEFAULT_DAYS
    )

    @root_validator
    def check_name_and_endtime(cls, values):
        if not values.get("name"):
            values["name"] = (
                time.strftime("%y-%m-%d-")
                + str(time.time())
                + "-"
                + "".join(
                    random.choice(string.ascii_lowercase + string.digits)
                    for _ in range(10)
                )
            )

        if not values.get("end_time"):
            values["end_time"] = datetime.now() + timedelta(
                days=Config.VM_DEFAULT_DAYS
            )
        
        max_time = datetime.now() + timedelta(
            days=current_app.config.get("VM_MAX_DAYS")
        )
        
        if max_time < values.get("end_time"):
            raise ValueError(
                "max lifetime of virtual machine(days):%s"
                % current_app.config.get("VM_MAX_DAYS")
            )

        return values

    @validator("pmachine_id")
    def check_pmselect(cls, v, values):
        if values.get("pmselect") and values.get("pmselect") == "assign":
            pm = Precise(Pmachine, {"id": v}).first()
            if not pm:
                raise ValueError("Must select an existing pysical machine, when pmselect is assign.")

class VmachineUpdate(UpdateBaseModel):
    memory: Optional[conint(ge=2048, le=Config.VM_MAX_MEMEORY)] = 2048
    sockets: Optional[conint(ge=1, le=Config.VM_MAX_SOCKET)] = 1
    cores: Optional[conint(ge=1, le=Config.VM_MAX_CORE)] = 1
    threads: Optional[conint(ge=1, le=Config.VM_MAX_THREAD)] = 1
    end_time: Optional[datetime]

    @validator("end_time")
    def check_end_time(cls, v, values):
        try:
            create_time = (
                Precise(Vmachine, {"id": values.get("id")}).first().create_time
            )
        except (IntegrityError, SQLAlchemyError):
            raise ValueError("Must select an existing virtual machine.")

        max_time = create_time + timedelta(
            days=current_app.config.get("VM_MAX_DAYS")
        ).strftime("%Y-%m-%d")
        if max_time < v:
            raise ValueError(
                "The lifetime of virtual machine(days):%s"
                % current_app.config.get("VM_MAX_DAYS")
            )
        return v

class VmachineDelay(UpdateBaseModel):
    end_time: Optional[datetime]

    @validator("end_time")
    def check_end_time(cls, v, values):
        try: 
            vm = Precise(Vmachine, {"id": values.get("id")}).first()
        except (SQLAlchemyError, IntegrityError):
            raise ValueError("Must select an existing virtual machine.")
        
        dl = (v - vm.end_time).days
        if dl > current_app.config.get("VM_MAX_DAYS"):
            raise ValueError(
                "The lifetime of virtual machine(days):%s"
                % current_app.config.get("VM_MAX_DAYS")
            )

        return v


class Power(UpdateBaseModel):
    status: VMStatus


class VnicBase(BaseModel):
    vmachine_id: int
    mode: Optional[NetMode] = "bridge"
    bus: Optional[NetBus] = "virtio"
    mac: Optional[constr(max_length=48)]


class VdiskBase(BaseModel):
    bus: Optional[DiskBus] = "virtio"
    capacity: Optional[conint(ge=1, le=Config.VM_MAX_CAPACITY)] = 1
    cache: Optional[DiskCache] = "default"
    vmachine_id: int
    volume: Optional[str]

    @validator("volume")
    def check_volume(cls, v, values):
        vmachine = Precise(Vmachine, {"id": values.get("vmacine_id")})
        disk = vmachine.vdisk.query.all()
        sign = len(disk) + 1
        while [True]:
            v = vmachine.name + str()
            if not Precise(Vdisk, {"volume": v}).first():
                break
            sign += 1
        return v


class DeviceDelete(BaseModel):
    id: int

class DeviceBase(BaseModel):
    vmachine_id: int
    device: List[dict]
    
    @validator("vmachine_id")
    def validate_vmachine(cls, v, values):
        _vmachine = Vmachine.query.filter_by(id=v).first()
        if not _vmachine:
            raise ValueError("The vmachine to attach is not exist")
            
        return v

    @validator("device")
    def validate_device(cls, v, values):
        for item in v:       
            if not item.get("service") or not item.get("device"):
                raise ValueError("Value format of device is invalid")
        
        return v

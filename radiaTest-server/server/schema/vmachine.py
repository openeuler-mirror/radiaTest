from socket import socket
import time
import json
import string
import random
from datetime import datetime, timedelta
from typing import List, Optional
import pytz
from flask import current_app
from pydantic import BaseModel, conint, constr, Field, validator, root_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from server.schema.base import PermissionBase
from server.utils.iptype_util import ip_type
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
from server.schema.base import PageBaseSchema, UpdateBaseModel

from server.utils.db import Precise

from server.model import Vmachine, Vdisk, Pmachine
from server.config.settings import Config


class VmachineQuerySchema(PageBaseSchema):
    machine_group_id: int
    host_ip: Optional[str]
    frame: Optional[Frame]
    ip: Optional[str]
    description: Optional[str]
    name: Optional[str]


class VmachinePreciseQuerySchema(BaseModel):
    id: Optional[int]
    host_ip: Optional[str]
    frame: Optional[Frame]
    ip: Optional[str]
    description: Optional[str]
    name: Optional[str]


class VmachineBaseSchema(BaseModel):
    frame: Frame
    description: constr(min_length=10, max_length=255)
    milestone_id: int
    pmachine_id: int
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
    end_time: Optional[datetime] = None


class VmachineDataCreateSchema(VmachineBaseSchema, PermissionBase):
    milestone: str
    product: str
    end_time: str
    status: str 
        

    @validator("end_time")
    def check_end_time(cls, v):
        try:
            v = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except (RuntimeError, ValueError, KeyError, AttributeError):
            v = datetime.strptime(v, "%Y-%m-%d")
            v = v + timedelta(days=Config.VM_DEFAULT_DAYS)
        return v


class VmachineCreateSchema(VmachineBaseSchema, PermissionBase):
    password: Optional[str]
    machine_group_id: Optional[int]
    pmachine_id: Optional[int]
    method: InstallMethod
    pm_select_mode: Optional[PmSelectMode] = "auto"

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
            values["end_time"] = datetime.now(pytz.timezone('Asia/Shanghai')) + \
                timedelta(days=Config.VM_DEFAULT_DAYS)           
        
        max_time = datetime.now(pytz.timezone('Asia/Shanghai')) + timedelta(
            days=current_app.config.get("VM_MAX_DAYS")
        )
        
        if max_time < values.get("end_time"):
            raise ValueError(
                "max lifetime of virtual machine(days):%s"
                % current_app.config.get("VM_MAX_DAYS")
            )

        return values

    @root_validator
    def check_pmselect(cls, values):
        if values.get("pm_select_mode") == "assign":
            if not values.get("pmachine_id"):
                raise ValueError(
                    "Must select a physical machine as the host, when select mode is assign."
                )
        elif values.get("pm_select_mode") == "auto":
            if not values.get("machine_group_id"):
                raise ValueError(
                    "Must select a machine group to automatically choose a host, when select mode is auto."
                )

        return values


class VmachineBatchCreateSchema(VmachineCreateSchema):
    count: conint(ge=1, le=Config.VM_MAX_COUNT)


class VmachineItemUpdateSchema(BaseModel):
    memory: Optional[conint(ge=2048, le=Config.VM_MAX_MEMEORY)]
    sockets: Optional[conint(ge=1, le=Config.VM_MAX_SOCKET)]
    cores: Optional[conint(ge=1, le=Config.VM_MAX_CORE)]
    threads: Optional[conint(ge=1, le=Config.VM_MAX_THREAD)]


class VmachineDataUpdateSchema(VmachineItemUpdateSchema):
    name: Optional[str]
    frame: Optional[Frame]
    mac: Optional[str]
    ip: Optional[str]
    password: Optional[str]
    user: Optional[str]
    vnc_port: Optional[int]
    status: Optional[str]
    vnc_token: Optional[str]
    pmachine_id: Optional[str]
    special_device: Optional[str]


class VmachineConfigUpdateSchema(BaseModel):
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
        except (IntegrityError, SQLAlchemyError) as e:
            raise ValueError("Must select an existing virtual machine.") from e

        max_time = create_time + timedelta(
            days=current_app.config.get("VM_MAX_DAYS")
        ).strftime("%Y-%m-%d")
        if max_time < v:
            raise ValueError(
                "The lifetime of virtual machine(days):%s"
                % current_app.config.get("VM_MAX_DAYS")
            )
        return v


class VmachineDelaySchema(BaseModel):
    end_time: Optional[datetime]

    @validator("end_time")
    def check_end_time(cls, v, values):
        if not v or v.astimezone(pytz.timezone('Asia/Shanghai')) \
            < (datetime.now(pytz.timezone('Asia/Shanghai'))):
            raise ValueError(
                "Empty time and Past time cannot be modified."
            )

        dl = (v.astimezone(pytz.timezone('Asia/Shanghai')) -
                datetime.now(pytz.timezone('Asia/Shanghai'))
            ).days
        if dl > current_app.config.get("VM_MAX_DAYS"):
            raise ValueError(
                "The lifetime of virtual machine(days):%s"
                % current_app.config.get("VM_MAX_DAYS")
            )

        return v


class VmachineIpaddrSchema(BaseModel):
    ip: str

    @validator("ip")
    def check_ip_format(cls, v):
        if not ip_type(v):
            raise ValueError("The ip of vmachine is invaild.")
        return v


class PowerSchema(UpdateBaseModel):
    status: VMStatus


class VnicBaseSchema(BaseModel):
    mode: Optional[NetMode] = "bridge"
    bus: Optional[NetBus] = "virtio"
    mac: Optional[constr(max_length=48)]
    source: Optional[str]


class VnicCreateSchema(VnicBaseSchema):
    vmachine_id: int


class VdiskBaseSchema(BaseModel):
    vmachine_id: int
    bus: Optional[DiskBus] = "virtio"
    capacity: Optional[conint(ge=1, le=Config.VM_MAX_CAPACITY)] = 1
    cache: Optional[DiskCache] = "default"
    volume: Optional[str]


class VdiskCreateSchema(VdiskBaseSchema):
    @root_validator
    def check_volume(cls, values):
        if not values.get("volume"):
            vmachine = Vmachine.query.filter_by(
                id=values.get("vmachine_id")
            ).first()
            disk = Vdisk.query.filter_by(vmachine_id=vmachine.id).all()
            sign = len(disk) + 1
            while [True]:
                values["volume"] = "{}-{}".format(vmachine.name, sign)
                if not Precise(Vdisk, {"volume": values["volume"]}).first():
                    break
                sign += 1
        
        return values


class VdiskUpdateSchema(BaseModel):
    bus: Optional[DiskBus]
    capacity: Optional[conint(ge=1, le=Config.VM_MAX_CAPACITY)]
    cache: Optional[DiskCache]
    volume: Optional[str]


class DeviceDeleteSchema(BaseModel):
    id: int


class DeviceBaseSchema(BaseModel):
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


class VmachineBriefSchema(BaseModel):
    ip: Optional[str]
    description: str
    milestone: str
    status: str
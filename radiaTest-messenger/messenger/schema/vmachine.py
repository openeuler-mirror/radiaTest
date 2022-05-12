from datetime import datetime, timedelta
from typing import List, Optional

from flask import current_app
from pydantic import BaseModel, conint, constr, root_validator, validator

from messenger.schema import (
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
    PermissionType,
)
from messenger.config.settings import Config


class AuthBaseModel(BaseModel):
    user_id: Optional[int]


class VmachineItemSchema(AuthBaseModel):
    vmachine: dict
    pmachine: dict

class PermissionBase(BaseModel):
    creator_id: int
    permission_type: PermissionType
    group_id: Optional[int] = None
    org_id: int

class VmachineCreateSchema(PermissionBase):
    frame: Frame
    description: constr(min_length=10, max_length=255)
    milestone_id: int
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
    password: Optional[str]
    machine_group_id: Optional[int]
    pmachine_id: Optional[int]
    method: InstallMethod = "import"
    pm_select_mode: PmSelectMode = "auto"


class VmachineBaseSchema(AuthBaseModel, PermissionBase):
    method: InstallMethod
    frame: Frame
    description: constr(min_length=10, max_length=255)
    name: constr(min_length=10, max_length=255)
    memory: conint(ge=2048, le=Config.VM_MAX_MEMEORY)
    sockets: conint(ge=1, le=Config.VM_MAX_SOCKET)
    cores: conint(ge=1, le=Config.VM_MAX_CORE)
    threads: conint(ge=1, le=Config.VM_MAX_THREAD)
    cpu_mode: CPUMode
    net_bus: NetBus
    net_mode: NetMode
    disk_bus: DiskBus
    capacity: Optional[conint(ge=10, le=Config.VM_MAX_CAPACITY)]
    disk_cache: DiskCache
    video_bus: VideoBus
    end_time: str
    machine_group_id: Optional[int]
    # password: Optional[str]

    product: dict
    milestone: dict
    update_milestone: Optional[dict]

    pmachine: Optional[dict]
    pm_select_mode: PmSelectMode

    @validator("end_time")
    def check_end_time(cls, v):
        try:
            v = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except:
            v = datetime.strptime(v, "%Y-%m-%d")
        
        return v


class VmachineUpdateSchema(AuthBaseModel):
    memory: Optional[conint(ge=2048, le=Config.VM_MAX_MEMEORY)] = 2048
    sockets: Optional[conint(ge=1, le=Config.VM_MAX_SOCKET)] = 1
    cores: Optional[conint(ge=1, le=Config.VM_MAX_CORE)] = 1
    threads: Optional[conint(ge=1, le=Config.VM_MAX_THREAD)] = 1

    pmachine: dict


class PowerSchema(AuthBaseModel):
    status: VMStatus
    pmachine: dict


class VnicBaseSchema(VmachineItemSchema):
    mode: Optional[NetMode] = "bridge"
    bus: Optional[NetBus] = "virtio"
    mac: Optional[constr(max_length=48)]


class VnicCreateSchema(VnicBaseSchema):
    vmachine_id: int


class VdiskBaseSchema(VmachineItemSchema):
    bus: Optional[DiskBus] = "virtio"
    capacity: Optional[conint(ge=1, le=Config.VM_MAX_CAPACITY)] = 1
    cache: Optional[DiskCache] = "default"
    volume: Optional[str]


class VdiskCreateSchema(VdiskBaseSchema):
    vmachine_id: int


class DeviceDeleteSchema(VmachineItemSchema):
    device: dict


class DeviceBaseSchema(VmachineItemSchema):
    device: List[dict]

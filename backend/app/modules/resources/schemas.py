# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

# 资源 Pydantic 模型：创建/更新/读取/导入导出参数与结果。

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.resources.models import (
    ConnectivityStatus,
    ManagementStatus,
    OccupancyStatus,
    ResourceType,
)
from app.modules.users.models import UserRole


class ResourceBase(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    management_status: ManagementStatus = ManagementStatus.ACTIVE
    connectivity_status: ConnectivityStatus = ConnectivityStatus.UNKNOWN
    is_critical: bool = False
    primary_ip: str | None = Field(default=None, min_length=1, max_length=64)
    mac_address: str | None = None
    arch: str | None = None
    os_version: str | None = None
    kernel_version: str | None = None
    ssh_username: str = Field(min_length=1, max_length=64)
    ssh_password: str | None = Field(default=None, min_length=1, max_length=512)
    tags: list[str] = Field(default_factory=list)
    usage_scenario: str | None = None
    extra: dict[str, object] = Field(default_factory=dict)

    device_location: str | None = None
    device_distribution: str | None = None
    bmc_ip: str | None = None
    bmc_username: str | None = None
    bmc_password: str | None = None
    cpu_model: str | None = None
    cpu_count: int | None = Field(default=None, ge=0)
    memory_count: int | None = Field(default=None, ge=0)
    memory_spec: str | None = None
    hdd_count: int | None = Field(default=None, ge=0)
    hdd_spec: str | None = None
    ssd_count: int | None = Field(default=None, ge=0)
    ssd_spec: str | None = None
    ssd_card_count: int | None = Field(default=None, ge=0)
    ssd_card_spec: str | None = None
    board_sn: str | None = None

    vm_name: str | None = None
    vnc_port: int | None = Field(default=None, ge=0)
    vnc_websocket_port: int | None = Field(default=None, ge=0)
    vcpu_count: int | None = Field(default=None, ge=0)
    memory_mb: int | None = Field(default=None, ge=0)
    disk_gb: int | None = Field(default=None, ge=0)
    host_resource_id: str | None = None
    system_disk_path: str | None = None
    data_disk_count: int | None = Field(default=None, ge=0)
    data_disk_size_gb: int | None = Field(default=None, ge=0)
    data_disk_paths: list[str] = Field(default_factory=list)


class ResourceCreate(ResourceBase):
    resource_code: str = Field(min_length=1, max_length=128)
    resource_type: ResourceType = ResourceType.PHYSICAL

    @model_validator(mode="after")
    def validate_type_credentials(self) -> "ResourceCreate":
        if self.resource_type == ResourceType.PHYSICAL:
            if not self.primary_ip:
                raise ValueError("physical resources require primary_ip")
            if not self.ssh_password:
                raise ValueError("physical resources require ssh_password")
            missing_bmc = not self.bmc_ip or not self.bmc_username or not self.bmc_password
            if missing_bmc:
                raise ValueError("physical resources require bmc_ip, bmc_username and bmc_password")
        return self


class ResourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    management_status: ManagementStatus | None = None
    connectivity_status: ConnectivityStatus | None = None
    is_critical: bool | None = None
    primary_ip: str | None = Field(default=None, min_length=1, max_length=64)
    mac_address: str | None = None
    arch: str | None = None
    os_version: str | None = None
    kernel_version: str | None = None
    ssh_username: str | None = Field(default=None, min_length=1, max_length=64)
    ssh_password: str | None = Field(default=None, min_length=1, max_length=512)
    tags: list[str] | None = None
    usage_scenario: str | None = None
    extra: dict[str, object] | None = None

    device_location: str | None = None
    device_distribution: str | None = None
    bmc_ip: str | None = None
    bmc_username: str | None = None
    bmc_password: str | None = None
    cpu_model: str | None = None
    cpu_count: int | None = Field(default=None, ge=0)
    memory_count: int | None = Field(default=None, ge=0)
    memory_spec: str | None = None
    hdd_count: int | None = Field(default=None, ge=0)
    hdd_spec: str | None = None
    ssd_count: int | None = Field(default=None, ge=0)
    ssd_spec: str | None = None
    ssd_card_count: int | None = Field(default=None, ge=0)
    ssd_card_spec: str | None = None
    board_sn: str | None = None

    vm_name: str | None = None
    vnc_port: int | None = Field(default=None, ge=0)
    vnc_websocket_port: int | None = Field(default=None, ge=0)
    vcpu_count: int | None = Field(default=None, ge=0)
    memory_mb: int | None = Field(default=None, ge=0)
    disk_gb: int | None = Field(default=None, ge=0)
    host_resource_id: str | None = None
    system_disk_path: str | None = None
    data_disk_count: int | None = Field(default=None, ge=0)
    data_disk_size_gb: int | None = Field(default=None, ge=0)
    data_disk_paths: list[str] | None = None


class ResourceRead(BaseModel):
    id: str
    resource_code: str
    resource_type: ResourceType
    name: str | None
    management_status: ManagementStatus
    connectivity_status: ConnectivityStatus
    occupancy_status: OccupancyStatus
    test_status: Literal["idle", "testing"]
    current_test_job_id: int | None
    current_lease_id: str | None
    current_lease_user_id: str | None
    current_lease_username: str | None
    current_lease_user_role: UserRole | None
    current_lease_purpose: str | None
    current_lease_expected_ends_at: datetime | None
    is_critical: bool
    primary_ip: str | None
    mac_address: str | None
    arch: str | None
    os_version: str | None
    kernel_version: str | None
    ssh_username: str
    has_ssh_password: bool
    tags: list[str]
    usage_scenario: str | None
    extra: dict[str, object]

    device_location: str | None
    device_distribution: str | None
    bmc_ip: str | None
    bmc_username: str | None
    has_bmc_password: bool
    cpu_model: str | None
    cpu_count: int | None
    memory_count: int | None
    memory_spec: str | None
    hdd_count: int | None
    hdd_spec: str | None
    ssd_count: int | None
    ssd_spec: str | None
    ssd_card_count: int | None
    ssd_card_spec: str | None
    board_sn: str | None

    vm_name: str | None
    vnc_port: int | None
    vnc_websocket_port: int | None
    vcpu_count: int | None
    memory_mb: int | None
    disk_gb: int | None
    host_resource_id: str | None
    host_primary_ip: str | None
    system_disk_path: str | None
    data_disk_count: int | None
    data_disk_size_gb: int | None
    data_disk_paths: list[str]

    model_config = ConfigDict(from_attributes=True)


class ResourceListParams(BaseModel):
    match: Literal["and", "or"] = "and"
    resource_code: str | None = None
    resource_type: str | None = None
    name: str | None = None
    management_status: str | None = None
    occupancy_status: str | None = None
    primary_ip: str | None = None
    mac_address: str | None = None
    arch: str | None = None
    os_version: str | None = None
    kernel_version: str | None = None
    usage_scenario: str | None = None
    current_lease_username: str | None = None
    current_lease_purpose: str | None = None
    bmc_ip: str | None = None
    cpu_model: str | None = None


class ResourceImportRequest(BaseModel):
    filename: str | None = None
    content: str = Field(min_length=1)
    dry_run: bool = False


class ResourceImportRowResult(BaseModel):
    row_number: int
    resource_code: str | None = None
    primary_ip: str | None = None
    status: Literal["created", "error", "validated"]
    errors: list[str] = Field(default_factory=list)


class ResourceImportResult(BaseModel):
    dry_run: bool
    total_rows: int
    success_count: int
    error_count: int
    rows: list[ResourceImportRowResult]

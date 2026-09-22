# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Literal

from pydantic import BaseModel, Field

# VM 宿主脚本(create-vm.sh / destroy-vm.sh / power-vm.sh / pxe-install.sh)的
# 请求/响应契约。host_runner 把 payload base64 编码经 SSH 喂给脚本，脚本
# stdout 输出 JSON，由这些模型校验。字段即宿主脚本的输入输出约定。


class VMHostCreatePayload(BaseModel):
    """create-vm.sh 输入：VM 规格 + 镜像缓存名 + 宿主网络配置。"""

    vm_uuid: str
    vm_name: str
    install_type: Literal["auto", "manual"]
    image_url: str
    cache_filename: str
    arch: str
    system_disk_size_gb: int
    vcpu_count: int
    memory_mb: int
    data_disk_count: int
    data_disk_size_gb: int
    extra_nic_num: int = 0
    dhcp_leases_url: str
    network_bridge: str
    host_resource_id: str


class VMHostCreateResult(BaseModel):
    """create-vm.sh 输出：VM 实际 IP/MAC/VNC 端口 + 磁盘路径，用于建资源记录。"""

    status: Literal["success"]
    vm_uuid: str
    vm_name: str
    primary_ip: str | None = None
    mac_address: str | None = None
    vnc_port: int
    vnc_websocket_port: int
    disk_gb: int
    system_disk_path: str
    data_disk_paths: list[str] = Field(default_factory=list)


class VMHostDestroyPayload(BaseModel):
    """destroy-vm.sh 输入：按 vm_name + 磁盘路径清理 libvirt 域与磁盘文件。"""

    vm_name: str
    system_disk_path: str | None = None
    data_disk_paths: list[str] = Field(default_factory=list)


class VMHostDestroyResult(BaseModel):
    status: Literal["success"]


class VMHostInspectPayload(BaseModel):
    """inspect-vm.sh 输入：按 vm_name + 磁盘路径回读宿主实际状态(只读)。"""

    vm_name: str
    system_disk_path: str | None = None
    data_disk_paths: list[str] = Field(default_factory=list)


class VMHostInspectResult(BaseModel):
    """inspect-vm.sh 输出：宿主事实快照，供销毁对账与创建登记确认使用。"""

    status: Literal["success"]
    domain_exists: bool
    power_state: str | None = None
    system_disk_exists: bool = False
    data_disks_existing: list[str] = Field(default_factory=list)


class VMHostPowerPayload(BaseModel):
    vm_name: str
    action: Literal["state", "start", "shutdown", "reboot"]


class VMHostPowerResult(BaseModel):
    status: Literal["success"]
    power_state: str


class PXEInstallPayload(BaseModel):
    target_mac: str
    target_ip: str
    efi_url: str | None = None
    repo_url: str | None = None
    iso_url: str | None = None
    round: str | None = None
    kernel_variant: str | None = None
    arch: str = ""
    tftp_root: str = "/var/lib/tftpboot"
    httpd_root: str = "/var/www/html"
    httpd_prefix: str = "http://172.168.131.94:9400"
    os_name: str = "openEuler"
    nics: list[str] = Field(default_factory=list)


class PXEInstallResult(BaseModel):
    status: Literal["ok"]
    efi_relative_path: str

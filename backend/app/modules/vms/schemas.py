# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator

from app.modules.vms.models import VMInstallType, VMRequestStatus

# VM 模块 API schema：申请/批量申请/释放/电源/控制台/镜像/ISO 的请求与响应模型。
# 请求模型的 normalize_text 校验器统一 strip 文本，并按 install_type 强制
# image_url 的有无(AUTO 忽略，MANUAL 必须是 HTTP/HTTPS)，是入参的安全边界。


class VMImageRead(BaseModel):
    dist: str
    os_version: str
    image_round: str
    arch: str
    url: str


class VMISORead(BaseModel):
    url: str
    sha256: str
    size_bytes: int



class KernelVariantRead(BaseModel):
    variant: str
    kernel_version_prefix: str


class VMRequestCreate(BaseModel):
    install_type: VMInstallType = VMInstallType.AUTO
    dist: str = Field(default="openEuler", min_length=1, max_length=64)
    os_version: str = Field(min_length=1, max_length=128)
    image_round: str = Field(default="", max_length=64)
    arch: str = Field(min_length=1, max_length=32)
    image_url: str | None = Field(default=None, max_length=2048)
    kernel_version: str | None = Field(default=None, max_length=128)
    kernel_variant: str | None = Field(default=None, max_length=128)
    kernel_rpm_url: str | None = Field(default=None, max_length=2048)
    vcpu_count: int = Field(default=2, ge=1, le=16)
    memory_mb: int = Field(default=4096, ge=512, le=32 * 1024)
    data_disk_count: int = Field(default=0, ge=0, le=4)
    extra_nic_num: int = Field(default=0, ge=0, le=4)
    purpose: str = Field(min_length=1, max_length=512)
    expected_ends_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_text(self) -> "VMRequestCreate":
        """strip 文本字段并按安装方式校验 image_url。

        AUTO 安装忽略 image_url(用镜像仓库)；MANUAL 必须提供 HTTP/HTTPS
        的 image_url。防止 AUTO 申请携带无关 URL 或 MANUAL 缺 URL。
        kernel_rpm_url 必须是 None 或 HTTP/HTTPS 且以 .rpm 结尾。
        """
        self.dist = self.dist.strip()
        self.os_version = self.os_version.strip()
        self.image_round = self.image_round.strip()
        self.arch = self.arch.strip()
        if self.image_url is not None:
            self.image_url = self.image_url.strip() or None
        if self.kernel_version is not None:
            self.kernel_version = self.kernel_version.strip() or None
        if self.kernel_variant is not None:
            self.kernel_variant = self.kernel_variant.strip() or None
        if self.kernel_rpm_url is not None:
            self.kernel_rpm_url = self.kernel_rpm_url.strip() or None
            parsed = urlparse(self.kernel_rpm_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("kernel_rpm_url must be an HTTP/HTTPS URL")
            if not self.kernel_rpm_url.lower().endswith(".rpm"):
                raise ValueError("kernel_rpm_url must end with .rpm")
        self.purpose = self.purpose.strip()

        if self.install_type == VMInstallType.AUTO:
            self.image_url = None
            return self

        if not self.image_url:
            raise ValueError("image_url is required for manual VM install")
        parsed = urlparse(self.image_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("manual image_url must be an HTTP/HTTPS URL")
        return self


class VMRequestRead(BaseModel):
    id: str
    requester_user_id: str
    requester_username: str | None
    status: VMRequestStatus
    purpose: str
    expected_ends_at: datetime | None
    dist: str
    os_version: str
    image_round: str
    arch: str
    kernel_version: str | None
    kernel_variant: str | None
    kernel_rpm_url: str | None
    install_type: VMInstallType
    image_url: str
    vcpu_count: int
    memory_mb: int
    data_disk_count: int
    data_disk_size_gb: int
    extra_nic_num: int
    resource_id: str | None
    host_resource_id: str | None
    error_code: str | None
    error_message: str | None
    host_attempts: list[dict[str, object]]
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None


class VMSpec(BaseModel):
    """批量请求中的单个架构规格。"""
    arch: str = Field(min_length=1, max_length=32)
    count: int = Field(default=1, ge=1, le=20)


class VMBatchCreate(BaseModel):
    """批量创建 VM：一次请求创建多种架构的 VM。"""
    specs: list[VMSpec] = Field(min_length=1, max_length=10)
    install_type: VMInstallType = VMInstallType.AUTO
    dist: str = Field(default="openEuler", min_length=1, max_length=64)
    os_version: str = Field(min_length=1, max_length=128)
    image_round: str = Field(default="", max_length=64)
    image_url: str | None = Field(default=None, max_length=2048)
    kernel_version: str | None = Field(default=None, max_length=128)
    vcpu_count: int = Field(default=2, ge=1, le=16)
    memory_mb: int = Field(default=4096, ge=512, le=32 * 1024)
    data_disk_count: int = Field(default=0, ge=0, le=4)
    extra_nic_num: int = Field(default=0, ge=0, le=4)
    purpose: str = Field(min_length=1, max_length=512)
    expected_ends_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_text(self) -> "VMBatchCreate":
        self.dist = self.dist.strip()
        self.os_version = self.os_version.strip()
        self.image_round = self.image_round.strip()
        if self.image_url is not None:
            self.image_url = self.image_url.strip() or None
        if self.kernel_version is not None:
            self.kernel_version = self.kernel_version.strip() or None
        self.purpose = self.purpose.strip()
        for spec in self.specs:
            spec.arch = spec.arch.strip()

        if self.install_type == VMInstallType.AUTO:
            self.image_url = None
            return self

        if not self.image_url:
            raise ValueError("image_url is required for manual VM install")
        parsed = urlparse(self.image_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("manual image_url must be an HTTP/HTTPS URL")
        return self


class VMReleaseRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def normalize_reason(self) -> "VMReleaseRequest":
        if self.reason is not None:
            self.reason = self.reason.strip() or None
        return self


class VMReleaseRead(BaseModel):
    resource_id: str
    status: Literal["queued"]


class VMReleaseBatchRequest(BaseModel):
    resource_ids: list[str]
    reason: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def normalize_reason(self) -> "VMReleaseBatchRequest":
        if self.reason is not None:
            self.reason = self.reason.strip() or None
        return self


class VMPowerRequest(BaseModel):
    action: Literal["start", "shutdown", "reboot"]


class VMPowerRead(BaseModel):
    resource_id: str
    vm_name: str | None
    power_state: str


class VMConsoleRead(BaseModel):
    resource_id: str
    vm_name: str | None
    url: str
    port: int | None
    websocket_port: int
    password: str | None = None

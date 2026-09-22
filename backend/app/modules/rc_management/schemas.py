# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.rc_management.models import CompareKind, CompareStatus, VersionStatus


class VersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    version_type: str | None = Field(default=None, max_length=16)
    # 创建时自动生成 round1..roundN 里程碑骨架（build_url 后续在里程碑上登记）
    rc_round_count: int = Field(default=0, ge=0, le=24)
    status: VersionStatus = VersionStatus.TESTING
    start_time: datetime | None = None
    end_time: datetime | None = None
    remark: str | None = None


class VersionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    version_type: str | None = Field(default=None, max_length=16)
    status: VersionStatus | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    remark: str | None = None


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version_type: str | None
    status: str
    start_time: datetime | None
    end_time: datetime | None
    remark: str | None
    created_by: str
    created_at: datetime
    milestone_count: int = 0


class MilestoneCreate(BaseModel):
    version_id: str
    name: str = Field(min_length=1, max_length=64)
    kernel_variant: str | None = Field(default=None, max_length=64)
    build_url: str | None = Field(default=None, max_length=1024)
    compare_base_milestone_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    kernel_variant: str | None = Field(default=None, max_length=64)
    build_url: str | None = Field(default=None, min_length=1, max_length=1024)
    compare_base_milestone_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_id: str
    name: str
    kernel_variant: str | None
    build_url: str | None
    pxe_round_label: str | None
    compare_base_milestone_id: str | None
    compare_base_name: str | None
    start_time: datetime | None
    end_time: datetime | None
    created_by: str
    created_at: datetime
    has_pxe_source: bool
    latest_compare: dict[str, object] | None


class CompareTrigger(BaseModel):
    base_milestone_id: str


class CompareRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    milestone_id: str
    base_milestone_id: str
    status: CompareStatus
    total_changed: int | None
    summary: dict[str, object] | None
    error_msg: str | None
    triggered_by: str
    triggered_at: datetime
    completed_at: datetime | None
    created_at: datetime


class PackageCompareResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: CompareKind
    repo_path: str
    pkg_name: str
    arch: str | None
    status: str
    rpm_base: str | None
    rpm_target: str | None

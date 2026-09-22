# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.test_management.models import (
    TestCaseRunStatus,
    TestEnvNodeStatus,
    TestEnvSetStatus,
    TestEnvType,
    TestFramework,
    TestJobStatus,
)


class MugenCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suite_name: str
    case_name: str
    env_type: TestEnvType
    node_num: int
    add_disk_num: int
    add_nic_num: int
    commit_sha: str
    synced_at: datetime


class MugenCaseSyncRequest(BaseModel):
    commit_sha: str = Field(min_length=1, max_length=64)
    suites: dict[str, object]


class MugenCaseSyncRead(BaseModel):
    commit_sha: str
    case_count: int


class MugenCaseSyncTaskRead(BaseModel):
    task_id: str
    status: str


class TestCaseSelection(BaseModel):
    suite_name: str = Field(min_length=1, max_length=255)
    case_names: list[str] | None = None

    @model_validator(mode="after")
    def normalize(self) -> TestCaseSelection:
        self.suite_name = self.suite_name.strip()
        if self.case_names is not None:
            self.case_names = [case.strip() for case in self.case_names if case.strip()]
            if not self.case_names:
                raise ValueError("case_names must not be empty")
        return self


class TestJobConfig(BaseModel):
    framework: TestFramework = TestFramework.MUGEN
    env_type: TestEnvType = TestEnvType.VM
    dist: str = Field(default="openEuler", min_length=1, max_length=64)
    os_version: str = Field(min_length=1, max_length=128)
    image_round: str = Field(min_length=1, max_length=64)
    arch: str = Field(min_length=1, max_length=32)
    env_set_num: int = Field(default=1, ge=1, le=20)
    keep_failed_env: bool = False
    pre_env_script: str | None = Field(default=None, max_length=20000)
    post_env_script: str | None = Field(default=None, max_length=20000)
    cases: list[TestCaseSelection] = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_text(self) -> TestJobConfig:
        self.dist = self.dist.strip()
        self.os_version = self.os_version.strip()
        self.image_round = self.image_round.strip()
        self.arch = self.arch.strip()
        if self.pre_env_script is not None:
            self.pre_env_script = self.pre_env_script.strip() or None
        if self.post_env_script is not None:
            self.post_env_script = self.post_env_script.strip() or None
        return self


class TestJobCreate(TestJobConfig):
    name: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def normalize_name(self) -> TestJobCreate:
        self.name = self.name.strip()
        return self


class TestJobTemplateCreate(TestJobConfig):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


class TestJobTemplateUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    framework: TestFramework | None = None
    env_type: TestEnvType | None = None
    dist: str | None = Field(default=None, min_length=1, max_length=64)
    os_version: str | None = Field(default=None, min_length=1, max_length=128)
    image_round: str | None = Field(default=None, min_length=1, max_length=64)
    arch: str | None = Field(default=None, min_length=1, max_length=32)
    env_set_num: int | None = Field(default=None, ge=1, le=20)
    keep_failed_env: bool | None = None
    pre_env_script: str | None = Field(default=None, max_length=20000)
    post_env_script: str | None = Field(default=None, max_length=20000)
    cases: list[TestCaseSelection] | None = Field(default=None, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        nullable = {"pre_env_script", "post_env_script"}
        null_fields = [key for key, item in value.items() if item is None and key not in nullable]
        if null_fields:
            raise ValueError(f"Fields must not be null: {', '.join(sorted(null_fields))}")
        return value

    @model_validator(mode="after")
    def normalize_text(self) -> TestJobTemplateUpdate:
        for field in ("dist", "os_version", "image_round", "arch"):
            value = getattr(self, field)
            if value is not None:
                setattr(self, field, value.strip())
        if self.pre_env_script is not None:
            self.pre_env_script = self.pre_env_script.strip() or None
        if self.post_env_script is not None:
            self.post_env_script = self.post_env_script.strip() or None
        return self


class TestEnvNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    node_index: int
    role: str
    status: TestEnvNodeStatus
    vm_request_id: str | None
    resource_id: str | None
    primary_ip: str | None
    created_at: datetime
    updated_at: datetime


class TestCaseRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    env_set_id: str
    suite_name: str
    case_name: str
    status: TestCaseRunStatus
    exit_code: int | None
    stdout_summary: str | None
    stderr_summary: str | None
    rerun_source_case_run_id: str | None
    rerun_root_case_run_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TestEnvSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    set_index: int
    status: TestEnvSetStatus
    node_num: int
    add_disk_num: int
    add_nic_num: int
    nodes: list[TestEnvNodeRead] = []
    case_runs: list[TestCaseRunRead] = []
    created_at: datetime
    updated_at: datetime


class PipelineOriginRead(BaseModel):
    """任务来源流水线信息：由 pipeline_run_jobs 反查得到，普通任务为 null。"""

    run_job_id: str
    config_name: str
    version: str
    module_name: str
    arch: str


class TestJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_user_id: str
    creator_username: str | None
    name: str
    status: TestJobStatus
    framework: TestFramework
    env_type: TestEnvType
    dist: str
    os_version: str
    image_round: str
    arch: str
    mugen_commit_sha: str
    env_set_num: int
    keep_failed_env: bool
    pre_env_script: str | None
    post_env_script: str | None
    task_id: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    pipeline_origin: PipelineOriginRead | None = None
    pipeline_origin_deleted: bool = False


class TestJobBatchDeleteRequest(BaseModel):
    ids: list[int] = Field(min_length=1)


class TestJobBatchDeleteResult(BaseModel):
    id: int
    success: bool
    detail: str | None = None


class TestJobBatchDeleteResponse(BaseModel):
    results: list[TestJobBatchDeleteResult]


class TestJobDetailRead(TestJobRead):
    env_sets: list[TestEnvSetRead]
    case_runs: list[TestCaseRunRead]


class TestJobTemplateRead(BaseModel):
    id: int
    creator_user_id: str
    creator_username: str | None
    name: str
    framework: TestFramework
    env_type: TestEnvType
    dist: str
    os_version: str
    image_round: str
    arch: str
    env_set_num: int
    keep_failed_env: bool
    pre_env_script: str | None
    post_env_script: str | None
    cases: list[TestCaseSelection]
    suite_count: int
    case_count: int
    is_available: bool
    unavailable_reason: str | None
    can_manage: bool
    created_at: datetime
    updated_at: datetime

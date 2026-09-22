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

from pydantic import BaseModel, ConfigDict, Field


class TestModuleTemplateRead(BaseModel):
    id: str
    name: str
    display_name: str
    suite_name: str
    pipeline_type: str
    env_set_num: int
    node_num: int
    case_filter: str
    env_type: str
    skip_packages: list[str]
    pre_env_script: str
    rerun_env_script: str
    post_env_script: str
    result_parser: str
    test_framework: str
    mugen_exec_command: str | None = None


class TestModuleTemplateUpdate(BaseModel):
    display_name: str | None = None
    suite_name: str | None = None
    pipeline_type: str | None = None
    env_set_num: int | None = None
    node_num: int | None = None
    case_filter: str | None = None
    env_type: str | None = None
    skip_packages: list[str] | None = None
    pre_env_script: str | None = None
    rerun_env_script: str | None = None
    post_env_script: str | None = None
    result_parser: str | None = None
    mugen_exec_command: str | None = None


class TestModuleTemplateCreate(BaseModel):
    name: str
    display_name: str
    suite_name: str
    pipeline_type: str = "update"
    env_set_num: int = 1
    node_num: int = 1
    case_filter: str = "none"
    env_type: str = "vm"
    skip_packages: list[str] = []
    pre_env_script: str = ""
    rerun_env_script: str = ""
    post_env_script: str = ""
    result_parser: str = "none"
    test_framework: str = "mugen"
    mugen_exec_command: str | None = None


class PipelineTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    strategy_kind: str = Field(default="direct_run", max_length=64)
    test_framework: str = Field(default="mugen", max_length=64)
    default_config: dict[str, object] = {}


class PipelineTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    strategy_kind: str
    test_framework: str
    is_system: bool
    default_config: dict[str, object]


class FrameworkRead(BaseModel):
    name: str
    display_name: str


class PipelineConfigCreate(BaseModel):
    name: str
    pipeline_type: str = "update"
    versions: list[str]
    archs: list[str]
    dist: str = "openEuler"
    image_round: str = ""
    test_framework: str = "mugen"
    config_data: dict[str, object] = {}


class LatestExecutionRead(BaseModel):
    """该 config 最近一次 execution 的摘要（配置列表"最近执行结果"列用）。"""

    id: str
    status: str
    triggered_at: datetime | None = None


class PipelineConfigRead(BaseModel):
    id: str
    name: str
    pipeline_type: str
    versions: list[str]
    archs: list[str]
    dist: str
    image_round: str
    test_framework: str
    config_data: dict[str, object]
    latest_execution: LatestExecutionRead | None = None


class PipelineConfigUpdate(BaseModel):
    name: str | None = None
    pipeline_type: str | None = None
    versions: list[str] | None = None
    archs: list[str] | None = None
    dist: str | None = None
    image_round: str | None = None
    test_framework: str | None = None
    config_data: dict[str, object] | None = None


class PipelineTriggerRequest(BaseModel):
    config_id: str
    versions: list[str] | None = None
    archs: list[str] | None = None
    # config.image_round 的 trigger 级覆盖。用于 release 类流水线——每次
    # trigger 对应一轮新 RC 构建。省略时 builder 回退到 config.image_round。
    image_round: str | None = None


class PipelineExecutionRead(BaseModel):
    id: str
    config_id: str
    config_name: str = ""
    triggered_by: str
    triggered_at: datetime | None = None
    completed_at: datetime | None = None
    status: str
    versions: list[str]
    archs: list[str]
    image_round: str | None = None


class PipelineRunRead(BaseModel):
    id: str
    config_id: str
    execution_id: str | None = None
    version: str
    status: str
    triggered_by: str
    triggered_at: datetime | None = None
    completed_at: datetime | None = None


class PipelineRunJobRead(BaseModel):
    id: str
    pipeline_run_id: str
    module_template_id: str
    arch: str
    env_type: str | None = None
    test_job_id: int | None = None
    rerun_source_run_job_id: str | None = None
    rerun_root_run_job_id: str | None = None
    status: str


class PipelineRunJobRerunRequest(BaseModel):
    case_run_ids: list[str] = Field(min_length=1)


class PipelineRunNodeInfoRead(BaseModel):
    id: str
    run_job_id: str
    resource_id: str | None = None
    resource_code: str | None = None
    primary_ip: str | None = None
    role: str | None = None
    env_set_index: int | None = None
    node_index: int | None = None
    status: str | None = None

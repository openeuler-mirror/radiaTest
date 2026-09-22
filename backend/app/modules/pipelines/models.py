# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class TestModuleTemplate(Base):
    __tablename__ = "test_module_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 与 framework 无关的 suite 标识。mugen framework 下为 mugen suite name。
    # 未来非 mugen framework 下由该 framework 的 executor 解释。
    suite_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # 指向 pipeline_types.name 的逻辑 FK。用于 UI 按类型分区展示。
    pipeline_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="update", index=True
    )
    env_set_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    node_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    case_filter: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    env_type: Mapped[str] = mapped_column(String(16), nullable=False, default="vm")
    skip_packages: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    pre_env_script: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rerun_env_script: Mapped[str] = mapped_column(Text, nullable=False, default="")
    post_env_script: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result_parser: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    test_framework: Mapped[str] = mapped_column(String(64), nullable=False, default="mugen")
    mugen_exec_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=utc_now,
        onupdate=utc_now,
    )


class PipelineType(Base):
    """注册的 pipeline type。通过 `strategy_kind` 分派决定 RunJob 形状。

    A-class(`strategy_kind=update_strategy`)type 的 strategy 在代码层
    `PIPELINE_STRATEGIES`，不可从前端删除(`is_system=True`)。
    B-class(`strategy_kind=direct_run`)type 共用 `DirectRunPipelineStrategy`，
    数据驱动；用户可从前端 CRUD。
    """

    __tablename__ = "pipeline_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_kind: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="direct_run"
    )
    test_framework: Mapped[str] = mapped_column(String(64), nullable=False, default="mugen")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_config: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, default=utc_now, onupdate=utc_now
    )


class PipelineConfig(Base):
    __tablename__ = "pipeline_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    pipeline_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="update", index=True
    )
    versions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    archs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dist: Mapped[str] = mapped_column(String(64), nullable=False, default="openEuler")
    image_round: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    test_framework: Mapped[str] = mapped_column(String(64), nullable=False, default="mugen")
    # 类型专属 config(update: module_template_ids + repo_base_url；release: suites 等)
    config_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PipelineExecution(Base):
    """一次 trigger 事件，可包含多个 version 的 run。"""

    __tablename__ = "pipeline_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    config_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    versions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    archs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # config.image_round 的 trigger 级覆盖。为 None 时 builder 回退到
    # config.image_round。用于 release 类流水线——每次 trigger 对应一轮新 RC 构建。
    image_round: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    config_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        ForeignKey("pipeline_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PipelineRunJob(Base):
    __tablename__ = "pipeline_run_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_template_id: Mapped[str] = mapped_column(
        ForeignKey("test_module_templates.id"),
        nullable=False,
        index=True,
    )
    arch: Mapped[str] = mapped_column(String(32), nullable=False)
    env_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    test_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rerun_source_run_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("pipeline_run_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rerun_root_run_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("pipeline_run_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rerun_case_selections: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PipelineRunNodeInfo(Base):
    """把 pipeline run job 映射到其执行机器，供 UI 展示。"""

    __tablename__ = "pipeline_run_node_infos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_job_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_run_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    resource_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    primary_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    env_set_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    node_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

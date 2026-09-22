# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from math import ceil
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TEMPLATE_CASES_TYPE = JSON().with_variant(JSONB(), "postgresql")

# 单个测试任务总执行上限：15 小时。超过即判 task_timeout 失败，避免长挂死占用 worker。
TEST_JOB_TIMEOUT = timedelta(hours=15)


class TestFramework(StrEnum):
    """支持的测试框架，目前仅 Mugen。"""

    MUGEN = "mugen"


class TestEnvType(StrEnum):
    """测试环境类型：虚拟机 / 物理机 / 未知。"""

    PHYSICAL = "physical"
    UNKNOWN = "unknown"
    VM = "vm"


class TestJobStatus(StrEnum):
    """测试任务状态机：pending→preparing→running→succeeded/failed/error/cancelled。"""

    PENDING = "pending"
    PREPARING = "preparing"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


class TestEnvSetStatus(StrEnum):
    """环境集状态机。

    not_executed 表示因前置跳过；error 表示环境问题(挂死/SSH)与 failed(用例失败)
    区分，决定是否保留环境供排查；destroying/destroyed 为清理阶段。
    """

    PENDING = "pending"
    CREATING_VMS = "creating_vms"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ERROR = "error"
    NOT_EXECUTED = "not_executed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class TestEnvNodeStatus(StrEnum):
    """环境节点状态机：pending→creating→ready/not_executed/error→destroyed。"""

    PENDING = "pending"
    CREATING = "creating"
    READY = "ready"
    NOT_EXECUTED = "not_executed"
    ERROR = "error"
    DESTROYED = "destroyed"


class TestCaseRunStatus(StrEnum):
    """单条用例运行结果：passed/failed/timeout/error/skipped/no_case/not_executed。

    no_case 表示 mugen 索引中找不到该用例；not_executed 表示因环境跳过未执行；
    error 表示执行链路异常(SSH/挂死)，与 failed(用例本身失败)严格区分。
    """

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"
    NO_CASE = "no_case"
    NOT_EXECUTED = "not_executed"


def utc_now() -> datetime:
    return datetime.now(UTC)


class MugenCase(Base):
    """Mugen 用例索引行，由 mugen 同步全量替换写入。

    不可破坏约束：(suite_name, case_name) 全局唯一，保证选择时不会拿到重复。
    commit_sha 标识该索引快照版本，正常状态下全表只有一个版本。
    """

    __tablename__ = "mugen_cases"
    __table_args__ = (
        UniqueConstraint("suite_name", "case_name", name="uq_mugen_cases_suite_case"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    suite_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    case_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    env_type: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=TestEnvType.VM.value,
    )
    node_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    add_disk_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    add_nic_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # 同步时脚本扫描出的危险标记(名字规则不落库,过滤时动态计算)。
    dangerous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dangerous_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TestJob(Base):
    """测试任务：一次跨多个环境集的 Mugen 执行单元。

    keep_failed_env 只保留失败环境；keep_env(流水线全保留)保留全部环境供人工排查。
    mugen_commit_sha 在创建时冻结，执行期始终用此版本，不随索引重新同步变化。
    """

    __tablename__ = "test_jobs"

    id: Mapped[int] = mapped_column(Integer, Identity(start=10000), primary_key=True)
    creator_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=TestJobStatus.PENDING.value,
    )
    framework: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=TestFramework.MUGEN.value,
    )
    env_type: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=TestEnvType.VM.value,
    )
    dist: Mapped[str] = mapped_column(String(64), nullable=False)
    os_version: Mapped[str] = mapped_column(String(128), nullable=False)
    image_round: Mapped[str] = mapped_column(String(64), nullable=False)
    arch: Mapped[str] = mapped_column(String(32), nullable=False)
    mugen_commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    env_set_num: Mapped[int] = mapped_column(Integer, nullable=False)
    keep_failed_env: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    keep_env: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pre_env_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    rerun_env_script: Mapped[str] = mapped_column(Text, nullable=False, default="")
    post_env_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    rerun_source_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_jobs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    task_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    physical_usage_scenario: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mugen_exec_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_parser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    update_packages: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # 类型专属执行参数（release 的 kernel_variant/kernel_rpm_url 等）；跨类型通用字段
    # 保留为实列，类型专属字段入此 JSONB，避免后续新流水线逐类型加列。
    pipeline_extras: Mapped[dict[str, object] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    env_sets: Mapped[list[TestEnvSet]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="TestEnvSet.set_index",
    )
    case_runs: Mapped[list[TestCaseRun]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class TestJobTemplate(Base):
    """测试任务模板：可复用的配置快照，名称大小写不敏感唯一。

    case_selections 用 JSONB(postgresql) 存储，供模板可用性校验时回放为
    TestCaseSelection 列表比对当前索引与镜像。
    """

    __tablename__ = "test_job_templates"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    creator_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    framework: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TestFramework.MUGEN.value,
    )
    env_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TestEnvType.VM.value,
    )
    dist: Mapped[str] = mapped_column(String(64), nullable=False)
    os_version: Mapped[str] = mapped_column(String(128), nullable=False)
    image_round: Mapped[str] = mapped_column(String(64), nullable=False)
    arch: Mapped[str] = mapped_column(String(32), nullable=False)
    env_set_num: Mapped[int] = mapped_column(Integer, nullable=False)
    keep_failed_env: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pre_env_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_env_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_selections: Mapped[list[dict[str, object]]] = mapped_column(
        TEMPLATE_CASES_TYPE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


Index("uq_test_job_templates_name_ci", func.lower(TestJobTemplate.name), unique=True)


def test_job_deadline(job: TestJob) -> datetime:
    """测试任务的硬截止时间 = created_at + 15h。created_at 缺时区时补 UTC。"""
    created_at = job.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return created_at + TEST_JOB_TIMEOUT


def remaining_test_job_seconds(job: TestJob, *, maximum: int) -> int:
    """剩余可用秒数，clamp 到 [0, maximum]，供各步骤派生子超时。"""
    remaining = ceil((test_job_deadline(job) - utc_now()).total_seconds())
    return max(0, min(maximum, remaining))


class TestEnvSet(Base):
    """环境集：一个测试任务下的一组节点+用例，可与其他环境集并行执行。

    不可破坏约束：(job_id, set_index) 唯一，保证同任务内环境集序号不重复。
    """

    __tablename__ = "test_env_sets"
    __table_args__ = (UniqueConstraint("job_id", "set_index", name="uq_test_env_sets_job_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[int] = mapped_column(
        ForeignKey("test_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=TestEnvSetStatus.PENDING.value,
    )
    node_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    env_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rerun_source_env_set_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_env_sets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    add_disk_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    add_nic_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    job: Mapped[TestJob] = relationship(back_populates="env_sets")
    nodes: Mapped[list[TestEnvNode]] = relationship(
        back_populates="env_set",
        cascade="all, delete-orphan",
        order_by="TestEnvNode.node_index",
    )
    case_runs: Mapped[list[TestCaseRun]] = relationship(back_populates="env_set")


class TestEnvNode(Base):
    """环境节点：control 或 peer，VM 场景关联一个 VM 资源，物理机场景关联物理资源。

    不可破坏约束：(env_set_id, node_index) 唯一。
    """

    __tablename__ = "test_env_nodes"
    __table_args__ = (
        UniqueConstraint("env_set_id", "node_index", name="uq_test_env_nodes_env_set_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    env_set_id: Mapped[str] = mapped_column(
        ForeignKey("test_env_sets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    node_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=TestEnvNodeStatus.PENDING.value,
    )
    vm_request_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    primary_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    env_set: Mapped[TestEnvSet] = relationship(back_populates="nodes")


class TestCaseRun(Base):
    """单条用例在一次环境集上的运行记录，结果与 stdout/stderr 摘要随执行写入。"""

    __tablename__ = "test_case_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[int] = mapped_column(
        ForeignKey("test_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    env_set_id: Mapped[str] = mapped_column(
        ForeignKey("test_env_sets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    suite_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    case_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=TestCaseRunStatus.PENDING.value,
    )
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rerun_source_case_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_case_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    rerun_root_case_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_case_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    job: Mapped[TestJob] = relationship(back_populates="case_runs")
    env_set: Mapped[TestEnvSet] = relationship(back_populates="case_runs")


class TestCaseRunDetail(Base):
    """子用例结果(ltp 子测试、pkgmanage 失败包名等)，挂在 case_run 下，best-effort 写入。"""

    __tablename__ = "test_case_run_details"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sub_test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TestLogArtifact(Base):
    """测试日志产物登记：TestJob 拥有，可选关联 pipeline_run_id 做存储分组。"""

    __tablename__ = "test_log_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pipeline_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    arch: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

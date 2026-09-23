# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Pipeline 配置/触发/执行读时聚合领域服务。

业务规则集中于此，router 只做请求解析与状态码映射。关键不变量：
- trigger 后 enqueue 必须在 db.commit() 之后执行（见 enqueue_run_jobs），否则
  worker 在事务可见前消费会查不到 run_job 而卡 pending。
- 重跑(create_run_job_rerun)只新建 pending RunJob 并用 rerun_source_run_job_id
  /rerun_root_run_job_id 建立来源链，绝不覆盖原始 RunJob/TestJob 的执行事实。
- Run/Execution 状态不落库，统一 read-time worst-wins 聚合(compute_run_status /
  compute_execution_status)，因此 stored status 仅作占位不可信。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, delete, distinct, func, or_, select, tuple_, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.modules.pipelines.models import (
    PipelineConfig,
    PipelineExecution,
    PipelineRun,
    PipelineRunJob,
    PipelineRunNodeInfo,
    PipelineType,
    TestModuleTemplate,
)
from app.modules.pipelines.registry import FRAMEWORK_EXECUTORS, get_pipeline_strategy
from app.modules.pipelines.schemas import (
    PipelineConfigCreate,
    PipelineConfigUpdate,
    PipelineTypeCreate,
    TestModuleTemplateUpdate,
)
from app.modules.resources.service import get_resource, resource_reuse_unavailable_reason
from app.modules.tasks.models import TaskEvent
from app.modules.tasks.service import (
    filter_started_task_keys,
    get_latest_task_event,
    record_task_recovery,
)
from app.modules.test_management.log_collector import LogCollector
from app.modules.test_management.models import (
    MugenCase,
    TestCaseRun,
    TestCaseRunDetail,
    TestEnvNode,
    TestEnvNodeStatus,
    TestEnvSet,
    TestEnvSetStatus,
    TestJob,
    TestLogArtifact,
)
from app.modules.test_management.physical_resources import (
    has_available_owned_physical_resource,
)
from app.modules.test_management.service import (
    TestJobQueueUnavailableError,
    delete_test_job_child_records,
)
from app.modules.vms.service import validate_kernel_64k_target
from app.worker import celery_app

logger = logging.getLogger(__name__)

# --- pipeline type errors ---


class PipelineTypeConflictError(Exception):
    """创建同名 pipeline type 时抛出。"""


class PipelineTypeReferencedError(Exception):
    """删除仍有 config 引用的 pipeline type 时抛出。

    属性 `reference_count` 指示引用该 type 的 config 数量。
    """

    def __init__(self, name: str, reference_count: int) -> None:
        self.reference_count = reference_count
        super().__init__(
            f"pipeline type {name!r} has {reference_count} referencing config(s); delete them first"
        )


class PipelineTypeSystemDeleteError(Exception):
    """删除系统 pipeline type(`is_system=True`)时抛出。"""


class PipelineTypeValidationError(Exception):
    """pipeline type 校验失败时抛出(未知 framework、前端创建 A-class
    strategy_kind 等)。
    """


# --- pipeline config / execution delete errors ---


class PipelineConfigReferencedError(Exception):
    """删除仍有 execution 引用的 pipeline config 时抛出。

    属性 `reference_count` 指示引用该 config 的 execution 数量。
    """

    def __init__(self, config_id: str, reference_count: int) -> None:
        self.reference_count = reference_count
        super().__init__(
            f"pipeline config {config_id!r} has {reference_count} execution(s); delete them first"
        )


class PipelineRunJobRerunError(Exception):
    """所选 Case Run 不满足重跑条件时抛出。"""


class PipelineConfigValidationError(Exception):
    """pipeline config 校验失败（如 release 多版本/内核参数冲突/未知 suite）。

    router 映射为 422。仅对受约束的 pipeline_type（release）校验，其他类型不受影响。
    """


class PipelineRunJobRerunConflict(PipelineRunJobRerunError):
    """来源链或共享环境状态变化，当前不能创建重跑时抛出。"""


class PipelineEnvironmentBusyError(Exception):
    """Execution 中仍有活动 RunJob，不能销毁共享环境。"""


class PhysicalResourceUnavailableError(Exception):
    """流水线所需的触发者自有物理机当前不可用。"""


def ensure_trigger_physical_resources_available(
    db: Session,
    *,
    config: PipelineConfig,
    versions: list[str],
    archs: list[str],
    actor_id: str,
) -> None:
    """按唯一架构和用途校验物理环境；版本共享同组机器，不按数量预留。"""
    if not versions:
        return
    template_ids = list(config.config_data.get("module_template_ids") or [])
    templates = [
        template
        for template in (db.get(TestModuleTemplate, template_id) for template_id in template_ids)
        if template is not None
    ]
    requirements: set[tuple[str, str]] = set()
    for template in templates:
        physical_enabled = template.env_type == "physical" or (
            template.env_type == "both"
            and config.config_data.get(f"{template.name}_physical_enabled", True)
        )
        if not physical_enabled:
            continue
        for arch in archs:
            if arch == "x86_64" and all(version.endswith("-64k") for version in versions):
                continue
            requirements.add((arch, f"{template.name}-update"))

    missing = []
    for arch, usage_scenario in sorted(requirements):
        if not has_available_owned_physical_resource(
            db,
            actor_id=actor_id,
            arch=arch,
            usage_scenario=usage_scenario,
        ):
            missing.append((arch, usage_scenario))
    if missing:
        details = "、".join(f"{arch}/{usage}" for arch, usage in missing)
        raise PhysicalResourceUnavailableError(
            f"没有可用的自有物理机：{details}；请先占用并确保机器未在执行测试"
        )


_RERUNNABLE_CASE_STATUSES = {"passed", "failed", "error", "timeout"}


def _env_set_rerun_unavailable_reason(db: Session, env_set: TestEnvSet) -> str | None:
    if env_set.status in {
        TestEnvSetStatus.DESTROYING.value,
        TestEnvSetStatus.DESTROYED.value,
    }:
        return "来源环境正在销毁或已销毁"
    if not env_set.nodes:
        return "来源环境没有可复用节点"
    for node in env_set.nodes:
        if node.status == TestEnvNodeStatus.DESTROYED.value or not node.resource_id:
            return "来源环境已销毁"
        reason = resource_reuse_unavailable_reason(db, node.resource_id)
        if reason is not None:
            return reason
    return None


def _root_env_set_for_case_run(db: Session, case_run: TestCaseRun) -> TestEnvSet | None:
    """返回 Case Run 重跑链首次执行时绑定的共享环境。"""
    root_case_run = db.get(TestCaseRun, case_run.rerun_root_case_run_id or case_run.id)
    if root_case_run is None or not root_case_run.env_set_id:
        return None
    return db.get(TestEnvSet, root_case_run.env_set_id)


def _run_job_rerun_unavailable_reason(db: Session, run_job: PipelineRunJob) -> str | None:
    if run_job.test_job_id is None:
        return "当前执行没有可重跑的用例"
    if run_job.status not in _TERMINAL_STATUSES:
        return "当前执行尚未结束"
    successor = (
        db.execute(
            select(PipelineRunJob.id).where(PipelineRunJob.rerun_source_run_job_id == run_job.id)
        )
        .scalars()
        .first()
    )
    if successor is not None:
        return "只能从重跑链上最新执行发起重跑"
    rerunnable_cases = [
        case_run
        for case_run in _latest_case_runs_for_run_job(db, run_job)
        if case_run.status in _RERUNNABLE_CASE_STATUSES
    ]
    if not rerunnable_cases:
        return "当前执行没有可重跑的终态用例"
    root_case_ids = {
        case_run.rerun_root_case_run_id or case_run.id for case_run in rerunnable_cases
    }
    root_cases_by_id_rows = (
        db.execute(
            select(TestCaseRun).where(TestCaseRun.id.in_(root_case_ids))
        ).scalars()
    )
    root_cases_by_id = {
        case_run.id: case_run
        for case_run in root_cases_by_id_rows
    }
    env_sets_by_id_rows = (
        db.execute(
            select(TestEnvSet)
            .options(selectinload(TestEnvSet.nodes))
            .where(
                TestEnvSet.id.in_({case_run.env_set_id for case_run in root_cases_by_id.values()})
            )
        ).scalars()
    )
    env_sets_by_id = {
        env_set.id: env_set
        for env_set in env_sets_by_id_rows
    }
    reasons_by_env_set_id: dict[str, str | None] = {}
    reasons = []
    for case_run in rerunnable_cases:
        root_case_id = case_run.rerun_root_case_run_id or case_run.id
        root_case = root_cases_by_id.get(root_case_id)
        env_set = env_sets_by_id.get(root_case.env_set_id) if root_case is not None else None
        if env_set is None:
            reasons.append("来源环境不存在")
            continue
        if env_set.id not in reasons_by_env_set_id:
            reasons_by_env_set_id[env_set.id] = _env_set_rerun_unavailable_reason(db, env_set)
        reasons.append(reasons_by_env_set_id[env_set.id])
    if reasons and all(reasons):
        return reasons[0]
    return None


def enqueue_run_job(run_job: PipelineRunJob, actor_user_id: str) -> str:
    if not get_settings().celery_broker_url:
        raise TestJobQueueUnavailableError("Celery broker is not configured")
    try:
        task_id = run_job.task_id or str(uuid4())
        run_job.task_id = task_id
        task = celery_app.send_task(
            "app.modules.pipelines.tasks.run_pipeline_run_job",
            args=[run_job.id, actor_user_id],
            task_id=task_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise TestJobQueueUnavailableError(str(exc)) from exc
    return str(task.id)


def create_run_job_rerun(
    db: Session,
    *,
    source_run_job_id: str,
    case_run_ids: list[str],
) -> PipelineRunJob:
    """从链上最新终态 RunJob 创建复用来源环境的 pending 重跑。"""
    source = db.get(PipelineRunJob, source_run_job_id)
    if source is None or source.test_job_id is None:
        raise PipelineRunJobRerunError("Pipeline run job has no executable case results")
    # 重跑插入与 Execution 销毁共同锁稳定的父 Run，避免只锁已有 RunJob
    # 时被并发新插入 successor 穿透查询快照。
    db.execute(
        select(PipelineRun.id).where(PipelineRun.id == source.pipeline_run_id).with_for_update()
    ).scalar_one()
    source = db.execute(
        select(PipelineRunJob).where(PipelineRunJob.id == source_run_job_id).with_for_update()
    ).scalar_one()
    unavailable_reason = _run_job_rerun_unavailable_reason(db, source)
    if unavailable_reason is not None:
        raise PipelineRunJobRerunConflict(unavailable_reason)

    selected_ids = set(case_run_ids)
    latest_case_runs = {
        case_run.id: case_run for case_run in _latest_case_runs_for_run_job(db, source)
    }
    case_runs = []
    for case_run_id in selected_ids:
        latest_case_run = latest_case_runs.get(case_run_id)
        if latest_case_run is not None and latest_case_run.status in _RERUNNABLE_CASE_STATUSES:
            case_runs.append(latest_case_run)
    if len(case_runs) != len(selected_ids):
        raise PipelineRunJobRerunError(
            "Only latest terminal executable cases from this rerun chain can be rerun"
        )

    selections = sorted({(case_run.suite_name, case_run.case_name) for case_run in case_runs})
    available_rows = (
        db.execute(
            select(MugenCase).where(
                tuple_(MugenCase.suite_name, MugenCase.case_name).in_(selections)
            )
        ).scalars()
    )
    available = {
        (case.suite_name, case.case_name)
        for case in available_rows
    }
    if not selections or len(available) != len(selections):
        raise PipelineRunJobRerunError("Selected cases are not executable Mugen cases")
    for case_run in case_runs:
        env_set = _root_env_set_for_case_run(db, case_run)
        reason = (
            _env_set_rerun_unavailable_reason(db, env_set)
            if env_set is not None
            else "来源环境不存在"
        )
        if reason is not None:
            raise PipelineRunJobRerunConflict(
                f"{case_run.suite_name}/{case_run.case_name}: {reason}"
            )

    rerun = PipelineRunJob(
        pipeline_run_id=source.pipeline_run_id,
        module_template_id=source.module_template_id,
        arch=source.arch,
        env_type=source.env_type,
        rerun_source_run_job_id=source.id,
        rerun_root_run_job_id=source.rerun_root_run_job_id or source.id,
        rerun_case_selections=[
            {"case_run_id": case_run.id} for case_run in sorted(case_runs, key=lambda item: item.id)
        ],
    )
    db.add(rerun)
    db.flush()
    return rerun


def enqueue_run_jobs(db: Session, run_jobs: list[PipelineRunJob], actor_user_id: str) -> None:
    """在 db.commit() 之后为每个 RunJob 投递 run_pipeline_run_job Celery 任务。

    必须在事务提交后调用：worker 用独立 session 查 run_job，commit 前消费会
    查不到而 return，导致 run_job 永远 pending。单个 enqueue 失败时标该 run_job
    为 error(queue_unavailable) 并继续其余，避免整体回滚导致已投递的 task 查不到
    未提交的 run_job（原竞态）。
    """
    for job in run_jobs:
        if job.task_id is None:
            job.task_id = str(uuid4())
            db.commit()
        try:
            enqueue_run_job(job, actor_user_id)
        except TestJobQueueUnavailableError as exc:
            job.status = "error"
            db.add(
                TaskEvent(
                    task_type="pipeline_runjob",
                    subject_type="runjob",
                    subject_id=job.id,
                    phase="enqueue_failed",
                    message=str(exc),
                    level="error",
                    error_code="queue_unavailable",
                )
            )
            db.commit()


def list_recoverable_pipeline_test_job_keys(
    db: Session,
    *,
    trigger: str,
    as_of: datetime,
    timeout: timedelta,
) -> list[tuple[int, str]]:
    """返回与已启动 Pipeline 执行关联且应恢复的 TestJob 标识。"""
    rows = db.execute(
        select(
            PipelineRunJob.id,
            PipelineRunJob.test_job_id,
            PipelineRunJob.task_id,
        ).where(
            PipelineRunJob.test_job_id.is_not(None),
            PipelineRunJob.task_id.is_not(None),
        )
    ).all()
    candidates = {
        (run_job_id, task_id)
        for run_job_id, _test_job_id, task_id in rows
        if task_id is not None
    }
    started_keys = filter_started_task_keys(
        db,
        task_type="pipeline_runjob",
        subject_type="runjob",
        candidates=candidates,
        started_before=as_of - timeout if trigger == "lazy_read" else None,
    )
    matched = []
    for run_job_id, test_job_id, task_id in rows:
        if test_job_id is None or task_id is None:
            continue
        if (run_job_id, task_id) in started_keys:
            matched.append((test_job_id, task_id))
    return matched


def recover_interrupted_run_jobs(
    db: Session,
    *,
    trigger: str,
    as_of: datetime,
    timeout: timedelta,
) -> int:
    """收敛已启动但未终止的 Pipeline RunJob，并保留恢复事件与审计记录。

    两条互斥分支：
    - 正常分支：有 task_id + 有 started 事件 + status 在 preparing/running，或已请求
      取消的 cancelling；
    - 孤儿分支：`task_id IS NULL` + `status='pending'`，超时基准改用
      `PipelineRunJob.created_at`，两种触发同一条件、启动不立即清，避开
      `plan_run_jobs` 提交后到 `enqueue_run_jobs` 补 task_id 之间的写入窗口。
    """
    active_status = or_(
        PipelineRunJob.status.in_(["preparing", "running"]),
        and_(
            PipelineRunJob.status == "cancelling",
            PipelineRunJob.cancel_requested.is_(True),
        ),
    )
    candidate_rows = db.execute(
        select(PipelineRunJob.id, PipelineRunJob.task_id).where(
            active_status,
            PipelineRunJob.task_id.is_not(None),
        )
    ).all()
    candidates = {
        (run_job_id, task_id)
        for run_job_id, task_id in candidate_rows
        if task_id is not None
    }
    started_keys = filter_started_task_keys(
        db,
        task_type="pipeline_runjob",
        subject_type="runjob",
        candidates=candidates,
        started_before=as_of - timeout if trigger == "lazy_read" else None,
    )
    error_code = "worker_interrupted" if trigger == "worker_startup" else "task_timeout"
    message = (
        "Worker 异常退出，Pipeline RunJob 已标记异常"
        if trigger == "worker_startup"
        else "Pipeline RunJob 超过 15 小时总超时，已标记异常"
    )
    run_jobs = list(
        db.execute(
            select(PipelineRunJob)
            .where(
                active_status,
                PipelineRunJob.task_id.is_not(None),
                tuple_(PipelineRunJob.id, PipelineRunJob.task_id).in_(started_keys),
            )
            .with_for_update(skip_locked=True)
        ).scalars()
    ) if started_keys else []

    orphan_rows = list(
        db.execute(
            select(PipelineRunJob)
            .where(
                PipelineRunJob.task_id.is_(None),
                PipelineRunJob.status == "pending",
                PipelineRunJob.created_at <= as_of - timeout,
            )
            .with_for_update(skip_locked=True)
        ).scalars()
    )

    def _recover(
        run_job: PipelineRunJob, *, code: str, msg: str, celery_task_id: str
    ) -> None:
        last_event = get_latest_task_event(
            db,
            task_type="pipeline_runjob",
            subject_type="runjob",
            subject_id=run_job.id,
            celery_task_id=celery_task_id,
        )
        before_status = run_job.status
        cancelled = run_job.cancel_requested and run_job.status == "cancelling"
        after_status = "cancelled" if cancelled else "error"
        recovery_code = "worker_interrupted_during_cancellation" if cancelled else code
        recovery_message = "Worker 异常退出，取消中的 Pipeline RunJob 已收敛" if cancelled else msg
        run_job.status = after_status
        record_task_recovery(
            db,
            task_type="pipeline_runjob",
            subject_type="runjob",
            subject_id=run_job.id,
            celery_task_id=celery_task_id,
            phase=after_status,
            trigger=trigger,
            before_status=before_status,
            after_status=after_status,
            error_code=recovery_code,
            message=recovery_message,
            last_event=last_event,
        )

    for run_job in run_jobs:
        if run_job.task_id is None:
            raise RuntimeError("收敛分支要求 run_job 已有 task_id")
        _recover(run_job, code=error_code, msg=message, celery_task_id=run_job.task_id)
    for run_job in orphan_rows:
        _recover(
            run_job,
            code="orphaned_no_dispatch",
            msg="申请从未成功派发(无 task_id)，已回收为异常",
            celery_task_id="",
        )
    return len(run_jobs) + len(orphan_rows)


def list_mugen_suites(db: Session) -> list[str]:
    """mugen_cases 表里 distinct suite_name，供 release 配置选 suite 用。"""
    rows = db.execute(select(distinct(MugenCase.suite_name))).scalars().all()
    return sorted(r for r in rows if r)


# --- pipeline types ---


def list_pipeline_types(db: Session) -> list[PipelineType]:
    return list(db.execute(select(PipelineType).order_by(PipelineType.name)).scalars().all())


def create_pipeline_type(
    db: Session,
    payload: PipelineTypeCreate,
) -> PipelineType:
    """创建 B-class direct_run pipeline type。

    校验：
    - `strategy_kind` 必须为 `direct_run`(A-class type 由 seed 生成，不前端创建)。
    - `test_framework` 必须是 FRAMEWORK_EXECUTORS 中代码注册的 framework。
    - `name` 不得与已有 type 冲突。
    """
    if payload.strategy_kind != "direct_run":
        raise PipelineTypeValidationError(
            "only direct_run strategy_kind can be created from frontend"
        )
    if payload.test_framework not in FRAMEWORK_EXECUTORS:
        raise PipelineTypeValidationError(f"unknown test_framework: {payload.test_framework}")
    existing = db.execute(
        select(PipelineType).where(PipelineType.name == payload.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise PipelineTypeConflictError(f"pipeline_type {payload.name!r} already exists")
    pt = PipelineType(
        name=payload.name,
        display_name=payload.display_name,
        strategy_kind=payload.strategy_kind,
        test_framework=payload.test_framework,
        is_system=False,
        default_config=payload.default_config or {},
    )
    db.add(pt)
    db.flush()
    return pt


def delete_pipeline_type(db: Session, type_id: str) -> PipelineType:
    """删除用户创建的 pipeline type。

    拒绝删除 `is_system=True` 的 type；拒绝删除仍有 pipeline_configs 引用的
    type(在 error 中返回引用计数)。
    """
    pt = db.get(PipelineType, type_id)
    if pt is None:
        return None  # caller translates to 404
    if pt.is_system:
        raise PipelineTypeSystemDeleteError(f"system pipeline type {pt.name!r} cannot be deleted")
    reference_count = db.execute(
        select(func.count())
        .select_from(PipelineConfig)
        .where(PipelineConfig.pipeline_type == pt.name)
    ).scalar_one()
    if reference_count > 0:
        raise PipelineTypeReferencedError(pt.name, reference_count)
    db.delete(pt)
    return pt


def list_frameworks() -> list[dict[str, str]]:
    """返回代码注册的 framework 及其展示元数据。"""
    result: list[dict[str, str]] = []
    for name, executor in FRAMEWORK_EXECUTORS.items():
        display_name = getattr(executor, "display_name", None) or name
        result.append({"name": name, "display_name": display_name})
    return result


def list_module_templates(
    db: Session, *, pipeline_type: str | None = None
) -> list[TestModuleTemplate]:
    stmt = select(TestModuleTemplate).order_by(TestModuleTemplate.name)
    if pipeline_type is not None:
        stmt = stmt.where(TestModuleTemplate.pipeline_type == pipeline_type)
    return list(db.execute(stmt).scalars().all())


def get_module_template(db: Session, template_id: str) -> TestModuleTemplate | None:
    return db.get(TestModuleTemplate, template_id)


def create_module_template(db: Session, payload: object) -> TestModuleTemplate:
    template = TestModuleTemplate(
        **payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    )
    db.add(template)
    db.flush()
    return template


def update_module_template(
    db: Session,
    template: TestModuleTemplate,
    payload: TestModuleTemplateUpdate,
) -> TestModuleTemplate:
    for field in (
        "display_name",
        "suite_name",
        "env_set_num",
        "node_num",
        "case_filter",
        "env_type",
        "skip_packages",
        "pre_env_script",
        "rerun_env_script",
        "post_env_script",
        "result_parser",
        "mugen_exec_command",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(template, field, value)
    db.flush()
    return template


def _validate_release_config(
    db: Session,
    *,
    pipeline_type: str,
    versions: list[str],
    config_data: dict[str, object],
) -> None:
    """release 配置校验：单版本、内核参数互斥、case_selections 引用真实 suite/case。

    其他 pipeline_type（update 等）不受影响——update 用 module_template_ids，不走
    case_selections 路径。release 是受约束的直接跑用例类型。create 与 update 共用。
    """
    if pipeline_type != "release":
        return
    if len(versions) != 1:
        raise PipelineConfigValidationError("release 配置只支持单版本")
    data = config_data or {}
    if data.get("kernel_variant") and data.get("kernel_rpm_url"):
        raise PipelineConfigValidationError(
            "kernel_variant 与 kernel_rpm_url 互斥，只能设其一"
        )
    # kernel_rpm_url 格式：HTTP/HTTPS + .rpm 结尾（与 VMRequestCreate 一致，配置级 fail-fast）
    rpm_url = data.get("kernel_rpm_url")
    if rpm_url:
        lower = str(rpm_url).lower()
        if not (lower.startswith(("http://", "https://")) and lower.endswith(".rpm")):
            raise PipelineConfigValidationError(
                "kernel_rpm_url 必须是 HTTP/HTTPS 且以 .rpm 结尾"
            )
    # 物理机用例执行开关：release 默认关闭（跳过为 NOT_EXECUTED），前端开关显式写入
    data.setdefault("release_physical_enabled", False)
    if not isinstance(data["release_physical_enabled"], bool):
        raise PipelineConfigValidationError("release_physical_enabled 必须是布尔值")
    case_selections = data.get("case_selections")
    if case_selections is None:
        # release 必须有 case_selections（避免 kernel_variant 单独提交却产生 0 RunJob 的静默 no-op）
        raise PipelineConfigValidationError("release 配置必须提供 case_selections")
    if not isinstance(case_selections, list):
        raise PipelineConfigValidationError("case_selections 必须是列表")
    for sel in case_selections:
        suite = sel.get("suite_name")
        case_names = sel.get("case_names") or []
        suite_exists = db.execute(
            select(MugenCase).where(MugenCase.suite_name == suite).limit(1)
        ).scalars().first()
        if not suite_exists:
            raise PipelineConfigValidationError(f"未知 suite: {suite}")
        if case_names:
            found = set(
                db.execute(
                    select(MugenCase.case_name).where(
                        MugenCase.suite_name == suite,
                        MugenCase.case_name.in_(case_names),
                    )
                ).scalars().all()
            )
            missing = set(case_names) - found
            if missing:
                raise PipelineConfigValidationError(
                    f"suite {suite} 不含 case: {sorted(missing)}"
                )


def _validate_update_config(
    db: Session, *, pipeline_type: str, config_data: dict | None
) -> None:
    """update 配置校验：pkgunion 与 pkgcmd/pkgserver 互斥。

    pkgunion 的 case_filter=repodata_union 已包含两老模块的用例并集，
    同勾会让重叠用例在新老模块间重复执行。create 与 update 共用。
    """
    if pipeline_type != "update":
        return
    template_ids = list((config_data or {}).get("module_template_ids") or [])
    names = {
        template.name
        for template in (db.get(TestModuleTemplate, tid) for tid in template_ids)
        if template is not None
    }
    if "pkgunion" not in names:
        return
    conflicts = sorted(names & {"pkgcmd", "pkgserver"})
    if conflicts:
        raise PipelineConfigValidationError(
            f"pkgunion 与 {'/'.join(conflicts)} 的用例并集重叠，不能同时勾选；"
            f"如需 pkgunion 覆盖，请从配置中移除 {'/'.join(conflicts)}"
        )


def create_pipeline_config(
    db: Session,
    payload: PipelineConfigCreate,
) -> PipelineConfig:
    _validate_release_config(
        db,
        pipeline_type=payload.pipeline_type,
        versions=payload.versions,
        config_data=payload.config_data or {},
    )
    _validate_update_config(
        db,
        pipeline_type=payload.pipeline_type,
        config_data=payload.config_data or {},
    )
    config = PipelineConfig(
        name=payload.name,
        pipeline_type=payload.pipeline_type,
        versions=payload.versions,
        archs=payload.archs,
        dist=payload.dist,
        image_round=payload.image_round,
        test_framework=payload.test_framework,
        config_data=payload.config_data or {},
    )
    db.add(config)
    db.flush()
    return config


def list_pipeline_configs(db: Session) -> list[PipelineConfig]:
    return list(db.execute(select(PipelineConfig).order_by(PipelineConfig.name)).scalars().all())


def latest_execution_for_config(db: Session, config_id: str) -> PipelineExecution | None:
    """该 config 最近一次 execution（按 triggered_at 降序，含运行中）。无则 None。"""
    return (
        db.execute(
            select(PipelineExecution)
            .where(PipelineExecution.config_id == config_id)
            .order_by(PipelineExecution.triggered_at.desc())
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )


def get_pipeline_config(db: Session, config_id: str) -> PipelineConfig | None:
    return db.get(PipelineConfig, config_id)


def update_pipeline_config(
    db: Session,
    config: PipelineConfig,
    payload: PipelineConfigUpdate,
) -> PipelineConfig:
    if payload.name is not None:
        config.name = payload.name
    if payload.pipeline_type is not None:
        config.pipeline_type = payload.pipeline_type
    if payload.versions is not None:
        config.versions = payload.versions
    if payload.archs is not None:
        config.archs = payload.archs
    if payload.dist is not None:
        config.dist = payload.dist
    if payload.image_round is not None:
        config.image_round = payload.image_round
    if payload.test_framework is not None:
        config.test_framework = payload.test_framework
    if payload.config_data is not None:
        config.config_data = payload.config_data
    _validate_release_config(
        db,
        pipeline_type=config.pipeline_type,
        versions=config.versions,
        config_data=config.config_data or {},
    )
    _validate_update_config(
        db,
        pipeline_type=config.pipeline_type,
        config_data=config.config_data or {},
    )
    db.flush()
    return config


def trigger_pipeline(
    db: Session,
    config: PipelineConfig,
    *,
    versions: list[str] | None = None,
    archs: list[str] | None = None,
    image_round: str | None = None,
    triggered_by: str = "manual",
) -> tuple[PipelineExecution, list[PipelineRunJob]]:
    resolved_versions = versions or config.versions
    resolved_archs = archs or config.archs
    for version in resolved_versions:
        if version.endswith("-64k"):
            validate_kernel_64k_target(os_version=version, arch="aarch64")
            for arch in resolved_archs:
                # The update strategy intentionally omits x86_64/-64k jobs.
                # Any other architecture would produce an unsupported RunJob.
                if arch != "x86_64":
                    validate_kernel_64k_target(os_version=version, arch=arch)
    ensure_trigger_physical_resources_available(
        db,
        config=config,
        versions=resolved_versions,
        archs=resolved_archs,
        actor_id=triggered_by,
    )

    execution = PipelineExecution(
        config_id=config.id,
        triggered_by=triggered_by,
        versions=resolved_versions,
        archs=resolved_archs,
        image_round=image_round,
    )
    db.add(execution)
    db.flush()

    # Seam 1: RunJob 形状按 pipeline_type 分派（update = 版本×架构×模块矩阵）
    strategy = get_pipeline_strategy(db, config.pipeline_type)
    run_jobs = strategy.plan_run_jobs(
        db,
        config=config,
        execution=execution,
        versions=resolved_versions,
        archs=resolved_archs,
        triggered_by=triggered_by,
    )
    db.flush()
    # enqueue 由调用方在 db.commit() 之后执行（见 enqueue_run_jobs），
    # 避免 worker 在事务可见前消费 task 查不到 run_job 而卡 pending。
    return execution, run_jobs


def list_pipeline_executions(
    db: Session,
    *,
    config_id: str | None = None,
    limit: int | None = None,
) -> list[PipelineExecution]:
    """列出 pipeline execution，可按 config_id 过滤和/或限制条数。

    设 `config_id` 时只返回该 config 的 execution(用于单 config 历史页)；
    设 `limit` 时返回最近 N 条(用于全局"近期执行"流)。
    """
    stmt = select(PipelineExecution).order_by(PipelineExecution.triggered_at.desc())
    if config_id is not None:
        stmt = stmt.where(PipelineExecution.config_id == config_id)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars().all())


def delete_pipeline_config(db: Session, config_id: str) -> PipelineConfig | None:
    """删除一个 pipeline config。返回被删的 config，不存在则返回 None。

    若有 execution 引用该 config 则抛 PipelineConfigReferencedError
    (调用方转 409)。
    """
    config = db.get(PipelineConfig, config_id)
    if config is None:
        return None
    reference_count = db.execute(
        select(func.count())
        .select_from(PipelineExecution)
        .where(PipelineExecution.config_id == config_id)
    ).scalar_one()
    if reference_count > 0:
        raise PipelineConfigReferencedError(config_id, reference_count)
    db.delete(config)
    return config


def _cancel_execution_tasks(db: Session, execution_id: str) -> None:
    """取消 pending run_job 并 revoke 运行中的 test_job Celery task。

    必须在删除 execution 记录之前调用并提交，使已入队的 Celery task 能读到
    更新后的状态从而跳过执行。
    """
    run_ids_subq = select(PipelineRun.id).where(PipelineRun.execution_id == execution_id)
    run_job_ids_subq = select(PipelineRunJob.id).where(
        PipelineRunJob.pipeline_run_id.in_(run_ids_subq)
    )

    # 批量取消 pending run_job，使 task handler 跳过它们。
    db.execute(
        update(PipelineRunJob)
        .where(
            PipelineRunJob.id.in_(run_job_ids_subq),
            PipelineRunJob.status == "pending",
        )
        .values(status="cancelled")
    )

    # revoke 运行中的 test_job Celery task 并标记为 error。
    active_test_jobs = (
        db.execute(
            select(TestJob).where(
                TestJob.id.in_(
                    select(PipelineRunJob.test_job_id).where(
                        PipelineRunJob.id.in_(run_job_ids_subq),
                        PipelineRunJob.test_job_id.isnot(None),
                    )
                ),
                TestJob.status.in_(("pending", "preparing", "running")),
            )
        )
        .scalars()
        .all()
    )

    for test_job in active_test_jobs:
        if test_job.task_id:
            celery_app.control.revoke(test_job.task_id, terminate=True)
        test_job.status = "error"

    db.commit()


def _bulk_delete_execution(db: Session, execution_id: str) -> None:
    """用 raw SQL 批量删除 execution 及其子记录。

    避免 ORM N+1 懒加载——execution 含大量 run/run_job/node_info 时
    懒加载会导致请求超时。RunJob 关联的 TestJob 及其子记录一并级联删除：
    环境已由 destroy_execution_envs 先行销毁，删除安全（ADR 0050）。
    """
    run_ids_rows = (
        db.execute(select(PipelineRun.id).where(PipelineRun.execution_id == execution_id))
        .scalars()
        .all()
    )
    run_ids = [
        r
        for r in run_ids_rows
    ]

    if run_ids:
        run_job_ids_rows = (
            db.execute(
                select(PipelineRunJob.id).where(PipelineRunJob.pipeline_run_id.in_(run_ids))
            )
            .scalars()
            .all()
        )
        run_job_ids = [
            rj
            for rj in run_job_ids_rows
        ]

        if run_job_ids:
            db.execute(
                delete(PipelineRunNodeInfo).where(PipelineRunNodeInfo.run_job_id.in_(run_job_ids))
            )
            test_job_ids_rows = (
                db.execute(
                    select(PipelineRunJob.test_job_id).where(
                        PipelineRunJob.id.in_(run_job_ids),
                        PipelineRunJob.test_job_id.is_not(None),
                    )
                )
                .scalars()
                .all()
            )
            test_job_ids = [
                tj
                for tj in test_job_ids_rows
            ]
            delete_test_job_child_records(db, job_ids=test_job_ids)
            if test_job_ids:
                db.execute(delete(TestJob).where(TestJob.id.in_(test_job_ids)))
        db.execute(delete(PipelineRunJob).where(PipelineRunJob.pipeline_run_id.in_(run_ids)))
        db.execute(delete(PipelineRun).where(PipelineRun.id.in_(run_ids)))

    db.execute(delete(PipelineExecution).where(PipelineExecution.id == execution_id))


def delete_pipeline_execution(
    db: Session, execution_id: str, actor=None
) -> PipelineExecution | None:
    """删除单个 pipeline execution。

    取消 pending 的 Celery task、revoke 运行中的 test_job task、销毁环境
    (VM/租约)，然后批量删除全部记录。
    """
    execution = db.get(PipelineExecution, execution_id)
    if execution is None:
        return None

    _cancel_execution_tasks(db, execution_id)

    if actor is not None:
        try:
            destroy_execution_envs(db, execution=execution, actor=actor)
        except Exception:  # noqa: BLE001
            # 清理失败会泄漏 VM/租约资源,但不应阻断删除本身;留 warning 以便运维追查泄漏。
            logger.warning(
                "env destroy cleanup failed for execution %s",
                execution_id,
                exc_info=True,
            )
            pass

    _bulk_delete_execution(db, execution_id)

    return execution


def delete_pipeline_executions_by_config(db: Session, config_id: str, actor=None) -> int:
    """删除一个 config 的全部 execution。

    取消 pending 的 Celery task、revoke 运行中的 test_job task、销毁环境
    (VM/租约)，然后批量删除全部记录。返回删除的 execution 数量。
    """
    execution_ids_rows = (
        db.execute(
            select(PipelineExecution.id).where(PipelineExecution.config_id == config_id)
        )
        .scalars()
        .all()
    )
    execution_ids = [
        e
        for e in execution_ids_rows
    ]

    for execution_id in execution_ids:
        _cancel_execution_tasks(db, execution_id)

    if actor is not None:
        for execution_id in execution_ids:
            execution = db.get(PipelineExecution, execution_id)
            if execution is not None:
                try:
                    destroy_execution_envs(db, execution=execution, actor=actor)
                except Exception:  # noqa: BLE001
                    # 批量删除时单条 execution 的 env 清理失败不应中断整批;
                    # 留 warning 以便运维追查泄漏的 VM/租约资源。
                    logger.warning(
                        "env destroy cleanup failed for execution %s",
                        execution_id,
                        exc_info=True,
                    )

    for execution_id in execution_ids:
        _bulk_delete_execution(db, execution_id)

    return len(execution_ids)


def execution_config_name(db: Session, execution: PipelineExecution) -> str:
    config = db.get(PipelineConfig, execution.config_id)
    return config.name if config else ""


def get_pipeline_execution(db: Session, execution_id: str) -> PipelineExecution | None:
    return db.get(PipelineExecution, execution_id)


def list_execution_runs(db: Session, execution_id: str) -> list[PipelineRun]:
    return list(
        db.execute(
            select(PipelineRun)
            .where(PipelineRun.execution_id == execution_id)
            .order_by(PipelineRun.version)
        )
        .scalars()
        .all()
    )


def list_pipeline_runs(db: Session) -> list[PipelineRun]:
    return list(
        db.execute(select(PipelineRun).order_by(PipelineRun.created_at.desc())).scalars().all()
    )


def get_pipeline_run(db: Session, run_id: str) -> PipelineRun | None:
    return db.get(PipelineRun, run_id)


def list_pipeline_run_jobs(db: Session, run_id: str) -> list[PipelineRunJob]:
    return list(
        db.execute(
            select(PipelineRunJob)
            .where(PipelineRunJob.pipeline_run_id == run_id)
            .order_by(PipelineRunJob.created_at)
        )
        .scalars()
        .all()
    )


def list_run_job_node_infos(db: Session, run_job_id: str) -> list[PipelineRunNodeInfo]:
    run_job = db.get(PipelineRunJob, run_job_id)
    if run_job is not None and run_job.test_job_id is not None:
        rows = db.execute(
            select(TestEnvNode, TestEnvSet)
            .join(TestEnvSet, TestEnvNode.env_set_id == TestEnvSet.id)
            .where(
                TestEnvSet.job_id == run_job.test_job_id,
                TestEnvNode.resource_id.isnot(None),
            )
            .order_by(TestEnvSet.set_index, TestEnvNode.node_index)
        ).all()
        return [
            PipelineRunNodeInfo(
                id=node.id,
                run_job_id=run_job.id,
                resource_id=node.resource_id,
                resource_code=resource.resource_code if resource is not None else None,
                primary_ip=node.primary_ip,
                role=node.role,
                env_set_index=env_set.set_index,
                node_index=node.node_index,
                status=node.status,
            )
            for node, env_set in rows
            for resource in [get_resource(db, node.resource_id)]
        ]
    return list(
        db.execute(
            select(PipelineRunNodeInfo)
            .where(PipelineRunNodeInfo.run_job_id == run_job_id)
            .order_by(PipelineRunNodeInfo.node_index)
        )
        .scalars()
        .all()
    )


# ---- read-time 聚合与详情 API ----

_TERMINAL_STATUSES = {"succeeded", "failed", "error", "cancelled"}
_LOG_TRUNCATE_BYTES = 1024 * 1024


def _latest_run_jobs(run_jobs: list[PipelineRunJob]) -> list[PipelineRunJob]:
    """返回每条原始-重跑链中最新可见的 RunJob。"""
    superseded_ids = {
        job.rerun_source_run_job_id for job in run_jobs if job.rerun_source_run_job_id is not None
    }
    return [job for job in run_jobs if job.id not in superseded_ids]


def _latest_case_runs_for_run_job(db: Session, run_job: PipelineRunJob) -> list[TestCaseRun]:
    """按根 Case Run 返回重跑链上的最新事实，未重跑项沿用来源结果。"""
    root_id = run_job.rerun_root_run_job_id or run_job.id
    chain_job_ids = list(
        db.execute(
            select(PipelineRunJob.test_job_id)
            .where(
                (PipelineRunJob.id == root_id) | (PipelineRunJob.rerun_root_run_job_id == root_id),
                PipelineRunJob.test_job_id.isnot(None),
            )
            .order_by(PipelineRunJob.created_at)
        ).scalars()
    )
    latest: dict[str, TestCaseRun] = {}
    for job_id in chain_job_ids:
        for case_run in db.execute(
            select(TestCaseRun).where(TestCaseRun.job_id == job_id)
        ).scalars():
            latest[case_run.rerun_root_case_run_id or case_run.id] = case_run
    return list(latest.values())


def _worst_wins_run_status(run_jobs: list[PipelineRunJob]) -> str:
    """read-time worst-wins：任一非终态 → running；否则 error > cancelled > failed > succeeded。

    `cancelled`(用户主动中止)优先于 failed:人为截断意味着剩余用例没测完,
    运维关心"为什么被取消"多于"哪个用例红了"。
    """
    statuses = [j.status for j in run_jobs]
    if not statuses:
        return "pending"
    if any(s not in _TERMINAL_STATUSES for s in statuses):
        return "running"
    if "error" in statuses:
        return "error"
    if "cancelled" in statuses:
        return "cancelled"
    if "failed" in statuses:
        return "failed"
    return "succeeded"


def compute_run_status(db: Session, run: PipelineRun) -> str:
    """read-time worst-wins 聚合 Run 的状态(不落库)。"""
    run_jobs = _latest_run_jobs(list_pipeline_run_jobs(db, run.id))
    return _worst_wins_run_status(run_jobs)


def compute_execution_status(db: Session, execution: PipelineExecution) -> str:
    """read-time worst-wins 聚合 Execution 状态(从 Run → RunJob，不落库)。"""
    runs = list_execution_runs(db, execution.id)
    if not runs:
        return "pending"
    statuses = [compute_run_status(db, r) for r in runs]
    if any(s not in _TERMINAL_STATUSES for s in statuses):
        return "running"
    if "error" in statuses:
        return "error"
    if "cancelled" in statuses:
        return "cancelled"
    if "failed" in statuses:
        return "failed"
    return "succeeded"


def get_execution_summary(db: Session, execution_id: str) -> dict | None:
    """Execution 总看板 read-time 聚合：RunJob 状态/计数/日志/IP。"""
    execution = db.get(PipelineExecution, execution_id)
    if execution is None:
        return None
    runs = list_execution_runs(db, execution_id)
    run_summaries: list[dict] = []
    for run in runs:
        run_jobs = _latest_run_jobs(list_pipeline_run_jobs(db, run.id))
        run_status = _worst_wins_run_status(run_jobs)
        job_summaries: list[dict] = []
        for job in run_jobs:
            case_runs = _latest_case_runs_for_run_job(db, job)
            counts = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "no_case": 0,
                "not_executed": 0,
                "pending": 0,
                "running": 0,
                "error": 0,
                "timeout": 0,
            }
            for cr in case_runs:
                key = cr.status if cr.status in counts else "error"
                counts[key] += 1
            # 超时 read-time 标记
            display_status = job.status
            if job.status not in _TERMINAL_STATUSES and job.test_job_id:
                from app.modules.test_management.models import TEST_JOB_TIMEOUT

                tj = db.get(TestJob, job.test_job_id)
                if tj is not None and tj.created_at is not None:
                    from datetime import UTC

                    if datetime.now(UTC) > tj.created_at + TEST_JOB_TIMEOUT:
                        display_status = "timeout"
            nodes = list_run_job_node_infos(db, job.id)
            job_summaries.append(
                {
                    "id": job.id,
                    "module_template_id": job.module_template_id,
                    "arch": job.arch,
                    "env_type": job.env_type,
                    "status": display_status,
                    "counts": counts,
                    "nodes": [
                        {
                            "primary_ip": n.primary_ip,
                            "resource_code": n.resource_code,
                            "role": n.role,
                            "env_set_index": n.env_set_index,
                            "node_index": n.node_index,
                        }
                        for n in nodes
                    ],
                }
            )
        run_summaries.append(
            {
                "id": run.id,
                "version": run.version,
                "status": run_status,
                "jobs": job_summaries,
            }
        )
    return {
        "id": execution.id,
        "config_id": execution.config_id,
        "triggered_by": execution.triggered_by,
        "triggered_at": execution.triggered_at.isoformat() if execution.triggered_at else None,
        "versions": execution.versions,
        "archs": execution.archs,
        "status": _execution_status_from_runs(run_summaries),
        "runs": run_summaries,
    }


def _execution_status_from_runs(run_summaries: list[dict]) -> str:
    statuses = [r["status"] for r in run_summaries]
    if not statuses:
        return "pending"
    if any(s not in _TERMINAL_STATUSES for s in statuses):
        return "running"
    if "error" in statuses:
        return "error"
    if "cancelled" in statuses:
        return "cancelled"
    if "failed" in statuses:
        return "failed"
    return "succeeded"


def list_run_logs(db: Session, run_id: str) -> list[TestLogArtifact]:
    return list(
        db.execute(
            select(TestLogArtifact)
            .where(
                (TestLogArtifact.pipeline_run_id == run_id)
                | TestLogArtifact.job_id.in_(
                    select(PipelineRunJob.test_job_id).where(
                        PipelineRunJob.pipeline_run_id == run_id,
                        PipelineRunJob.test_job_id.isnot(None),
                    )
                )
            )
            .order_by(TestLogArtifact.created_at)
        )
        .scalars()
        .all()
    )


def _artifact_belongs_to_run(db: Session, *, artifact: TestLogArtifact, run_id: str) -> bool:
    if artifact.pipeline_run_id == run_id:
        return True
    return (
        db.scalar(
            select(PipelineRunJob.id).where(
                PipelineRunJob.pipeline_run_id == run_id,
                PipelineRunJob.test_job_id == artifact.job_id,
            )
        )
        is not None
    )


def read_run_log_content(db: Session, run_id: str, artifact_id: str) -> str | None:
    artifact = db.get(TestLogArtifact, artifact_id)
    if artifact is None or not _artifact_belongs_to_run(db, artifact=artifact, run_id=run_id):
        return None
    try:
        content = artifact.storage_path and __read_file(artifact.storage_path)
    except OSError:
        # 日志文件读取失败(缺失/IO 错)按软失败返回 None,留 debug 便于排查为何取不到日志。
        logger.debug("failed to read run log artifact %s", artifact_id, exc_info=True)
        return None
    if content is None:
        return ""
    if len(content.encode("utf-8", errors="replace")) > _LOG_TRUNCATE_BYTES:
        return content[:_LOG_TRUNCATE_BYTES] + "\n...[truncated, download for full]"
    return content


def __read_file(path: str) -> str:
    from pathlib import Path

    return Path(path).read_text(encoding="utf-8", errors="replace")


def list_dir_artifact_files(db: Session, run_id: str, artifact_id: str) -> list[str] | None:
    """列出目录型 artifact 内的文件名。不存在或非目录时返回 None。"""
    artifact = db.get(TestLogArtifact, artifact_id)
    if artifact is None or not _artifact_belongs_to_run(db, artifact=artifact, run_id=run_id):
        return None
    if artifact.artifact_type != "pkg_folder":
        return None
    collector = LogCollector(base_dir="")
    return collector.list_dir_files(artifact)


def read_dir_artifact_file(
    db: Session, run_id: str, artifact_id: str, file_path: str
) -> str | None:
    """读取目录型 artifact 中的单个文件。防 path traversal。"""
    artifact = db.get(TestLogArtifact, artifact_id)
    if artifact is None or not _artifact_belongs_to_run(db, artifact=artifact, run_id=run_id):
        return None
    if artifact.artifact_type != "pkg_folder":
        return None
    collector = LogCollector(base_dir="")
    content = collector.read_dir_file(artifact, file_path)
    if content is None:
        return None
    if len(content.encode("utf-8", errors="replace")) > _LOG_TRUNCATE_BYTES:
        return content[:_LOG_TRUNCATE_BYTES] + "\n...[truncated, download for full]"
    return content


def get_case_mugen_log(db: Session, run_job_id: str, case_run_id: str) -> dict | None:
    """查找并返回指定 case_run 的 mugen 日志文件内容。

    在 artifact_name 以 ``logs`` 结尾的 ``pkg_folder`` artifact 中搜索匹配
    ``{suite_name}/{case_name}/`` 前缀的文件。返回首个匹配文件的内容(截断
    至 1 MB)及全部匹配文件路径列表；无匹配则返回 None。
    """
    run_job = db.get(PipelineRunJob, run_job_id)
    if run_job is None or not run_job.test_job_id:
        return None
    case_run = db.get(TestCaseRun, case_run_id)
    if case_run is None or case_run.job_id != run_job.test_job_id:
        return None
    suite = case_run.suite_name
    case_name = case_run.case_name
    if not suite or not case_name:
        return None

    collector = LogCollector(base_dir="")
    prefix = f"{suite}/{case_name}/"
    artifacts = list(
        db.execute(
            select(TestLogArtifact).where(
                TestLogArtifact.job_id == run_job.test_job_id,
                TestLogArtifact.artifact_type == "pkg_folder",
            )
        )
        .scalars()
        .all()
    )
    matching_files: list[str] = []
    matched_artifact: TestLogArtifact | None = None
    for art in artifacts:
        if not art.artifact_name.endswith("logs"):
            continue
        files = collector.list_dir_files(art)
        for f in files:
            if f.startswith(prefix):
                matching_files.append(f)
                if matched_artifact is None:
                    matched_artifact = art
    if not matching_files or matched_artifact is None:
        return None
    matching_files.sort()
    content = collector.read_dir_file(matched_artifact, matching_files[0])
    if content is None:
        return None
    if len(content.encode("utf-8", errors="replace")) > _LOG_TRUNCATE_BYTES:
        content = content[:_LOG_TRUNCATE_BYTES] + "\n...[truncated, download for full]"
    return {
        "content": content,
        "file_path": matching_files[0],
        "files": matching_files,
        "run_id": run_job.pipeline_run_id,
        "artifact_id": matched_artifact.id,
    }


def get_run_job_detail(db: Session, run_job_id: str) -> dict | None:
    run_job = db.get(PipelineRunJob, run_job_id)
    if run_job is None:
        return None
    rerun_root_id = run_job.rerun_root_run_job_id or run_job.id
    rerun_chain = list(
        db.execute(
            select(PipelineRunJob)
            .where(
                (PipelineRunJob.id == rerun_root_id)
                | (PipelineRunJob.rerun_root_run_job_id == rerun_root_id)
            )
            .order_by(PipelineRunJob.created_at)
        )
        .scalars()
        .all()
    )
    chain_by_id = {item.id: item for item in rerun_chain}

    def rerun_attempt(item: PipelineRunJob) -> int:
        attempt = 0
        while item.rerun_source_run_job_id:
            attempt += 1
            item = chain_by_id.get(item.rerun_source_run_job_id)
            if item is None:
                break
        return attempt

    case_runs = (
        list(
            db.execute(
                select(TestCaseRun)
                .where(TestCaseRun.job_id == run_job.test_job_id)
                .order_by(TestCaseRun.suite_name, TestCaseRun.case_name)
            )
            .scalars()
            .all()
        )
        if run_job.test_job_id
        else []
    )
    latest_case_runs = sorted(
        _latest_case_runs_for_run_job(db, run_job),
        key=lambda item: (item.suite_name, item.case_name),
    )
    case_runs_by_id = {item.id: item for item in [*case_runs, *latest_case_runs]}
    root_case_ids = {item.rerun_root_case_run_id or item.id for item in latest_case_runs}
    missing_root_case_ids = root_case_ids - case_runs_by_id.keys()
    if missing_root_case_ids:
        case_runs_by_id_rows = (
            db.execute(
                select(TestCaseRun).where(TestCaseRun.id.in_(missing_root_case_ids))
            ).scalars()
        )
        case_runs_by_id.update(
            {
                item.id: item
                for item in case_runs_by_id_rows
            }
        )
    env_set_ids = {item.env_set_id for item in case_runs}
    for item in latest_case_runs:
        root_case = case_runs_by_id.get(item.rerun_root_case_run_id or item.id)
        if root_case is not None:
            env_set_ids.add(root_case.env_set_id)
    env_sets_by_id_rows = (
        db.execute(
            select(TestEnvSet)
            .options(selectinload(TestEnvSet.nodes))
            .where(TestEnvSet.id.in_(env_set_ids))
        ).scalars()
    )
    env_sets_by_id = {
        item.id: item
        for item in env_sets_by_id_rows
    }
    details_by_case_run_id: dict[str, list[TestCaseRunDetail]] = {}
    for detail in db.execute(
        select(TestCaseRunDetail)
        .where(TestCaseRunDetail.case_run_id.in_(case_runs_by_id))
        .order_by(TestCaseRunDetail.case_run_id, TestCaseRunDetail.sub_test_name)
    ).scalars():
        details_by_case_run_id.setdefault(detail.case_run_id, []).append(detail)
    env_set_reasons: dict[str, str | None] = {}

    def env_set_unavailable_reason(env_set: TestEnvSet | None) -> str | None:
        if env_set is None:
            return "来源环境不存在"
        if env_set.id not in env_set_reasons:
            env_set_reasons[env_set.id] = _env_set_rerun_unavailable_reason(db, env_set)
        return env_set_reasons[env_set.id]

    case_details: list[dict] = []
    for cr in case_runs:
        env_set = env_sets_by_id.get(cr.env_set_id)
        case_unavailable_reason = env_set_unavailable_reason(env_set)
        sub = details_by_case_run_id.get(cr.id, [])
        case_details.append(
            {
                "id": cr.id,
                "suite_name": cr.suite_name,
                "case_name": cr.case_name,
                "status": cr.status,
                "exit_code": cr.exit_code,
                "stdout_summary": cr.stdout_summary,
                "stderr_summary": cr.stderr_summary,
                "env_type": env_set.env_type if env_set else None,
                "env_set_id": env_set.id if env_set else None,
                "env_set_index": env_set.set_index if env_set else None,
                "rerun_source_case_run_id": cr.rerun_source_case_run_id,
                "rerun_root_case_run_id": cr.rerun_root_case_run_id,
                "can_rerun": (
                    cr.status in _RERUNNABLE_CASE_STATUSES and case_unavailable_reason is None
                ),
                "rerun_unavailable_reason": case_unavailable_reason,
                "sub_cases": [
                    {
                        "id": s.id,
                        "sub_test_name": s.sub_test_name,
                        "status": s.status,
                    }
                    for s in sub
                ],
            }
        )
    attempt_by_test_job_id = {
        item.test_job_id: rerun_attempt(item)
        for item in rerun_chain
        if item.test_job_id is not None
    }
    rerun_candidates: list[dict] = []
    for cr in latest_case_runs:
        root_case = case_runs_by_id.get(cr.rerun_root_case_run_id or cr.id)
        env_set = env_sets_by_id.get(root_case.env_set_id) if root_case is not None else None
        case_unavailable_reason = env_set_unavailable_reason(env_set)
        if cr.status not in _RERUNNABLE_CASE_STATUSES:
            case_unavailable_reason = "该状态不支持重跑"
        sub = details_by_case_run_id.get(cr.id, [])
        rerun_candidates.append(
            {
                "id": cr.id,
                "suite_name": cr.suite_name,
                "case_name": cr.case_name,
                "status": cr.status,
                "exit_code": cr.exit_code,
                "stdout_summary": cr.stdout_summary,
                "stderr_summary": cr.stderr_summary,
                "env_type": env_set.env_type if env_set else None,
                "env_set_id": env_set.id if env_set else None,
                "env_set_index": env_set.set_index if env_set else None,
                "rerun_source_case_run_id": cr.rerun_source_case_run_id,
                "rerun_root_case_run_id": cr.rerun_root_case_run_id,
                "latest_rerun_attempt": attempt_by_test_job_id.get(cr.job_id, 0),
                "can_rerun": (
                    cr.status in _RERUNNABLE_CASE_STATUSES and case_unavailable_reason is None
                ),
                "rerun_unavailable_reason": case_unavailable_reason,
                "sub_cases": [
                    {
                        "id": s.id,
                        "sub_test_name": s.sub_test_name,
                        "status": s.status,
                    }
                    for s in sub
                ],
            }
        )
    nodes = list_run_job_node_infos(db, run_job_id)
    job_logs = (
        list(
            db.execute(
                select(TestLogArtifact)
                .where(TestLogArtifact.job_id == run_job.test_job_id)
                .order_by(TestLogArtifact.created_at)
            )
            .scalars()
            .all()
        )
        if run_job.test_job_id
        else []
    )
    # 取 TestJob 的错误信息(若存在)
    test_job = db.get(TestJob, run_job.test_job_id) if run_job.test_job_id else None
    error_code = test_job.error_code if test_job else None
    error_message = test_job.error_message if test_job else None
    rerun_unavailable_reason = _run_job_rerun_unavailable_reason(db, run_job)
    chain_case_counts = {
        item.id: (
            db.execute(
                select(func.count())
                .select_from(TestCaseRun)
                .where(TestCaseRun.job_id == item.test_job_id)
            ).scalar_one()
            if item.test_job_id is not None
            else 0
        )
        for item in rerun_chain
    }

    # 取该 RunJob 的 task event(runjob 级错误如构建失败以 subject_id=run_job.id
    # 记录；test-job 级 event 用 test_job_id 记录)。
    # 物理机 -64k 的内核安装事件记录在 resource 级别（subject_id=resource_id，
    # task_type=pxe_install），这里只纳入 kernel_64k_* / kernel_latest_* 的 resource
    # 级事件，PXE 细节（sync_files/bind_dhcp 等）不放入 RunJob 执行过程。
    task_events: list[dict] = []
    subject_ids = [run_job.id]
    if run_job.test_job_id:
        subject_ids.append(run_job.test_job_id)
    events = list(
        db.execute(
            select(TaskEvent)
            .where(TaskEvent.subject_id.in_(subject_ids))
            .order_by(TaskEvent.created_at.asc())
        )
        .scalars()
        .all()
    )
    resource_ids = [n.resource_id for n in nodes if n.resource_id]
    if resource_ids:
        resource_events = list(
            db.execute(
                select(TaskEvent)
                .where(
                    TaskEvent.subject_id.in_(resource_ids),
                    TaskEvent.phase.like("kernel_64k_%")
                    | TaskEvent.phase.like("kernel_latest_%"),
                )
                .order_by(TaskEvent.created_at.asc())
            )
            .scalars()
            .all()
        )
        events.extend(resource_events)
        events.sort(key=lambda e: e.created_at)
    for ev in events:
        task_events.append(
            {
                "phase": ev.phase,
                "level": ev.level,
                "message": ev.message or "",
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
        )

    return {
        "id": run_job.id,
        "pipeline_run_id": run_job.pipeline_run_id,
        "module_template_id": run_job.module_template_id,
        "arch": run_job.arch,
        "env_type": run_job.env_type,
        "test_job_id": run_job.test_job_id,
        "rerun_source_run_job_id": run_job.rerun_source_run_job_id,
        "rerun_root_run_job_id": run_job.rerun_root_run_job_id,
        "rerun_attempt": rerun_attempt(run_job),
        "can_rerun": rerun_unavailable_reason is None,
        "rerun_unavailable_reason": rerun_unavailable_reason,
        "rerun_chain": [
            {
                "id": item.id,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "rerun_attempt": rerun_attempt(item),
                "case_count": chain_case_counts[item.id],
            }
            for item in rerun_chain
        ],
        "status": run_job.status,
        "error_code": error_code,
        "error_message": error_message,
        "result_parser": test_job.result_parser if test_job else None,
        "update_packages": test_job.update_packages if test_job else [],
        "task_events": task_events,
        "case_runs": case_details,
        "rerun_candidates": rerun_candidates,
        "nodes": [
            {
                "primary_ip": n.primary_ip,
                "resource_code": n.resource_code,
                "role": n.role,
                "env_set_index": n.env_set_index,
                "env_type": next(
                    (
                        es.env_type
                        for es in (test_job.env_sets if test_job else [])
                        if es.set_index == n.env_set_index
                    ),
                    None,
                ),
                "node_index": n.node_index,
                "resource_id": n.resource_id,
            }
            for n in nodes
        ],
        "logs": [
            {
                "id": art.id,
                "artifact_type": art.artifact_type,
                "artifact_name": art.artifact_name,
                "module": art.module,
                "arch": art.arch,
                "content": (
                    read_run_log_content(db, run_job.pipeline_run_id, art.id)
                    if art.artifact_type == "module_log"
                    and (
                        "pkgmanage-details" in art.artifact_name
                        or "pkgcmd" in art.artifact_name
                        or "update_list" in art.artifact_name
                    )
                    else None
                ),
            }
            for art in job_logs
        ],
    }


def ensure_execution_envs_destroyable(
    db: Session, execution_id: str, *, lock: bool = False
) -> None:
    """校验 Execution 无活动 RunJob；执行销毁时锁定父 Run 与重跑创建互斥。"""
    if lock:
        list(
            db.execute(
                select(PipelineRun.id)
                .where(PipelineRun.execution_id == execution_id)
                .with_for_update()
            ).scalars()
        )
    statement = (
        select(PipelineRunJob)
        .join(PipelineRun, PipelineRunJob.pipeline_run_id == PipelineRun.id)
        .where(PipelineRun.execution_id == execution_id)
    )
    run_jobs = list(db.execute(statement).scalars())
    if any(job.status not in _TERMINAL_STATUSES and job.status != "cancelled" for job in run_jobs):
        raise PipelineEnvironmentBusyError("当前执行仍在使用环境，不能销毁")


def destroy_execution_envs(db: Session, *, execution: PipelineExecution, actor) -> dict:
    """发版后人工统一销毁：遍历 Execution 所有 RunJob 的 TestJob 的 env_set.nodes，
    VM 走 destroy_env_node_vm，物理机释放租约。不改 RunJob/Execution 状态。

    使用 raw SQL 查 test_job_id 避免 ORM identity map 返回已删除的 stale 对象。
    """
    from app.modules.leases.schemas import LeaseRelease
    from app.modules.leases.service import get_resource_active_lease, release_lease
    from app.modules.resources.models import Resource, ResourceType
    from app.modules.test_management.envs.vm import destroy_env_node_vm
    run_ids_rows = (
        db.execute(select(PipelineRun.id).where(PipelineRun.execution_id == execution.id))
        .scalars()
        .all()
    )
    run_ids = [
        r
        for r in run_ids_rows
    ]

    ensure_execution_envs_destroyable(db, execution.id, lock=True)

    test_job_ids = list(
        db.execute(
            select(PipelineRunJob.test_job_id).where(
                PipelineRunJob.pipeline_run_id.in_(run_ids),
                PipelineRunJob.test_job_id.isnot(None),
            )
        ).scalars()
    )
    db.execute(
        update(TestEnvSet)
        .where(TestEnvSet.job_id.in_(test_job_ids))
        .values(status=TestEnvSetStatus.DESTROYING.value)
    )
    db.commit()

    destroyed: list[str] = []
    failed: list[str] = []
    processed: set[str] = set()
    for test_job_id in test_job_ids:
        job = db.get(TestJob, test_job_id)
        if job is None:
            continue
        for env_set in job.env_sets:
            for node in env_set.nodes:
                if not node.resource_id:
                    continue
                if node.resource_id in processed:
                    continue
                processed.add(node.resource_id)
                res = db.get(Resource, node.resource_id)
                if res is None:
                    continue
                try:
                    if res.resource_type == ResourceType.VIRTUAL.value:
                        destroy_env_node_vm(db, job=job, node=node, actor=actor)
                    else:
                        lease = get_resource_active_lease(db, res)
                        if lease is not None:
                            release_lease(
                                db,
                                lease=lease,
                                actor=actor,
                                payload=LeaseRelease(
                                    reason=f"pipeline destroy-envs execution {execution.id}"
                                ),
                                force=True,
                                allow_virtual=True,
                            )
                    db.execute(
                        update(TestEnvNode)
                        .where(TestEnvNode.resource_id == node.resource_id)
                        .values(status=TestEnvNodeStatus.DESTROYED.value)
                    )
                    destroyed.append(node.resource_id)
                except Exception:  # noqa: BLE001
                    failed.append(node.resource_id)
    db.execute(
        update(TestEnvSet)
        .where(TestEnvSet.job_id.in_(test_job_ids))
        .values(
            status=(TestEnvSetStatus.ERROR.value if failed else TestEnvSetStatus.DESTROYED.value)
        )
    )
    db.commit()
    return {"destroyed": destroyed, "failed": failed}

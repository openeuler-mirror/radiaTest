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

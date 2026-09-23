# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from billiard.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.test_management.case_log_context import (
    CaseLogContext,
    pop_case_log_context,
    set_case_log_context,
)
from app.modules.test_management.envs.physical import create_env_node_physical
from app.modules.test_management.envs.vm import (
    cleanup_env_vms,
    create_env_node_vm,
    node_runtime,
)
from app.modules.test_management.errors import EnvSetHangError, TestJobExecutionError
from app.modules.test_management.frameworks.mugen_runner import (
    archive_rerun_case_outputs,
    prepare_env,
    prepare_rerun_env,
    run_case,
    run_hook,
    ssh_connect_refused,
    sync_vm_disks,
    try_vm_recovery,
    vm_host_channel,
)
from app.modules.test_management.models import (
    TestCaseRunStatus,
    TestEnvNodeStatus,
    TestEnvSet,
    TestEnvSetStatus,
    TestEnvType,
    TestJob,
    TestJobStatus,
    test_job_deadline,
    utc_now,
)
from app.modules.test_management.remote import RemoteCommandError
from app.modules.test_management.service import record_test_job_event
from app.modules.users.models import User

logger = logging.getLogger(__name__)

# SSH 连续失败断路阈值：同一环境集内连续 3 个用例因挂死或 SSH 失败，
# 视为环境不可用，跳过本环境集剩余用例并标 error，避免空转刷错误。
_SSH_FAILURE_CIRCUIT_BREAKER = 3
_CANCEL_OBSERVATION_SECONDS = 15
_TERMINAL_TEST_JOB_STATUSES = frozenset(
    {
        TestJobStatus.SUCCEEDED.value,
        TestJobStatus.FAILED.value,
        TestJobStatus.ERROR.value,
        TestJobStatus.CANCELLED.value,
    }
)


def _is_cancel_requested(db: Session, job_id: int) -> bool:
    """Re-query cancel_requested from DB to catch cross-session updates.

    Uses a scalar select to bypass the session identity map, ensuring the
    latest committed value is read (not a stale in-memory snapshot).
    """
    return (
        db.execute(select(TestJob.cancel_requested).where(TestJob.id == job_id)).scalar() or False
    )


def _cancel_check_factory(job_id: int):
    """Create a thread-safe cancel check callable that opens its own DB session."""
    def _check() -> bool:
        with SessionLocal() as wdb:
            return _is_cancel_requested(wdb, job_id)

    return _check


def _start_test_job_cancel_watcher(
    job_id: int, cancel_event: threading.Event
) -> tuple[threading.Event, threading.Thread]:
    """在整个 TestJob 生命周期观察已提交的取消请求。

    VM 创建不能安全地在中途终止，但 watcher 会让随后环境准备和 SSH 命令立刻读取同一个
    `cancel_event`；调用方必须在结束时设置返回的 stop event，避免遗留轮询线程。
    """
    stop_event = threading.Event()
    cancel_check = _cancel_check_factory(job_id)

    def _watch() -> None:
        while not stop_event.wait(_CANCEL_OBSERVATION_SECONDS):
            try:
                if cancel_check():
                    cancel_event.set()
                    return
            except Exception:  # noqa: BLE001
                logger.debug("test job cancel watcher check failed", exc_info=True)

    watcher = threading.Thread(
        target=_watch,
        name=f"test-job-cancel-{job_id}",
        daemon=True,
    )
    watcher.start()
    return stop_event, watcher


def _mark_env_set_not_executed(
    db: Session, *, env_set: TestEnvSet, commit: bool = True
) -> None:
    """把当前环境集的节点与用例收敛为未执行，不依赖其他任务的事件文本。"""
    for node in env_set.nodes:
        if node.status in {
            TestEnvNodeStatus.PENDING.value,
            TestEnvNodeStatus.CREATING.value,
        }:
            node.status = TestEnvNodeStatus.NOT_EXECUTED.value
    for case_run in env_set.case_runs:
        if case_run.status == TestCaseRunStatus.PENDING.value:
            case_run.status = TestCaseRunStatus.NOT_EXECUTED.value
            case_run.completed_at = utc_now()
    env_set.status = TestEnvSetStatus.NOT_EXECUTED.value
    if commit:
        db.commit()


def cancel_unstarted_test_job(db: Session, *, job: TestJob) -> None:
    """收敛尚未开始的 TestJob，避免取消后留下 pending EnvSet/CaseRun。"""
    for env_set in job.env_sets:
        if env_set.status == TestEnvSetStatus.PENDING.value:
            _mark_env_set_not_executed(db, env_set=env_set, commit=False)
    job.status = TestJobStatus.CANCELLED.value
    job.completed_at = utc_now()
    record_test_job_event(
        db,
        job=job,
        phase="cancelled",
        message="测试任务已取消",
    )
    db.commit()


def _test_job_is_terminal(db: Session, job: TestJob) -> bool:
    """刷新 TestJob，避免存活 Worker 覆盖恢复服务已提交的终态。"""
    db.refresh(job, with_for_update=True)
    return job.status in _TERMINAL_TEST_JOB_STATUSES


def fail_job(db: Session, job: TestJob, *, code: str, message: str) -> bool:
    """把任务置为 error 并记 error 事件，不清理环境(由调用方决定)。"""
    if _test_job_is_terminal(db, job):
        return False
    job.status = TestJobStatus.ERROR.value
    job.error_code = code
    job.error_message = message
    job.completed_at = utc_now()
    record_test_job_event(
        db,
        job=job,
        phase="error",
        message=message,
        level="error",
        error_code=code,
    )
    return True


def cleanup_failed_job_envs(
    db: Session,
    *,
    job: TestJob,
    actor: User,
) -> None:
    """失败后清理环境集 VM。保留规则：已 destroyed 跳过；keep_failed_env 且该
    环境为 failed 则保留；keep_env(全保留)一律跳过。清理失败只记事件不抛。
    """
    for env_set in job.env_sets:
        if env_set.status == TestEnvSetStatus.DESTROYED.value:
            continue
        if job.keep_failed_env and env_set.status == TestEnvSetStatus.FAILED.value:
            continue
        # keep_env（流水线全保留）→ 跳过 cleanup，保留环境供人工检查
        if job.keep_env:
            continue
        env_set.status = TestEnvSetStatus.ERROR.value
        db.commit()
        try:
            cleanup_env_vms(db, job=job, env_set=env_set, actor=actor, preserve=False)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            env_set.status = TestEnvSetStatus.ERROR.value
            record_test_job_event(
                db,
                job=job,
                phase="env_cleanup_failed",
                message=f"env {env_set.set_index} 清理失败：{exc}",
                level="error",
                error_code="env_cleanup_failed",
            )
            db.commit()


def handle_job_execution_error(
    db: Session,
    *,
    job: TestJob,
    actor: User,
    code: str,
    message: str,
) -> None:
    """统一异常出口：标 error 提交后清理环境，避免异常路径泄漏未清理的 VM。"""
    if not fail_job(db, job, code=code, message=message):
        return
    db.commit()
    cleanup_failed_job_envs(db, job=job, actor=actor)


def ensure_test_job_within_deadline(
    job: TestJob, cancel_event: threading.Event | None = None
) -> None:
    """超过 15h 总超时或 cancel_event 命中即抛,供各步骤前置检查。

    cancel_event 优先于超时判定:取消是用户明确意图,`job_cancelled` 与
    `task_timeout` 走不同收敛路径(cancel → CANCELLED / timeout → ERROR)。
    """
    if cancel_event is not None and cancel_event.is_set():
        raise TestJobExecutionError("job_cancelled", "测试任务已取消")
    if utc_now() >= test_job_deadline(job):
        raise TestJobExecutionError("task_timeout", "测试任务超过 15 小时总超时")


def execute_env_set(
    db: Session,
    *,
    job: TestJob,
    env_set: TestEnvSet,
    actor: User,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, bool]:
    """执行单个环境集，返回 (has_failure, has_error)。

    has_failure=用例本身失败(failed/timeout)，has_error=环境问题(挂死/SSH)。
    挂死与 SSH 失败不中断环境集，给自愈一个机会继续后续用例；连续失败达
    _SSH_FAILURE_CIRCUIT_BREAKER 时先尝试宿主机硬复位恢复(每环境集一次，
    ADR 0046)，失败才把剩余用例标 error 并跳出。post_env 在
    finally 执行，保证即使中途异常也跑收尾脚本。状态按结果收敛：
    error>failed>succeeded。

    cancel_event 由 `process_test_job` 顶层持有，Soft 超时或 DB cancel/watcher
    命中会 set 它；挂死只使用 run_case 内部的用例级事件。本函数在每步前后判
    job 级取消，不再受"卡在 SSH 12h"阻塞。
    """
    ensure_test_job_within_deadline(job, cancel_event)
    if env_set.status == TestEnvSetStatus.NOT_EXECUTED.value:
        return False, False
    is_rerun = job.rerun_source_job_id is not None
    if not is_rerun:
        env_set.status = TestEnvSetStatus.CREATING_VMS.value
        db.commit()
        use_physical = (env_set.env_type or job.env_type) == TestEnvType.PHYSICAL.value
        for node in env_set.nodes:
            ensure_test_job_within_deadline(job, cancel_event)
            if use_physical:
                ready = create_env_node_physical(
                    db, job=job, env_set=env_set, node=node, actor=actor
                )
            else:
                ready = create_env_node_vm(db, job=job, env_set=env_set, node=node, actor=actor)
            if not ready:
                _mark_env_set_not_executed(db, env_set=env_set)
                return False, False
        # 立即提交节点 IP，让 Pipeline 通过 Test Job 节点读取时马上可见。
        db.commit()
    control_node = next(node for node in env_set.nodes if node.role == "control")
    peer_node = next((node for node in env_set.nodes if node.role == "peer"), None)
    control = node_runtime(db, control_node)
    peer = node_runtime(db, peer_node) if peer_node else None
    directory = (
        prepare_rerun_env(
            db, job=job, env_set=env_set, control=control, peer=peer, cancel_event=cancel_event
        )
        if is_rerun
        else prepare_env(
            db, job=job, env_set=env_set, control=control, peer=peer, cancel_event=cancel_event
        )
    )
    ensure_test_job_within_deadline(job, cancel_event)

    # 宿主通道探针门（ADR 0046 修订）：物理机/无宿主 VM 不探活不恢复。
    host_channel = vm_host_channel(db, control)
    env_has_failure = False
    env_has_error = False
    rerun_prepare_failed = False
    # 恢复预算标记必须在 try 之前初始化：pre_env 期间取消/失败时 finally 的
    # post_env 探针门会读它（job 10244/10245 曾因晚赋值抛 UnboundLocalError，
    # 把 job_cancelled 吞成 unexpected_execution_error）。
    vm_recovery_used = False
    try:
        if is_rerun:
            try:
                if job.rerun_env_script:
                    run_hook(
                        db,
                        job=job,
                        control=control,
                        directory=directory,
                        script_name="rerun_env.sh",
                        phase="rerun_env",
                        error_code="rerun_env_failed",
                        cancel_event=cancel_event,
                    )
                archive_rerun_case_outputs(
                    job=job,
                    control=control,
                    case_runs=list(env_set.case_runs),
                    cancel_event=cancel_event,
                )
            except (RemoteCommandError, TestJobExecutionError):
                rerun_prepare_failed = True
                for case_run in env_set.case_runs:
                    if case_run.status == TestCaseRunStatus.PENDING.value:
                        case_run.status = TestCaseRunStatus.ERROR.value
                        case_run.completed_at = utc_now()
                db.commit()
                raise
        elif job.pre_env_script:
            ensure_test_job_within_deadline(job, cancel_event)
            run_hook(
                db,
                job=job,
                control=control,
                directory=directory,
                script_name="pre_env.sh",
                phase="pre_env",
                cancel_event=cancel_event,
            )

        # 环境就绪后强制刷盘（ADR 0046 修订二，job 10238）：硬复位等价拔电，
        # 页缓存未落盘的写会丢（mugen env.json 0 字节 → 后续用例全失败）。
        # 只对有宿主通道的 VM 同步——只有它们可能被硬复位。
        if host_channel is not None:
            sync_vm_disks(control)
        env_set.status = TestEnvSetStatus.RUNNING.value
        job.status = TestJobStatus.RUNNING.value
        db.commit()
        case_iter = iter(env_set.case_runs)
        consecutive_failures = 0
        cancel_check = _cancel_check_factory(job.id)
        for case_run in case_iter:
            if case_run.status in (
                TestCaseRunStatus.SKIPPED.value,
                TestCaseRunStatus.NO_CASE.value,
                TestCaseRunStatus.NOT_EXECUTED.value,
            ):
                continue
            ensure_test_job_within_deadline(job, cancel_event)
            if _is_cancel_requested(db, job.id):
                if case_run.status in {
                    TestCaseRunStatus.PENDING.value,
                    TestCaseRunStatus.RUNNING.value,
                }:
                    case_run.status = TestCaseRunStatus.NOT_EXECUTED.value
                    case_run.completed_at = utc_now()
                for remaining in case_iter:
                    if remaining.status in {
                        TestCaseRunStatus.PENDING.value,
                        TestCaseRunStatus.RUNNING.value,
                    }:
                        remaining.status = TestCaseRunStatus.NOT_EXECUTED.value
                        remaining.completed_at = utc_now()
                env_set.status = TestEnvSetStatus.NOT_EXECUTED.value
                db.commit()
                return env_has_failure, env_has_error
            try:
                # 用例间探针（ADR 0046 修订，job 10235）：上例杀掉 sshd
                # （连接拒绝签名）时先恢复再执行，本用例拿回真实结果；
                # 超时/失联不触发（机器状态未知，交给挂死链路）。预算按
                # 尝试计：失败不重试，避免连环硬复位烧任务预算。
                if (
                    host_channel is not None
                    and not vm_recovery_used
                    and ssh_connect_refused(control)
                ):
                    vm_recovery_used = True
                    try_vm_recovery(
                        db,
                        job=job,
                        control=control,
                        cancel_event=cancel_event,
                        trigger="probe",
                    )
                run_case(
                    db,
                    job=job,
                    control=control,
                    case_run=case_run,
                    cancel_check=cancel_check,
                    cancel_event=cancel_event,
                )
                # 用例正常返回即刷盘：保住日志/results（ADR 0046 修订二）。
                # 杀手用例自身例外——它杀 sshd 时 sync 已连不上，静默失败。
                if host_channel is not None:
                    sync_vm_disks(control)
                consecutive_failures = 0
            except (EnvSetHangError, RemoteCommandError):
                # vm_hang/SSH 失败：当前用例已被 run_case 标 ERROR，不 break，
                # 给 HangDetector 自愈和 SSH 恢复一个机会继续后续用例。
                env_has_error = True
                consecutive_failures += 1
                if consecutive_failures >= _SSH_FAILURE_CIRCUIT_BREAKER:
                    # 熔断前先试宿主机硬复位恢复（每环境集一次，ADR 0046）：
                    # 成功则计数清零继续剩余用例，失败维持原熔断批量标 error。
                    if not vm_recovery_used and try_vm_recovery(
                        db, job=job, control=control, cancel_event=cancel_event
                    ):
                        vm_recovery_used = True
                        consecutive_failures = 0
                        continue
                    for remaining in case_iter:
                        if remaining.status in {
                            TestCaseRunStatus.PENDING.value,
                            TestCaseRunStatus.RUNNING.value,
                        }:
                            remaining.status = TestCaseRunStatus.ERROR.value
                            remaining.completed_at = utc_now()
                    db.commit()
                    break
                continue
            if case_run.status in {TestCaseRunStatus.FAILED.value, TestCaseRunStatus.TIMEOUT.value}:
                env_has_failure = True
    finally:
        if job.post_env_script:
            # post_env 前探针（ADR 0046 修订，job 10235）：末尾用例杀掉
            # sshd 时先恢复，避免清理失败把全 passed 的 job 误标 error；
            # 恢复失败则清理失败仍按现状向上传播。
            if (
                host_channel is not None
                and not vm_recovery_used
                and ssh_connect_refused(control)
            ):
                vm_recovery_used = True
                try_vm_recovery(
                    db,
                    job=job,
                    control=control,
                    cancel_event=cancel_event,
                    trigger="probe",
                )
            try:
                run_hook(
                    db,
                    job=job,
                    control=control,
                    directory=directory,
                    script_name="post_env.sh",
                    phase="post_env",
                    cancel_event=cancel_event,
                )
            except (RemoteCommandError, TestJobExecutionError):
                if not rerun_prepare_failed:
                    raise

    if env_has_error:
        env_set.status = TestEnvSetStatus.ERROR.value
    elif env_has_failure:
        env_set.status = TestEnvSetStatus.FAILED.value
    else:
        env_set.status = TestEnvSetStatus.SUCCEEDED.value
    db.commit()
    return env_has_failure, env_has_error


@dataclass
class _EnvSetResult:
    env_set_id: str
    has_failure: bool
    has_error: bool


def _run_env_set_thread(
    job_id: str,
    env_set_id: str,
    actor_id: str,
    cancel_event: threading.Event,
) -> _EnvSetResult:
    """在独立线程+独立 DB session 中跑一个环境集，供并行执行。

    线程级 session 隔离避免多线程共享同一 session 的竞态。异常分类处理：
    SoftTimeLimitExceeded 直接抛(由上层判 task_timeout)；`job_cancelled` 只
    由本线程被打断触发,不打断主线程已决定的终态(Soft 或 DB cancel),只收敛
    env_set 与剩余用例到 `not_executed` 后返回,不再 handle_job_execution_error;
    其他 Remote/Execution 异常走统一错误出口;其余异常记
    unexpected_execution_error。完成后按 keep_failed_env/keep_env 决定是否清理 VM。
    """
    with SessionLocal() as db:
        job = db.get(TestJob, job_id)
        env_set = db.get(TestEnvSet, env_set_id)
        actor = db.get(User, actor_id)
        if job is None or env_set is None or actor is None:
            return _EnvSetResult(env_set_id=env_set_id, has_failure=False, has_error=True)
        try:
            env_failed, env_error = execute_env_set(
                db, job=job, env_set=env_set, actor=actor, cancel_event=cancel_event
            )
            if not job.keep_env:
                cleanup_env_vms(
                    db,
                    job=job,
                    env_set=env_set,
                    actor=actor,
                    preserve=job.keep_failed_env and env_failed,
                )
            return _EnvSetResult(env_set_id=env_set_id, has_failure=env_failed, has_error=env_error)
        except SoftTimeLimitExceeded:
            raise
        except TestJobExecutionError as exc:
            # `job_cancelled`:case 循环被 job 级 cancel_event(Soft / DB)打断。
            # 收敛本 env_set 的 PENDING case + 清理 VM,把主线程的终态判定权
            # 让出去(主线程根据 DB `cancel_requested` → cancelled 或
            # `handle_job_execution_error` → error+cleanup_failed_job_envs)。
            if exc.code == "job_cancelled":
                for case_run in env_set.case_runs:
                    if case_run.status == TestCaseRunStatus.PENDING.value:
                        case_run.status = TestCaseRunStatus.NOT_EXECUTED.value
                        case_run.completed_at = utc_now()
                db.commit()
                if not job.keep_env:
                    try:
                        cleanup_env_vms(
                            db,
                            job=job,
                            env_set=env_set,
                            actor=actor,
                            preserve=False,
                        )
                    except (TestJobExecutionError, RemoteCommandError) as cleanup_exc:
                        record_test_job_event(
                            db,
                            job=job,
                            phase="env_cleanup_failed",
                            message=f"env {env_set.set_index} 清理失败：{cleanup_exc}",
                            level="error",
                            error_code="env_cleanup_failed",
                        )
                        db.commit()
                return _EnvSetResult(
                    env_set_id=env_set_id, has_failure=False, has_error=False
                )
            handle_job_execution_error(db, job=job, actor=actor, code=exc.code, message=str(exc))
            return _EnvSetResult(env_set_id=env_set_id, has_failure=False, has_error=True)
        except RemoteCommandError as exc:
            handle_job_execution_error(
                db, job=job, actor=actor, code="remote_command_failed", message=str(exc)
            )
            return _EnvSetResult(env_set_id=env_set_id, has_failure=False, has_error=True)
        except Exception as exc:  # noqa: BLE001
            handle_job_execution_error(
                db,
                job=job,
                actor=actor,
                code="unexpected_execution_error",
                message=f"测试任务执行异常：{exc}",
            )
            return _EnvSetResult(env_set_id=env_set_id, has_failure=False, has_error=True)


def process_test_job(
    job_id: int, case_log_context: CaseLogContext | None = None
) -> None:
    """测试任务顶层编排：pending→preparing→并行执行各环境集→收敛终态。

    环境集用 ThreadPoolExecutor(≤4) 并行，各线程独立 session。手工管理
    executor(不再用 `with`)是 P0-A 终止语义的关键:Celery `soft_time_limit`
    以信号在主线程抛 SoftTimeLimitExceeded,`with __exit__` 会 shutdown(wait=True)
    阻塞至所有子线程跑完(可能再等 12h case 自然 timeout)。改为:先 set
    job 级 `cancel_event`,让每线程内的 `run_process`/`event.wait` 秒级返回,
    再 shutdown(wait=True) 收敛。终态优先级 error>failed>succeeded;
    DB `cancel_requested` 走 cancelled 分支。

    case_log_context（ADR 0048）：executor 注入的逐 case 日志上传上下文，
    注册到进程内注册表供 run_case 读取；所有终止路径统一注销防泄漏。
    """
    if case_log_context is not None:
        set_case_log_context(job_id, case_log_context)
    try:
        _process_test_job_inner(job_id)
    finally:
        pop_case_log_context(job_id)


def _process_test_job_inner(job_id: int) -> None:
    with SessionLocal() as db:
        job = db.get(TestJob, job_id)
        if job is None or job.status != TestJobStatus.PENDING.value:
            return
        if _is_cancel_requested(db, job.id):
            cancel_unstarted_test_job(db, job=job)
            return
        job.status = TestJobStatus.PREPARING.value
        record_test_job_event(db, job=job, phase="started", message="worker 已领取测试任务")
        db.commit()

        actor = db.get(User, job.creator_user_id)
        if actor is None or not actor.is_active:
            fail_job(db, job, code="creator_unavailable", message="测试任务创建人不可用")
            db.commit()
            return

        env_set_ids = [es.id for es in job.env_sets]
        any_case_failed = False
        any_env_error = False
        cancel_event = threading.Event()
        cancel_watcher_stop, cancel_watcher = _start_test_job_cancel_watcher(job.id, cancel_event)
        executor: ThreadPoolExecutor | None = None
        try:
            ensure_test_job_within_deadline(job, cancel_event)
            max_workers = min(len(env_set_ids), 4)
            executor = ThreadPoolExecutor(max_workers=max_workers)
            futures = {
                executor.submit(
                    _run_env_set_thread, job_id, es_id, actor.id, cancel_event
                ): es_id
                for es_id in env_set_ids
            }
            for future in as_completed(futures):
                result: _EnvSetResult = future.result()
                any_case_failed = any_case_failed or result.has_failure
                any_env_error = any_env_error or result.has_error
        except SoftTimeLimitExceeded:
            # 关键:set 通知各 env_set 线程内 run_process/cancel_event.wait 秒退,
            # 再 shutdown 才能不等 12h;否则 with __exit__ 会阻塞在此。
            cancel_event.set()
            if executor is not None:
                executor.shutdown(wait=True)
            handle_job_execution_error(
                db,
                job=job,
                actor=actor,
                code="task_timeout",
                message="测试任务超过 15 小时总超时",
            )
            return
        except (RemoteCommandError, TestJobExecutionError) as exc:
            cancel_event.set()
            if executor is not None:
                executor.shutdown(wait=True)
            code = exc.code if isinstance(exc, TestJobExecutionError) else "remote_command_failed"
            handle_job_execution_error(db, job=job, actor=actor, code=code, message=str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            cancel_event.set()
            if executor is not None:
                executor.shutdown(wait=True)
            handle_job_execution_error(
                db,
                job=job,
                actor=actor,
                code="unexpected_execution_error",
                message=f"测试任务执行异常：{exc}",
            )
            return
        finally:
            # 兜底:未进任何 handler 的路径(如 ensure_..._deadline 前置抛)不阻塞主线程。
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)
            cancel_watcher_stop.set()
            cancel_watcher.join(timeout=1)

        if _test_job_is_terminal(db, job):
            return
        if _is_cancel_requested(db, job.id):
            job.status = TestJobStatus.CANCELLED.value
            job.completed_at = utc_now()
            record_test_job_event(
                db,
                job=job,
                phase="cancelled",
                message="测试任务已取消",
            )
            db.commit()
            return

        if any_env_error:
            job.status = TestJobStatus.ERROR.value
        elif any_case_failed:
            job.status = TestJobStatus.FAILED.value
        else:
            job.status = TestJobStatus.SUCCEEDED.value
        job.completed_at = utc_now()
        record_test_job_event(
            db,
            job=job,
            phase="completed",
            message="测试任务执行完成",
            level="error" if (any_case_failed or any_env_error) else "info",
        )
        db.commit()

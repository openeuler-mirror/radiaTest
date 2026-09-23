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
import os
import shlex
import shutil
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.credentials import decrypt_secret
from app.db.session import SessionLocal
from app.modules.resources.models import Resource
from app.modules.test_management.case_log_context import get_case_log_context
from app.modules.test_management.console_capture import (
    bmc_power_on,
    capture_bmc_diagnostics,
    capture_vm_console_output,
    vm_domstate_alive,
    vm_hard_reset,
)
from app.modules.test_management.envs.vm import VMNodeRuntime
from app.modules.test_management.errors import EnvSetHangError, TestJobExecutionError
from app.modules.test_management.hang_detector import (
    WATCH_POWER_OFF_DEADLINE_SECONDS,
    WATCH_TIMEOUT_SECONDS,
    HangDetector,
)
from app.modules.test_management.log_collector import LogCollector
from app.modules.test_management.models import (
    TestCaseRun,
    TestCaseRunDetail,
    TestCaseRunStatus,
    TestEnvSet,
    TestJob,
    TestLogArtifact,
    remaining_test_job_seconds,
    utc_now,
)
from app.modules.test_management.remote import (
    RemoteCommandError,
    RemoteCommandResult,
    run_remote_bash_command,
    run_ssh_command,
    scp_directory,
    write_remote_file,
)
from app.modules.test_management.result_parser import (
    SubTestResult,
    parse_ltp_log,
    parse_mugen_results_dir,
    parse_pkgmanage_log,
)
from app.modules.test_management.service import record_test_job_event

logger = logging.getLogger(__name__)

# Mugen 测试执行器：在 control 节点上部署 Mugen、配置节点、跑用例并解析结果。
# 所有远程命令的子超时都从 job 的剩余时间派生(job_step_timeout)，保证不越过
# 15h 总超时。挂死由 HangDetector 心跳探测，抓 console 输出存诊断产物。
SSH_READY_TIMEOUT_SECONDS = 900
MUGEN_PREPARE_TIMEOUT_SECONDS = 3600
HOOK_TIMEOUT_SECONDS = 3600
CASE_TIMEOUT_SECONDS = 12 * 3600
# 命令超时比用例超时多 60s，留出 SSH transport 收尾时间，避免边界误判。
CASE_COMMAND_TIMEOUT_SECONDS = CASE_TIMEOUT_SECONDS + 60
SSH_READY_RETRY_INTERVAL_SECONDS = 10
MUGEN_CONFIG_MAX_ATTEMPTS = 5
MUGEN_CONFIG_ATTEMPT_TIMEOUT_SECONDS = 120
HEARTBEAT_TIMEOUT_SECONDS = 30
# 强制刷盘上限（ADR 0046 修订二）：常规用例脏页为 KB~MB 级，30s 足够兜住
# 重型写用例；best-effort，超时即放弃（数据丢失面交给下个边界收敛）。
SYNC_TIMEOUT_SECONDS = 30


def job_step_timeout(job: TestJob, maximum: int) -> int:
    """取本步骤可用秒数=min(剩余总时间, maximum)。剩余≤0 直接判 task_timeout。"""
    timeout_seconds = remaining_test_job_seconds(job, maximum=maximum)
    if timeout_seconds <= 0:
        raise TestJobExecutionError("task_timeout", "测试任务超过 15 小时总超时")
    return timeout_seconds


def require_success(
    db: Session,
    *,
    job: TestJob,
    phase: str,
    message: str,
    result: RemoteCommandResult,
    error_code: str,
) -> None:
    if result.returncode == 0:
        return
    detail = result.stderr or result.stdout or f"exit code {result.returncode}"
    record_test_job_event(
        db,
        job=job,
        phase=phase,
        message=f"{message}: {detail}",
        level="error",
        error_code=error_code,
    )
    raise TestJobExecutionError(error_code, f"{message}: {detail}")


def quote_env(value: str | None) -> str:
    return shlex.quote(str(value) if value is not None else "")


def _raise_cancelled() -> None:
    """统一"测试任务已取消"收敛出口。

    code 固定为 `job_cancelled`,由 `_run_env_set_thread` / `process_test_job`
    顶层根据 DB `cancel_requested` 决定标 `cancelled` 还是 `error(task_timeout)`。
    所有"因 cancel_event 打断本步骤"的调用点必须走这个出口,避免各文件里的
    错误码字符串与"测试任务已取消"消息漂移。
    """
    raise TestJobExecutionError("job_cancelled", "测试任务已取消")


def run_control_command(
    *,
    control: VMNodeRuntime,
    script: str,
    timeout_seconds: int,
    on_line: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    cancel_events: Sequence[threading.Event] = (),
) -> RemoteCommandResult:
    return run_remote_bash_command(
        host=control.ip,
        username=control.username,
        password=control.password,
        script=script,
        timeout_seconds=timeout_seconds,
        verify_host_key=False,
        on_line=on_line,
        cancel_event=cancel_event,
        cancel_events=cancel_events,
    )


def wait_for_ssh_ready(
    db: Session,
    node: VMNodeRuntime,
    *,
    job: TestJob,
    timeout_seconds: int = SSH_READY_TIMEOUT_SECONDS,
    retry_interval_seconds: int = SSH_READY_RETRY_INTERVAL_SECONDS,
    cancel_event: threading.Event | None = None,
) -> None:
    """轮询等待节点 SSH 可登录，超时抛 ssh_ready_timeout。

    每 3 次重试记一条事件(约 30s)，让用户能看到 SSH 失败原因而不只是卡住。
    cancel_event 非空时每轮开始判打断，`run_control_command` 返回 cancelled=True
    立即抛 `job_cancelled`；等待间隔用 `event.wait` 让取消秒级生效。
    """
    timeout_seconds = job_step_timeout(job, timeout_seconds)
    deadline = time.monotonic() + timeout_seconds
    last_detail = "SSH is not ready"
    attempt = 0
    while True:
        if cancel_event is not None and cancel_event.is_set():
            _raise_cancelled()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TestJobExecutionError("ssh_ready_timeout", last_detail)
        attempt += 1
        result = run_control_command(
            control=node,
            script="true",
            timeout_seconds=max(1, min(10, int(remaining))),
            cancel_event=cancel_event,
        )
        if result.cancelled:
            _raise_cancelled()
        if result.returncode == 0:
            return
        last_detail = result.stderr or result.stdout or "SSH is not ready"
        # Log every 3rd attempt (~30s interval) so user can see WHY SSH fails
        if attempt % 3 == 0:
            record_test_job_event(
                db,
                job=job,
                phase="ssh_retry",
                message=f"SSH 重试 #{attempt}（剩余 {int(remaining)}s）: {last_detail[:200]}",
                level="warning",
            )
            db.commit()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TestJobExecutionError("ssh_ready_timeout", last_detail)
        interval = min(retry_interval_seconds, remaining)
        if cancel_event is not None:
            if cancel_event.wait(interval):
                _raise_cancelled()
        else:
            time.sleep(interval)


def write_control_file(
    *,
    job: TestJob,
    control: VMNodeRuntime,
    path: str,
    content: str,
    cancel_event: threading.Event | None = None,
) -> None:
    result = write_remote_file(
        host=control.ip,
        username=control.username,
        password=control.password,
        path=path,
        content=content,
        timeout_seconds=job_step_timeout(job, 30),
        verify_host_key=False,
        cancel_event=cancel_event,
    )
    if result.cancelled:
        _raise_cancelled()
    if result.returncode != 0:
        raise TestJobExecutionError("ssh_write_failed", result.stderr or result.stdout)


def build_env_file(
    *,
    job: TestJob,
    env_set: TestEnvSet,
    control: VMNodeRuntime,
    peer: VMNodeRuntime | None,
) -> str:
    values = {
        "KRONOS_JOB_ID": job.id,
        "KRONOS_JOB_NAME": job.name,
        "KRONOS_ENV_SET_INDEX": str(env_set.set_index),
        "KRONOS_NODE_NUM": str(env_set.node_num),
        "KRONOS_DIST": job.dist,
        "KRONOS_OS_VERSION": job.os_version,
        "KRONOS_IMAGE_ROUND": job.image_round,
        "KRONOS_ARCH": job.arch,
        "OET_PATH": "/opt/mugen",
        "KRONOS_CONTROL_IP": control.ip,
        "KRONOS_CONTROL_SSH_USER": control.username,
        "KRONOS_CONTROL_SSH_PASSWORD": control.password,
        "KRONOS_PEER_IP": peer.ip if peer else "",
        "KRONOS_PEER_SSH_USER": peer.username if peer else "",
        "KRONOS_PEER_SSH_PASSWORD": peer.password if peer else "",
        "KRONOS_TEST_PACKAGES": " ".join(job.update_packages or []),
        # docker 类模块的 pre_env.sh 会 source kronos.env 后用这个 sha `git
        # fetch/checkout` 显式 pin mugen 到用例快照版本;不 pin 每次跟 master
        # tip 漂移,mugen 上游 breaking 会静默击穿(见 ADR0031 前后 2026-09
        # upstream eb987747b 一例)。
        "KRONOS_MUGEN_COMMIT_SHA": job.mugen_commit_sha,
    }
    return "".join(f"{key}={quote_env(value)}\n" for key, value in values.items())


def job_dir(job: TestJob, env_set: TestEnvSet) -> str:
    return f"/root/kronos/jobs/{job.id}/env-{env_set.set_index}"


def prepare_mugen(
    db: Session,
    *,
    job: TestJob,
    control: VMNodeRuntime,
    cancel_event: threading.Event | None = None,
) -> None:
    settings = get_settings()
    record_test_job_event(db, job=job, phase="mugen_prepare", message="开始部署 Mugen")
    script = "\n".join(
        [
            "set -Eeuo pipefail",
            # Install prerequisites before cloning mugen.
            # Official openEuler images don't ship git/python3-pip by default.
            "dnf install -y git python3 python3-pip 2>/dev/null || true",
            "rm -rf /opt/mugen",
            (
                f"git clone --depth=1 --branch {shlex.quote(settings.mugen_repo_branch)} "
                f"{shlex.quote(settings.mugen_repo_url)} /opt/mugen"
            ),
            "cd /opt/mugen",
            f"git fetch --depth=1 origin {shlex.quote(job.mugen_commit_sha)} || true",
            f"git checkout {shlex.quote(job.mugen_commit_sha)}",
            "bash dep_install.sh",
        ]
    )
    result = run_control_command(
        control=control,
        script=script,
        timeout_seconds=job_step_timeout(job, MUGEN_PREPARE_TIMEOUT_SECONDS),
        cancel_event=cancel_event,
    )
    if result.cancelled:
        _raise_cancelled()
    require_success(
        db,
        job=job,
        phase="mugen_prepare_failed",
        message="Mugen 部署失败",
        result=result,
        error_code="mugen_prepare_failed",
    )
    record_test_job_event(db, job=job, phase="mugen_prepare_done", message="Mugen 部署完成")


def configure_mugen_node(
    db: Session,
    *,
    job: TestJob,
    control: VMNodeRuntime,
    node: VMNodeRuntime,
    role: str,
    cancel_event: threading.Event | None = None,
) -> None:
    """在 control 上用 mugen.sh -c 配置某节点(control/peer)，失败重试至 MAX_ATTEMPTS。

    重试是因为新 VM 首次 SSH 可能抖动，给几次机会避免误判。最终失败抛
    mugen_config_failed。cancel_event 命中或本地命令被主动打断则抛 job_cancelled。
    """
    record_test_job_event(db, job=job, phase="mugen_config", message=f"配置 Mugen {role} 节点")
    script = (
        "cd /opt/mugen && "
        f"bash mugen.sh -c --ip {shlex.quote(node.ip)} "
        f"--password {shlex.quote(node.password)} "
        f"--user {shlex.quote(node.username)} --port 22"
    )
    deadline = time.monotonic() + job_step_timeout(job, SSH_READY_TIMEOUT_SECONDS)
    last_detail = ""
    attempt = 0
    while True:
        if cancel_event is not None and cancel_event.is_set():
            _raise_cancelled()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        attempt += 1
        result = run_control_command(
            control=control,
            script=script,
            timeout_seconds=max(30, min(MUGEN_CONFIG_ATTEMPT_TIMEOUT_SECONDS, int(remaining))),
            cancel_event=cancel_event,
        )
        if result.cancelled:
            _raise_cancelled()
        if result.returncode == 0:
            record_test_job_event(
                db,
                job=job,
                phase="mugen_config_done",
                message=f"Mugen {role} 节点配置完成",
            )
            return
        last_detail = result.stderr or result.stdout or f"exit code {result.returncode}"
        if attempt >= MUGEN_CONFIG_MAX_ATTEMPTS:
            break
        record_test_job_event(
            db,
            job=job,
            phase="mugen_config_retry",
            level="warning",
            message=(
                f"Mugen {role} 节点配置重试 #{attempt}"
                f"（剩余 {int(remaining)}s）: {last_detail[:200]}"
            ),
        )
        db.commit()
        remaining = deadline - time.monotonic()
        if remaining > 0:
            interval = min(SSH_READY_RETRY_INTERVAL_SECONDS, remaining)
            if cancel_event is not None:
                if cancel_event.wait(interval):
                    _raise_cancelled()
            else:
                time.sleep(interval)
    record_test_job_event(
        db,
        job=job,
        phase="mugen_config_failed",
        level="error",
        error_code="mugen_config_failed",
        message=f"Mugen {role} 节点配置失败: {last_detail}",
    )
    raise TestJobExecutionError("mugen_config_failed", f"Mugen {role} 节点配置失败: {last_detail}")


def prepare_env(
    db: Session,
    *,
    job: TestJob,
    env_set: TestEnvSet,
    control: VMNodeRuntime,
    peer: VMNodeRuntime | None,
    cancel_event: threading.Event | None = None,
) -> str:
    """准备环境：等 SSH 就绪→写 kronos.env 与 hook 脚本→部署 Mugen 并配置节点。

    mugen_exec_command 非空时(如 docker 模块在容器内跑 mugen)跳过 Mugen 部署。
    返回 control 上的工作目录路径，供后续 hook 与用例执行复用。cancel_event
    向下透传到 wait_for_ssh_ready / prepare_mugen / configure_mugen_node,命中
    则各步立即抛 job_cancelled,取消不再需要等各步自然 timeout。
    """
    record_test_job_event(db, job=job, phase="ssh_ready", message="等待测试环境 SSH 可登录")
    wait_for_ssh_ready(db, control, job=job, cancel_event=cancel_event)
    if peer:
        wait_for_ssh_ready(db, peer, job=job, cancel_event=cancel_event)
    record_test_job_event(db, job=job, phase="ssh_ready_done", message="测试环境 SSH 已就绪")
    # Skip repos with broken metadata (e.g. 20.03-LTS-SP4 update repo on
    # public mirror has sha512 checksum mismatches) so dnf falls back to
    # OS/everything repos. Written here (before mugen_prepare and pre_env.sh)
    # so ALL modules are covered, including docker (where prepare_mugen is
    # skipped because mugen_exec_command is set).
    run_control_command(
        control=control,
        script="echo 'skip_if_unavailable=True' >> /etc/dnf/dnf.conf 2>/dev/null || true",
        timeout_seconds=30,
        cancel_event=cancel_event,
    )
    directory = job_dir(job, env_set)
    write_control_file(
        job=job,
        control=control,
        path=f"{directory}/kronos.env",
        content=build_env_file(job=job, env_set=env_set, control=control, peer=peer),
        cancel_event=cancel_event,
    )
    if job.pre_env_script:
        write_control_file(
            job=job,
            control=control,
            path=f"{directory}/pre_env.sh",
            content=job.pre_env_script,
            cancel_event=cancel_event,
        )
    if job.post_env_script:
        write_control_file(
            job=job,
            control=control,
            path=f"{directory}/post_env.sh",
            content=job.post_env_script,
            cancel_event=cancel_event,
        )

    # Skip mugen deployment on VM host when mugen_exec_command is set
    # (e.g. docker module runs mugen inside a container via docker exec)
    if not job.mugen_exec_command:
        prepare_mugen(db, job=job, control=control, cancel_event=cancel_event)
        configure_mugen_node(
            db,
            job=job,
            control=control,
            node=control,
            role="control",
            cancel_event=cancel_event,
        )
        if peer:
            configure_mugen_node(
                db,
                job=job,
                control=control,
                node=peer,
                role="peer",
                cancel_event=cancel_event,
            )
    return directory


def prepare_rerun_env(
    db: Session,
    *,
    job: TestJob,
    env_set: TestEnvSet,
    control: VMNodeRuntime,
    peer: VMNodeRuntime | None,
    cancel_event: threading.Event | None = None,
) -> str:
    """校验来源节点并写本次脚本，不重新部署或配置 Mugen。"""
    record_test_job_event(db, job=job, phase="ssh_ready", message="检查复用环境 SSH")
    wait_for_ssh_ready(db, control, job=job, cancel_event=cancel_event)
    if peer:
        wait_for_ssh_ready(db, peer, job=job, cancel_event=cancel_event)
    directory = job_dir(job, env_set)
    write_control_file(
        job=job,
        control=control,
        path=f"{directory}/kronos.env",
        content=build_env_file(job=job, env_set=env_set, control=control, peer=peer),
        cancel_event=cancel_event,
    )
    for script_name, content in (
        ("rerun_env.sh", job.rerun_env_script),
        ("post_env.sh", job.post_env_script),
    ):
        if content:
            write_control_file(
                job=job,
                control=control,
                path=f"{directory}/{script_name}",
                content=content,
                cancel_event=cancel_event,
            )
    return directory


def archive_rerun_case_outputs(
    *,
    job: TestJob,
    control: VMNodeRuntime,
    case_runs: list[TestCaseRun],
    cancel_event: threading.Event | None = None,
) -> None:
    """把所选 case 的远端旧输出移出 Mugen 活跃目录。"""
    archive = f"/root/kronos/rerun-archive/{job.id}"
    commands = [f"mkdir -p {shlex.quote(archive)}"]
    log_name = (
        "docker"
        if job.mugen_exec_command and "openEuler_test" in job.mugen_exec_command
        else {
            "ltp": "kernel",
            "pkgcmd": "pkgcmd",
            "pkgmanage": "pkgmanage",
            "pkgserver": "pkgserver",
            "pkgunion": "pkgunion",
        }.get(job.result_parser or "")
    )
    if log_name:
        module_archive = f"{archive}/module-logs"
        commands.extend(
            [
                f"mkdir -p {shlex.quote(module_archive)}",
                (f"mv /opt/{log_name}-logs/* {shlex.quote(module_archive)}/ 2>/dev/null || true"),
            ]
        )
    case_commands: list[str] = []
    for case_run in case_runs:
        suite = shlex.quote(case_run.suite_name)
        case = shlex.quote(case_run.case_name)
        case_commands.extend(
            [
                f"mkdir -p {archive}/{suite}",
                f"mv /opt/mugen/logs/{suite}/{case} {archive}/{suite}/ 2>/dev/null || true",
                (
                    "for bucket in succeed failed skipped; do "
                    f"mv /opt/mugen/results/{suite}/$bucket/{case} "
                    f"{archive}/{suite}/$bucket-{case} 2>/dev/null || true; done"
                ),
            ]
        )
    if job.mugen_exec_command and "openEuler_test" in job.mugen_exec_command:
        commands.append(
            "docker exec openEuler_test bash -c "
            + shlex.quote(
                "\n".join(command.replace("/opt/mugen", "/home/mugen") for command in case_commands)
            )
            + " || true"
        )
    else:
        commands.extend(case_commands)
    result = run_control_command(
        control=control,
        script="\n".join(commands),
        timeout_seconds=job_step_timeout(job, 120),
        cancel_event=cancel_event,
    )
    if result.cancelled:
        _raise_cancelled()
    if result.returncode != 0:
        raise TestJobExecutionError("rerun_output_archive_failed", result.stderr or result.stdout)


def run_hook(
    db: Session,
    *,
    job: TestJob,
    control: VMNodeRuntime,
    directory: str,
    script_name: str,
    phase: str,
    error_code: str = "hook_failed",
    cancel_event: threading.Event | None = None,
) -> None:
    """跑环境 hook 脚本(pre_env/rerun_env/post_env)。cancel_event 命中或
    `run_control_command` 因 kill 返回 cancelled=True → 抛 job_cancelled,
    取消不再需要等各步骤自然 timeout 结束。
    """
    record_test_job_event(db, job=job, phase=phase, message=f"执行 {script_name}")
    db.commit()

    # Stream stdout line-by-line so KRONOS_PROGRESS: markers emitted by the
    # pre/post_env script become visible task_events in real time (not just at
    # the end). Lets users see which step a long pre_env (e.g. docker install)
    # is on / where it hangs. Non-marker lines are ignored.
    def _on_line(line: str) -> None:  # noqa: ANN001
        marker = "KRONOS_PROGRESS:"
        if line.startswith(marker):
            step = line[len(marker):].strip()
            if step:
                record_test_job_event(db, job=job, phase="env_progress", message=step)
                db.commit()

    result = run_control_command(
        control=control,
        script=(
            f"set -a && source {shlex.quote(directory)}/kronos.env && set +a && "
            f"bash {shlex.quote(directory)}/{script_name}"
        ),
        timeout_seconds=job_step_timeout(job, HOOK_TIMEOUT_SECONDS),
        on_line=_on_line,
        cancel_event=cancel_event,
    )
    if result.cancelled:
        _raise_cancelled()
    require_success(
        db,
        job=job,
        phase=f"{phase}_failed",
        message=f"{script_name} 执行失败",
        result=result,
        error_code=error_code,
    )
    record_test_job_event(db, job=job, phase=f"{phase}_done", message=f"{script_name} 执行完成")


def mark_case_execution_error(
    db: Session,
    *,
    job: TestJob,
    case_run: TestCaseRun,
    detail: str,
    error_code: str = "remote_command_failed",
) -> None:
    """把用例标 error 并记 case_error 事件。用于 SSH/挂死等链路异常，
    与用例本身失败(failed)区分，便于后续重跑策略。
    """
    case_run.status = TestCaseRunStatus.ERROR.value
    case_run.completed_at = utc_now()
    record_test_job_event(
        db,
        job=job,
        phase="case_error",
        message=f"用例执行链路异常 {case_run.suite_name}/{case_run.case_name}: {detail}",
        level="error",
        error_code=error_code,
    )
    db.commit()


class _HeartbeatStats:
    """心跳探活失败模式统计（ADR 0042）：判挂死时把传输层特征写进错误详情。

    分桶语义（与传输层事实对齐，供人工定界，不参与自动判定）：
    - 失联：连接阶段即超时/无路由（SSH 内层 ConnectTimeout 先于进程超时，
      表现为 exit 255 + "Connection timed out"）——整机失联嫌疑最大；
    - 超时：进程级超时（TCP 已建立、echo 卡死到 30s）——OS 活着但重度受阻；
    - 拒绝/断连：sshd 层问题，OS 与网络层明显存活。
    """

    _MODES = ("失联", "超时", "拒绝", "断连", "其他")

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.last_error: str = ""

    def record_result(self, result: RemoteCommandResult) -> None:
        if result.timed_out:
            mode = "超时"
        elif result.returncode == 255:
            text = f"{result.stderr}\n{result.stdout}"
            if (
                "Connection reset" in text
                or "Connection closed" in text
                or "banner exchange" in text
            ):
                # banner/reset/closed 说明 TCP 已通且对端有响应，先于失联判定。
                mode = "断连"
            elif "Connection refused" in text:
                mode = "拒绝"
            elif "Connection timed out" in text or "No route to host" in text:
                mode = "失联"
            else:
                mode = "其他"
        else:
            mode = "其他"
        self.counts[mode] = self.counts.get(mode, 0) + 1
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            self.last_error = detail.splitlines()[-1][:200]

    def record_exception(self) -> None:
        # check_fn 自身抛错(如 worker 缺 sshpass)拿不到传输层特征，归入其他。
        self.counts["其他"] = self.counts.get("其他", 0) + 1

    def summary(self) -> str:
        if not self.counts:
            return ""
        parts = [f"{mode}×{self.counts[mode]}" for mode in self._MODES if mode in self.counts]
        text = "：" + "，".join(parts)
        if self.last_error:
            text += f"；末次错误：{self.last_error}"
        return text


def _ssh_alive(control: VMNodeRuntime, stats: _HeartbeatStats | None = None) -> bool:
    try:
        result = run_ssh_command(
            host=control.ip,
            username=control.username,
            password=control.password,
            command="echo ok",
            timeout_seconds=HEARTBEAT_TIMEOUT_SECONDS,
            # 测试机每轮 PXE 重装都会轮换 host key，known_hosts 里的旧 key
            # 会让 accept-new 在 preauth 秒断，心跳三连失败误判 vm_hang。
            # 与全链路其他测试机连接一致，探活不校验 host key。
            verify_host_key=False,
        )
    except Exception:  # noqa: BLE001
        logger.debug("ssh liveness check failed", exc_info=True)
        if stats is not None:
            stats.record_exception()
        return False
    if result.returncode == 0:
        return True
    if stats is not None:
        stats.record_result(result)
    return False


def ssh_connect_refused(control: VMNodeRuntime) -> bool:
    """用例间探针（ADR 0046 修订，job 10235）：SSH 是否"连接拒绝"。

    只认 Connection refused——sshd 挂了但 OS/网络活着的确定签名
    （crypto-policies 类用例触发 systemd start-limit 杀 sshd 的特征）；
    超时/失联/进程超时返回 False：机器状态未知时交给既有挂死链路，
    不做恢复（误恢复代价是白硬复位一次）。
    """
    try:
        result = run_ssh_command(
            host=control.ip,
            username=control.username,
            password=control.password,
            command="echo ok",
            timeout_seconds=HEARTBEAT_TIMEOUT_SECONDS,
            # 与心跳探活一致：测试机 host key 每轮轮换，不校验。
            verify_host_key=False,
        )
    except Exception:  # noqa: BLE001
        logger.debug("ssh refused probe failed", exc_info=True)
        return False
    if result.returncode == 0 or result.timed_out:
        return False
    # 与 _HeartbeatStats 的"拒绝"分类同一签名（exit 255 + refused）。
    text = f"{result.stderr}\n{result.stdout}"
    return result.returncode == 255 and "Connection refused" in text


def sync_vm_disks(control: VMNodeRuntime) -> None:
    """强制刷盘（ADR 0046 修订二，job 10238）：收敛硬复位的页缓存丢失面。

    virsh destroy 等价拔电，复位前未落盘的页缓存写回会丢（ext4 延迟分配：
    mugen env.json 与已通过用例的日志/results 全 0 字节，重启后 read_conf
    解析空 JSON 崩溃，后续用例全失败、keep_env 复用被投毒）。环境就绪后
    与每个用例正常返回后各 sync 一次，丢失面收敛到杀手用例自身（sshd
    已死无从 sync，由 console 取证覆盖）。契约：绝不抛异常——SSH 已死是
    预期场景，失败静默，下轮探针恢复接管。
    """
    try:
        run_control_command(
            control=control,
            script="sync",
            timeout_seconds=SYNC_TIMEOUT_SECONDS,
        )
    except Exception:  # noqa: BLE001
        logger.debug("best-effort sync failed", exc_info=True)


def vm_host_channel(db: Session, control: VMNodeRuntime) -> tuple[str, str, str] | None:
    """VM 宿主机带外通道：(host_ip, vm_name, ssh_key)；物理机/无宿主/未配置返回 None。

    宿主信息在 virtual_spec 上（ADR 0002 拆表），不在 Resource 主表上；
    与 console 取证共用同一 SSH key（vm_host_ssh_key_path），不新增凭据。
    """
    resource = getattr(control, "resource", None)
    if resource is None:
        return None
    if getattr(resource, "physical_spec", None) is not None:
        return None
    virtual = getattr(resource, "virtual_spec", None)
    host_id = getattr(virtual, "host_resource_id", None) if virtual is not None else None
    if not host_id:
        return None
    host = db.get(Resource, host_id)
    vm_name = getattr(virtual, "vm_name", None)
    ssh_key = get_settings().vm_host_ssh_key_path or ""
    if host is None or not host.primary_ip:
        return None
    if not vm_name or not ssh_key:
        return None
    return host.primary_ip, vm_name, ssh_key


def _capture_and_store_console(
    db: Session, *, job: TestJob, control: VMNodeRuntime, case_run: TestCaseRun
) -> None:
    """挂死时抓诊断存 artifact：VM 走宿主机 virsh console（console_diagnostic），
    物理机走 BMC SEL/电源/传感器（bmc_diagnostic，ADR 0032 延后项的落地）。
    """
    channel = vm_host_channel(db, control)
    if channel is None:
        _capture_and_store_bmc_diagnostics(db, job=job, control=control, case_run=case_run)
        return
    host_ip, vm_name, ssh_key = channel
    try:
        output = capture_vm_console_output(
            host_ip=host_ip, vm_name=vm_name, ssh_key_path=ssh_key
        )
    except Exception:  # noqa: BLE001
        logger.debug("console capture failed", exc_info=True)
        output = "failed to capture console output"
    try:
        collector = LogCollector(base_dir=get_settings().pipeline_log_dir)
        collector.store_artifact(
            db=db,
            storage_scope=f"job-{job.id}",
            job_id=job.id,
            module="hang",
            arch=job.arch,
            artifact_type="console_diagnostic",
            artifact_name=f"console-{case_run.suite_name}-{case_run.case_name}.log",
            content=output,
        )
        db.commit()
    except Exception:  # noqa: BLE001
        # 取证落盘失败不能拖垮挂死主流程：case 还要标 ERROR 并抛 EnvSetHangError。
        logger.debug("console diagnostic artifact store failed", exc_info=True)
        db.rollback()


def _capture_and_store_bmc_diagnostics(
    db: Session, *, job: TestJob, control: VMNodeRuntime, case_run: TestCaseRun
) -> None:
    """物理机挂死取证：BMC 独立于被测 OS，整机挂死仍可读 SEL/电源/传感器。

    凭据走 physical_spec 的应用层加密密文；best-effort——BMC 不可达只记
    debug 日志，不阻断挂死主流程，也绝不据此自动重启物理机。
    """
    physical = getattr(control.resource, "physical_spec", None)
    if physical is None or not physical.bmc_ip or not physical.bmc_username:
        return
    try:
        password = decrypt_secret(physical.bmc_password_ciphertext or "")
    except Exception:  # noqa: BLE001
        logger.debug("bmc credential decrypt failed", exc_info=True)
        return
    if not password:
        return
    try:
        output = capture_bmc_diagnostics(
            bmc_ip=physical.bmc_ip,
            username=physical.bmc_username,
            password=password,
        )
    except Exception:  # noqa: BLE001
        logger.debug("bmc diagnostics capture failed", exc_info=True)
        output = "failed to capture BMC diagnostics"
    try:
        collector = LogCollector(base_dir=get_settings().pipeline_log_dir)
        collector.store_artifact(
            db=db,
            storage_scope=f"job-{job.id}",
            job_id=job.id,
            module="hang",
            arch=job.arch,
            artifact_type="bmc_diagnostic",
            artifact_name=f"bmc-{case_run.suite_name}-{case_run.case_name}.log",
            content=output,
        )
        db.commit()
    except Exception:  # noqa: BLE001
        # 取证落盘失败不能拖垮挂死主流程：case 还要标 ERROR 并抛 EnvSetHangError。
        logger.debug("bmc diagnostic artifact store failed", exc_info=True)
        db.rollback()


class _BmcHangGate:
    """BMC 电源确认门：为 HangDetector 提供带外三态确认与观察模式回调。

    confirm() 三态：True=电源开启；False=电源关闭(锚定断电宽限)；
    None=查询失败(不下结论)。判死只信电源状态，SEL 不参与判定
    (ADR 0044 修订，job 10232 实证 BMC 时钟与事件流不可信)。
    回调在检测器线程执行，事件与取证产物一律走独立数据库会话，
    全部 best-effort，绝不阻断心跳循环。
    """

    def __init__(
        self,
        *,
        job: TestJob,
        case_run: TestCaseRun,
        bmc_ip: str,
        username: str,
        password: str,
    ) -> None:
        self._job_id = job.id
        self._arch = job.arch
        self._suite = case_run.suite_name
        self._case = case_run.case_name
        self._bmc_ip = bmc_ip
        self._username = username
        self._password = password
        self._watch_started_monotonic: float | None = None
        self._off_reported = False
        self.last_verdict: bool | None = None
        # 判死 detail 的关机证据文案：区分 BMC（电源）与宿主机（domstate）来源。
        self.off_evidence = "BMC 报告电源断开"

    def confirm(self) -> bool | None:
        try:
            self.last_verdict = bmc_power_on(
                bmc_ip=self._bmc_ip,
                username=self._username,
                password=self._password,
            )
        except Exception:  # noqa: BLE001
            logger.debug("bmc confirm probe failed", exc_info=True)
            self.last_verdict = None
            return self.last_verdict
        # 观察中首次读到电源 off：留痕宽限规则（首查 off 已含在 watch-entry 事件里）。
        if (
            self.last_verdict is False
            and self._watch_started_monotonic is not None
            and not self._off_reported
        ):
            self._off_reported = True
            _record_hang_watch_event(
                self._job_id,
                phase="hang_watch",
                level="warning",
                message=(
                    f"BMC（{self._bmc_ip}）观察到电源断开，"
                    f"{int(WATCH_POWER_OFF_DEADLINE_SECONDS // 60)} 分钟内 SSH"
                    f" 未恢复将判死，用例 {self._suite}/{self._case}"
                ),
            )
        return self.last_verdict

    def on_watch_start(self) -> None:
        self._watch_started_monotonic = time.monotonic()
        if self.last_verdict is True:
            verdict_text = "电源开启"
        elif self.last_verdict is False:
            verdict_text = "电源断开"
        else:
            verdict_text = "查询失败"
        _record_hang_watch_event(
            self._job_id,
            phase="hang_watch",
            level="warning",
            message=(
                f"SSH 心跳连续失败已达判定阈值，BMC 检查（{self._bmc_ip}）"
                f"{verdict_text}，进入观察模式暂缓判死"
                f"（上限 {int(WATCH_TIMEOUT_SECONDS // 60)} 分钟，断电宽限"
                f" {int(WATCH_POWER_OFF_DEADLINE_SECONDS // 60)} 分钟），"
                f"用例 {self._suite}/{self._case}"
            ),
        )
        self._store_artifact(f"bmc-{self._suite}-{self._case}-watch-entry.log")

    def on_recovered(self) -> None:
        watched_seconds = 0
        if self._watch_started_monotonic is not None:
            watched_seconds = int(time.monotonic() - self._watch_started_monotonic)
        # 复位观察态：off 事件守卫(_watch_started_monotonic)必须严格等于
        # "观察中"，多 episode 时阈值首查 off 只由 watch-entry 文案报告一次。
        self._watch_started_monotonic = None
        _record_hang_watch_event(
            self._job_id,
            phase="hang_recovered",
            level="info",
            message=(
                f"SSH 心跳恢复，退出观察模式继续执行（观察 {watched_seconds} 秒），"
                f"用例 {self._suite}/{self._case}"
            ),
        )
        self._store_artifact(f"bmc-{self._suite}-{self._case}-watch-recovered.log")

    def _store_artifact(self, artifact_name: str) -> None:
        try:
            output = capture_bmc_diagnostics(
                bmc_ip=self._bmc_ip, username=self._username, password=self._password
            )
        except Exception:  # noqa: BLE001
            logger.debug("bmc watch capture failed", exc_info=True)
            output = "failed to capture BMC diagnostics"
        _store_hang_watch_artifact(
            job_id=self._job_id,
            arch=self._arch,
            artifact_name=artifact_name,
            content=output,
            artifact_type="bmc_diagnostic",
        )


def _record_hang_watch_event(job_id: int, *, phase: str, message: str, level: str) -> None:
    """观察模式事件落库（检测器线程调用）：独立会话避免与主线程共享 db。"""
    try:
        with SessionLocal() as session:
            job = session.get(TestJob, job_id)
            if job is not None:
                record_test_job_event(
                    session, job=job, phase=phase, message=message, level=level
                )
            session.commit()
    except Exception:  # noqa: BLE001
        logger.debug("hang watch event record failed", exc_info=True)


def _store_hang_watch_artifact(
    *,
    job_id: int,
    arch: str,
    artifact_name: str,
    content: str,
    artifact_type: str,
) -> None:
    """观察/恢复取证产物落库（检测器线程调用）：独立会话，失败只记日志。"""
    try:
        with SessionLocal() as session:
            collector = LogCollector(base_dir=get_settings().pipeline_log_dir)
            collector.store_artifact(
                db=session,
                storage_scope=f"job-{job_id}",
                job_id=job_id,
                module="hang",
                arch=arch,
                artifact_type=artifact_type,
                artifact_name=artifact_name,
                content=content,
            )
            session.commit()
    except Exception:  # noqa: BLE001
        logger.debug("hang watch artifact store failed", exc_info=True)


def _build_bmc_hang_gate(
    job: TestJob, control: VMNodeRuntime, case_run: TestCaseRun
) -> _BmcHangGate | None:
    """有 BMC 配置的物理机返回确认门；VM、无 BMC 或凭据不可用返回 None。

    None 表示沿用原判定（阈值+复核即判死），见 ADR 0044。
    """
    resource = getattr(control, "resource", None)
    physical = getattr(resource, "physical_spec", None)
    if physical is None or not physical.bmc_ip or not physical.bmc_username:
        return None
    try:
        password = decrypt_secret(physical.bmc_password_ciphertext or "")
    except Exception:  # noqa: BLE001
        logger.debug("bmc credential decrypt failed", exc_info=True)
        return None
    if not password:
        return None
    return _BmcHangGate(
        job=job,
        case_run=case_run,
        bmc_ip=physical.bmc_ip,
        username=physical.bmc_username,
        password=password,
    )


class _VmHangGate:
    """宿主机 domstate 确认门（ADR 0046）：VM 的带外三态确认与观察模式回调。

    confirm() 三态：True=domstate 活态(running/paused 等)；False=关机/崩溃
    态(锚定关机宽限，覆盖 on_crash=restart 自动拉起)；None=宿主机查询失败
    (不下结论)。回调在检测器线程执行，事件与取证产物一律走独立数据库
    会话，全部 best-effort，绝不阻断心跳循环。
    """

    def __init__(
        self,
        *,
        job: TestJob,
        case_run: TestCaseRun,
        host_ip: str,
        vm_name: str,
        ssh_key_path: str,
    ) -> None:
        self._job_id = job.id
        self._arch = job.arch
        self._suite = case_run.suite_name
        self._case = case_run.case_name
        self._host_ip = host_ip
        self._vm_name = vm_name
        self._ssh_key_path = ssh_key_path
        self._watch_started_monotonic: float | None = None
        self._off_reported = False
        self.last_verdict: bool | None = None
        self.off_evidence = f"宿主机报告 VM {vm_name} 已关机"

    def confirm(self) -> bool | None:
        try:
            self.last_verdict = vm_domstate_alive(
                host_ip=self._host_ip,
                vm_name=self._vm_name,
                ssh_key_path=self._ssh_key_path,
            )
        except Exception:  # noqa: BLE001
            logger.debug("vm domstate confirm probe failed", exc_info=True)
            self.last_verdict = None
            return self.last_verdict
        # 观察中首次读到关机态：留痕宽限规则（首查 off 已含在 watch-entry 事件里）。
        if (
            self.last_verdict is False
            and self._watch_started_monotonic is not None
            and not self._off_reported
        ):
            self._off_reported = True
            _record_hang_watch_event(
                self._job_id,
                phase="hang_watch",
                level="warning",
                message=(
                    f"宿主机（{self._host_ip}）观察到 VM {self._vm_name} 已关机，"
                    f"{int(WATCH_POWER_OFF_DEADLINE_SECONDS // 60)} 分钟内 SSH"
                    f" 未恢复将判死，用例 {self._suite}/{self._case}"
                ),
            )
        return self.last_verdict

    def on_watch_start(self) -> None:
        self._watch_started_monotonic = time.monotonic()
        if self.last_verdict is True:
            verdict_text = "VM 运行中"
        elif self.last_verdict is False:
            verdict_text = "VM 已关机"
        else:
            verdict_text = "查询失败"
        _record_hang_watch_event(
            self._job_id,
            phase="hang_watch",
            level="warning",
            message=(
                f"SSH 心跳连续失败已达判定阈值，宿主机 virsh 检查"
                f"（{self._vm_name}@{self._host_ip}）{verdict_text}，"
                f"进入观察模式暂缓判死"
                f"（上限 {int(WATCH_TIMEOUT_SECONDS // 60)} 分钟，关机宽限"
                f" {int(WATCH_POWER_OFF_DEADLINE_SECONDS // 60)} 分钟），"
                f"用例 {self._suite}/{self._case}"
            ),
        )
        self._store_artifact(f"console-{self._suite}-{self._case}-watch-entry.log")

    def on_recovered(self) -> None:
        watched_seconds = 0
        if self._watch_started_monotonic is not None:
            watched_seconds = int(time.monotonic() - self._watch_started_monotonic)
        self._watch_started_monotonic = None
        _record_hang_watch_event(
            self._job_id,
            phase="hang_recovered",
            level="info",
            message=(
                f"SSH 心跳恢复，退出观察模式继续执行（观察 {watched_seconds} 秒），"
                f"用例 {self._suite}/{self._case}"
            ),
        )
        # 恢复不另存产物：判死路径已由 _capture_and_store_console 覆盖。

    def _store_artifact(self, artifact_name: str) -> None:
        try:
            output = capture_vm_console_output(
                host_ip=self._host_ip,
                vm_name=self._vm_name,
                ssh_key_path=self._ssh_key_path,
            )
        except Exception:  # noqa: BLE001
            logger.debug("vm watch capture failed", exc_info=True)
            output = "failed to capture console output"
        _store_hang_watch_artifact(
            job_id=self._job_id,
            arch=self._arch,
            artifact_name=artifact_name,
            content=output,
            artifact_type="console_diagnostic",
        )


def _build_vm_hang_gate(
    db: Session, job: TestJob, control: VMNodeRuntime, case_run: TestCaseRun
) -> _VmHangGate | None:
    """有宿主机通道的 VM 返回 domstate 确认门；物理机/无通道/未配置返回 None。

    None 表示沿用原判定（阈值+复核即判死），见 ADR 0044/0046。
    """
    channel = vm_host_channel(db, control)
    if channel is None:
        return None
    host_ip, vm_name, ssh_key = channel
    return _VmHangGate(
        job=job,
        case_run=case_run,
        host_ip=host_ip,
        vm_name=vm_name,
        ssh_key_path=ssh_key,
    )


def try_vm_recovery(
    db: Session,
    *,
    job: TestJob,
    control: VMNodeRuntime,
    cancel_event: threading.Event | None,
    trigger: str = "breaker",
) -> bool:
    """宿主机硬复位恢复（ADR 0046）：destroy+start 后轮询 SSH 就绪。

    trigger="breaker" 为熔断点触发（原版），"probe" 为用例间/post_env 前
    探针触发（连接拒绝签名）。每环境集一次的预算由调用方持有（按尝试计）；
    成功 True（调用方清零连击计数继续剩余用例），无通道/复位失败/SSH 未回
    False（维持原判定）。事件 vm_recovery_started/vm_recovered/
    vm_recovery_failed 留痕，复位前抓 console 存肇事现场。
    """
    channel = vm_host_channel(db, control)
    if channel is None:
        return False
    host_ip, vm_name, ssh_key = channel

    def _record(phase: str, message: str, *, level: str = "warning") -> None:
        record_test_job_event(db, job=job, phase=phase, message=message, level=level)
        db.commit()

    if trigger == "probe":
        _record(
            "vm_recovery_started",
            f"用例间探活发现 SSH 连接拒绝（sshd 不可用），"
            f"宿主机硬复位 {vm_name}（{host_ip}）尝试恢复",
        )
    else:
        _record(
            "vm_recovery_started",
            f"连续用例 SSH 失败触发熔断，宿主机硬复位 {vm_name}（{host_ip}）尝试恢复",
        )
    # 复位前取证：这是肇事现场（防火墙残留/isolate 僵尸态的 console 输出）。
    try:
        console = capture_vm_console_output(
            host_ip=host_ip, vm_name=vm_name, ssh_key_path=ssh_key
        )
    except Exception:  # noqa: BLE001
        logger.debug("recovery console capture failed", exc_info=True)
        console = "failed to capture console output"
    _store_hang_watch_artifact(
        job_id=job.id,
        arch=job.arch,
        artifact_name="console-recovery.log",
        content=console,
        artifact_type="console_diagnostic",
    )

    if not vm_hard_reset(host_ip=host_ip, vm_name=vm_name, ssh_key_path=ssh_key):
        _record(
            "vm_recovery_failed",
            f"宿主机硬复位失败（{vm_name}@{host_ip}），剩余用例按熔断处理",
        )
        return False
    wait_budget = remaining_test_job_seconds(job, maximum=SSH_READY_TIMEOUT_SECONDS)
    if wait_budget <= 0:
        _record(
            "vm_recovery_failed",
            f"宿主机硬复位完成但任务剩余时间不足（{vm_name}@{host_ip}），"
            f"剩余用例按熔断处理",
        )
        return False

    deadline = time.monotonic() + wait_budget
    while True:
        if _ssh_alive(control):
            _record(
                "vm_recovered",
                f"宿主机硬复位后 SSH 恢复，继续执行剩余用例（{vm_name}@{host_ip}）",
                level="info",
            )
            return True
        if time.monotonic() >= deadline:
            break
        if cancel_event is not None:
            cancel_event.wait(SSH_READY_RETRY_INTERVAL_SECONDS)
            if cancel_event.is_set():
                break
        else:
            time.sleep(SSH_READY_RETRY_INTERVAL_SECONDS)
    _record(
        "vm_recovery_failed",
        f"宿主机硬复位后 SSH 未恢复（{vm_name}@{host_ip}），剩余用例按熔断处理",
    )
    return False


def _ssh_read_file(control: VMNodeRuntime, path: str) -> str:
    result = run_ssh_command(
        host=control.ip,
        username=control.username,
        password=control.password,
        command=f"cat {shlex.quote(path)} 2>/dev/null",
        timeout_seconds=120,
    )
    return result.stdout or ""


def _ssh_results_listing(control: VMNodeRuntime, suite_name: str) -> dict:
    """读 mugen results/<suite>/{succeed,failed,skipped} 目录列表。best-effort。"""
    listing: dict[str, list[str]] = {"succeed": [], "failed": [], "skipped": []}
    for bucket in listing:
        result = run_ssh_command(
            host=control.ip,
            username=control.username,
            password=control.password,
            command=f"ls -1 /tmp/mugen/results/{shlex.quote(suite_name)}/{bucket}/ 2>/dev/null",
            timeout_seconds=30,
        )
        if result.returncode == 0 and result.stdout:
            listing[bucket] = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return listing


def _parse_and_store_subcases(
    db: Session, *, job: TestJob, control: VMNodeRuntime, case_run: TestCaseRun
) -> None:
    """run_case 正常结束后按 job.result_parser 解析子用例写 TestCaseRunDetail。best-effort。"""
    parser = (getattr(job, "result_parser", None) or "").strip()
    if not parser or parser == "none":
        return
    sub_results: list[SubTestResult] = []
    try:
        if parser == "ltp":
            text = _ssh_read_file(control, "/tmp/mugen/logs/ltp.log")
            sub_results = parse_ltp_log(text)
        elif parser == "pkgmanage":
            text = _ssh_read_file(control, "/tmp/module-logs/pkgmanage-details.log")
            sub_results = parse_pkgmanage_log(text)
        elif parser in {"pkgcmd", "pkgserver", "pkgunion", "mugen_results", "docker"}:
            listing = _ssh_results_listing(control, case_run.suite_name)
            sub_results = parse_mugen_results_dir(listing)
    except Exception:  # noqa: BLE001
        logger.debug("subcase parse/store failed", exc_info=True)
        return
    for r in sub_results:
        db.add(
            TestCaseRunDetail(
                case_run_id=case_run.id,
                sub_test_name=r.sub_test_name,
                status=r.status,
                detail={},
            )
        )
    db.commit()


# 注意：模板经 .format(module=...) 渲染，除 {module} 外的 shell 花括号必须
# 双写转义（{{...}}），否则 str.format 抛 KeyError 被 best-effort 吞掉，
# 逐 case 收集静默失效（1a92de8 引入时的隐性 bug，修复于 pkgunion 接入时）。
_PER_CASE_COLLECT_SCRIPT = r"""OET_PATH="/opt/mugen"
LOG_FILE="/opt/{module}-logs/{module}.log"
mkdir -p "$(dirname "${{LOG_FILE}}")"
SUITE_DIR=$(ls -1 "${{OET_PATH}}/results/" 2>/dev/null | head -n 1)
if [ -z "${{SUITE_DIR}}" ]; then exit 0; fi
R="${{OET_PATH}}/results/${{SUITE_DIR}}"
SUCCEED=0; FAILED=0; SKIPPED=0; FAILED_CASES=""
[ -d "${{R}}/succeed" ] && SUCCEED=$(ls -1 "${{R}}/succeed" 2>/dev/null | wc -l)
[ -d "${{R}}/failed" ] && FAILED=$(ls -1 "${{R}}/failed" 2>/dev/null | wc -l)
[ -d "${{R}}/skipped" ] && SKIPPED=$(ls -1 "${{R}}/skipped" 2>/dev/null | wc -l)
[ ${{FAILED}} -gt 0 ] && FAILED_CASES=$(ls -1 "${{R}}/failed" 2>/dev/null | xargs)
{{
    echo "${{SUITE_DIR}} 用例已执行"
    echo "成功 ${{SUCCEED}} 个"
    echo "跳过 ${{SKIPPED}} 个"
    echo "失败 ${{FAILED}} 个"
    [ -n "${{FAILED_CASES}}" ] && echo "failed：${{FAILED_CASES}}"
    echo "-----------------------------"
}} >> "${{LOG_FILE}}"
"""


def _per_case_collect_log(
    db: Session, *, job: TestJob, control: VMNodeRuntime, case_run: TestCaseRun
) -> None:
    """每个 case 结束后收集 mugen 结果并追加到 module 日志(逐 case 收集)。

    仅对 result_parser 为 pkgcmd / pkgserver / pkgunion 的 module 生效——它们需要逐 case
    收集，因为 mugen.sh 会在多次运行间覆盖 results 目录。best-effort：收集
    失败不让 case 失败。
    """
    parser = (getattr(job, "result_parser", None) or "").strip()
    if parser not in ("pkgcmd", "pkgserver", "pkgunion"):
        return
    try:
        script = _PER_CASE_COLLECT_SCRIPT.format(module=parser)
        run_control_command(
            control=control,
            script=script,
            timeout_seconds=60,
        )
    except Exception:  # noqa: BLE001
        logger.debug("per-case log collect failed", exc_info=True)


def _stop_remote_mugen(control: VMNodeRuntime) -> None:
    """尽力停止当前控制节点上的 Mugen，避免本地 SSH 被取消后远端继续运行。"""
    try:
        run_control_command(
            control=control,
            script="pkill -f mugen.sh || true",
            timeout_seconds=30,
        )
    except Exception:  # noqa: BLE001
        logger.debug("failed to stop remote mugen after cancellation", exc_info=True)


# 逐 case 上传（ADR 0048）相关常量：results 桶名与 scp 上限秒数。
_RESULT_BUCKETS = ("succeed", "failed", "skipped")
_CASE_UPLOAD_SCP_TIMEOUT_SECONDS = 300


def _case_upload_pieces(case_run: TestCaseRun) -> list[tuple[str, str]]:
    """返回 [(artifact_dir, 相对落位路径)]：logs 目录 + 三个 results 桶。"""
    rel = f"{case_run.suite_name}/{case_run.case_name}"
    return [
        ("logs", f"logs/{rel}"),
        *[("results", f"results/{case_run.suite_name}/{bucket}/{case_run.case_name}")
          for bucket in _RESULT_BUCKETS],
    ]


def _docker_stage_case_outputs(
    job: TestJob, control: VMNodeRuntime, case_run: TestCaseRun
) -> str:
    """docker 模块：把容器内该 case 的 logs 与 results 桶 docker cp 到宿主机
    staging（目录结构与最终落位一致），返回 staging 路径。
    """
    suite = shlex.quote(case_run.suite_name)
    case = shlex.quote(case_run.case_name)
    stage = f"/tmp/kronos-case-upload/{case_run.id}"
    dirs = [f"{stage}/logs/{suite}"]
    cmds = [f"rm -rf {shlex.quote(stage)}"]
    for bucket in _RESULT_BUCKETS:
        dirs.append(f"{stage}/results/{suite}/{bucket}")
    cmds.append(f"mkdir -p {' '.join(dirs)}")
    cmds.append(
        f"docker cp openEuler_test:/home/mugen/logs/{suite}/{case} "
        f"{stage}/logs/{suite}/ 2>/dev/null || true"
    )
    for bucket in _RESULT_BUCKETS:
        cmds.append(
            f"docker cp openEuler_test:/home/mugen/results/{suite}/{bucket}/{case} "
            f"{stage}/results/{suite}/{bucket}/ 2>/dev/null || true"
        )
    run_control_command(
        control=control,
        script="\n".join(cmds),
        timeout_seconds=job_step_timeout(job, 120),
    )
    return stage


def _existing_remote_paths(control: VMNodeRuntime, paths: list[str]) -> set[str]:
    """返回 paths 中在控制节点上真实存在的目录。

    mugen 逐 case 覆盖 results 目录，case 只落在恰好一个 outcome 桶里，缺失桶
    的 scp 必然失败——必须先探测区分"远端缺失"（跳过）与"传输失败"（放弃），
    否则每个 case 都会被缺失桶误判为传输失败。探测失败按全部缺失处理，交由
    任务结束补拉兜底。
    """
    if not paths:
        return set()
    script = "\n".join(
        f"[ -d {shlex.quote(path)} ] && echo {shlex.quote(path)}" for path in paths
    )
    try:
        result = run_control_command(
            control=control, script=script, timeout_seconds=30
        )
    except Exception:  # noqa: BLE001
        logger.debug("remote piece path probe failed", exc_info=True)
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _cleanup_remote_stage(control: VMNodeRuntime, stage: str) -> None:
    """尽力清理测试机上的 docker staging 目录，keep_env 机器长期复用不残留。"""
    try:
        run_control_command(
            control=control,
            script=f"rm -rf {shlex.quote(stage)}",
            timeout_seconds=30,
        )
    except Exception:  # noqa: BLE001
        logger.debug("failed to clean remote case staging", exc_info=True)


def _ensure_case_dir_artifact(
    db: Session,
    *,
    job: TestJob,
    run_id: str,
    module_name: str,
    arch: str,
    artifact_name: str,
    local_dir: Path,
) -> None:
    """幂等登记共享目录 artifact（logs/results），已存在则跳过。"""
    existing = db.execute(
        select(TestLogArtifact).where(
            TestLogArtifact.job_id == job.id,
            TestLogArtifact.artifact_name == artifact_name,
        )
    ).scalars().first()
    if existing is not None:
        return
    LogCollector(base_dir=get_settings().pipeline_log_dir).store_dir_artifact(
        db=db,
        pipeline_run_id=run_id,
        job_id=job.id,
        module=module_name,
        arch=arch,
        artifact_type="pkg_folder",
        artifact_name=artifact_name,
        local_dir=str(local_dir),
    )


def upload_case_logs(
    db: Session,
    *,
    job: TestJob,
    control: VMNodeRuntime,
    case_run: TestCaseRun,
) -> None:
    """逐 case 日志原子上传（ADR 0048）。

    case 正常收敛后由 run_case 内联调用：把该 case 的 mugen 执行日志目录与
    results 桶目录上传到服务端共享目录 artifact 的对应子路径。各 piece 先拉到
    独立暂存目录，全部成功后统一 rename 落位——单 case 要么完整可见要么不存在；
    任一 piece 失败则整 case 放弃（不留部分落位、不留可复用残留），由任务结束
    时的补漏式自汇集兜底。无上下文（非 pipeline 入口）直接跳过。best-effort：
    失败记 debug 日志，绝不影响 case 结果。幂等：目标 case 目录已存在视为已
    上传（rerun 归档会先移走旧输出，正常流程不会重复落位）。
    """
    tmp_root: Path | None = None
    try:
        job_id = getattr(job, "id", None)
        ctx = get_case_log_context(job_id) if job_id is not None else None
        if ctx is None:
            return
        env_set = db.get(TestEnvSet, case_run.env_set_id) if case_run.env_set_id else None
        env_index = env_set.set_index if env_set is not None else 1
        multi_env = len(job.env_sets) > 1
        base = (
            Path(get_settings().pipeline_log_dir)
            / ctx.run_id
            / ctx.module_name
            / ctx.arch
            / ctx.run_job_id
        )
        if multi_env:
            base /= f"env-{env_index}"
        prefix = f"env{env_index}-" if multi_env else ""

        # 幂等门：logs 主内容已落位即视为该 case 已上传。
        if (base / "logs" / case_run.suite_name / case_run.case_name).exists():
            return

        tmp_root = base.parent / f".tmp-{case_run.id}"
        shutil.rmtree(tmp_root, ignore_errors=True)
        tmp_root.mkdir(parents=True, exist_ok=True)
        scp_timeout = job_step_timeout(job, _CASE_UPLOAD_SCP_TIMEOUT_SECONDS)

        docker = bool(
            getattr(job, "mugen_exec_command", None)
            and "openEuler_test" in job.mugen_exec_command
        )
        staged: list[tuple[str, str, Path]] = []
        if docker:
            stage = _docker_stage_case_outputs(job, control, case_run)
            try:
                scp_ok = scp_directory(
                    host=control.ip,
                    username=control.username,
                    password=control.password,
                    remote_path=stage,
                    local_dir=str(tmp_root),
                    timeout_seconds=scp_timeout,
                    verify_host_key=False,
                )
            finally:
                _cleanup_remote_stage(control, stage)
            if not scp_ok:
                return
            stage_local = tmp_root / case_run.id
            for artifact_dir, rel in _case_upload_pieces(case_run):
                target = base / rel
                if target.exists():
                    continue
                source = stage_local / rel
                if not source.exists():
                    continue
                staged.append((artifact_dir, rel, source))
        else:
            # 逐 piece 拉到独立暂存子目录：某 piece scp 失败不留部分内容，
            # 也不会被下一个 piece 的 scp 嵌套复用；全部成功后才统一落位。
            pieces = [
                (artifact_dir, rel)
                for artifact_dir, rel in _case_upload_pieces(case_run)
                if not (base / rel).exists()
            ]
            existing = _existing_remote_paths(
                control, [f"/opt/mugen/{rel}" for _artifact_dir, rel in pieces]
            )
            for index, (artifact_dir, rel) in enumerate(pieces):
                remote_path = f"/opt/mugen/{rel}"
                if remote_path not in existing:
                    continue
                piece_dir = tmp_root / f"piece-{index}"
                piece_dir.mkdir(parents=True, exist_ok=True)
                if not scp_directory(
                    host=control.ip,
                    username=control.username,
                    password=control.password,
                    remote_path=remote_path,
                    local_dir=str(piece_dir),
                    timeout_seconds=scp_timeout,
                    verify_host_key=False,
                ):
                    # 任一 piece 传输失败即放弃整 case（原子性），等待结束补拉兜底。
                    return
                source = piece_dir / case_run.case_name
                if not source.exists():
                    continue
                staged.append((artifact_dir, rel, source))

        # 统一落位：全部 piece 暂存完成后一次 rename，保证单 case 原子可见。
        # 注：rename 循环中途失败（同子树 rename 现实中几乎不发生）仍可能留下
        # 部分落位，幂等门以 logs 为准，缺口由结束补拉合并补齐。
        landed_dirs: set[str] = set()
        for artifact_dir, rel, source in staged:
            target = base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
            landed_dirs.add(artifact_dir)

        # 共享目录 artifact 幂等登记（与 _self_collect_logs 命名一致），
        # 仅登记实际有内容落位的目录。
        if "logs" in landed_dirs:
            _ensure_case_dir_artifact(
                db,
                job=job,
                run_id=ctx.run_id,
                module_name=ctx.module_name,
                arch=ctx.arch,
                artifact_name=f"{prefix}logs",
                local_dir=base / "logs",
            )
        if "results" in landed_dirs:
            _ensure_case_dir_artifact(
                db,
                job=job,
                run_id=ctx.run_id,
                module_name=ctx.module_name,
                arch=ctx.arch,
                artifact_name=f"{prefix}results",
                local_dir=base / "results",
            )
        if landed_dirs:
            db.commit()
    except Exception:  # noqa: BLE001
        logger.debug(
            "case log upload failed: job=%s case=%s",
            getattr(job, "id", None),
            getattr(case_run, "id", None),
            exc_info=True,
        )
        db.rollback()
    finally:
        if tmp_root is not None:
            shutil.rmtree(tmp_root, ignore_errors=True)


def _env_label(db: Session, case_run: TestCaseRun) -> str:
    """按 case_run 所属 env_set 的 env_type 返回 'VM' 或 '物理机'。"""
    env_set = db.get(TestEnvSet, case_run.env_set_id) if case_run.env_set_id else None
    if env_set and env_set.env_type == "physical":
        return "物理机"
    return "VM"


def run_case(
    db: Session,
    *,
    job: TestJob,
    control: VMNodeRuntime,
    case_run: TestCaseRun,
    cancel_check: Callable[[], bool] | None = None,
    cancel_event: threading.Event | None = None,
) -> None:
    """执行单条用例并写结果。

    流程：标 running→写当前 case 标识(挂死时对得上 console)→起 HangDetector
    心跳→跑 mugen.sh(或 mugen_exec_command)→据 exit code 定 passed/failed/
    timeout。mugen exit 0 不等于通过：还要查 results/skipped/ 判断是否被跳过。
    挂死(心跳连续失败)抓 console 存诊断产物并抛 EnvSetHangError。正常结束才
    解析子用例与按模块收集结果。所有步骤超时派生自 job 剩余时间。

    cancel_check 非空时启动并行取消检测线程：轮询 cancel_requested，命中后
    先 set job 级 cancel_event(触发所有 EnvSet 本地 SSH 秒级退出)，再新开 SSH
    执行 pkill -f mugen.sh。命令返回后按优先级分派:
    - DB 取消(`cancel_detected` 或 `cancel_check`) → 标 `not_executed` 并 return;
    - hang → 现有挂死路径;
    - `result.cancelled`+外部 event(Soft 或跨环境集取消) → 标 `not_executed`
      并抛 `job_cancelled`。
    """
    case_run.status = TestCaseRunStatus.RUNNING.value
    case_run.started_at = utc_now()
    env_label = _env_label(db, case_run)
    record_test_job_event(
        db,
        job=job,
        phase="case_started",
        message=f"开始执行 {case_run.suite_name}/{case_run.case_name} ({env_label} {control.ip})",
    )
    db.commit()

    # 写当前 case 标识，挂死时 console 输出能对上
    try:
        write_remote_file(
            host=control.ip,
            username=control.username,
            password=control.password,
            path="/tmp/kronos-current-case",
            content=f"{case_run.suite_name}/{case_run.case_name}",
            timeout_seconds=30,
            verify_host_key=False,
        )
    except Exception:  # noqa: BLE001
        logger.debug("remote marker write failed", exc_info=True)

    case_cancel_event = threading.Event()
    heartbeat_stats = _HeartbeatStats()
    # 有带外通道的机器挂死前先确认（观察模式）：物理机走 BMC 电源门（ADR 0044），
    # VM 走宿主机 domstate 门（ADR 0046）；无通道返回 None 走原判定。
    hang_gate = _build_bmc_hang_gate(job, control, case_run) or _build_vm_hang_gate(
        db, job, control, case_run
    )
    detector = HangDetector(
        check_fn=lambda: _ssh_alive(control, heartbeat_stats),
        on_hung=case_cancel_event.set,
        confirm_fn=hang_gate.confirm if hang_gate is not None else None,
        on_watch_start=hang_gate.on_watch_start if hang_gate is not None else None,
        on_recovered=hang_gate.on_recovered if hang_gate is not None else None,
    )
    detector.start()

    # 取消检测线程：周期性轮询 cancel_check；命中先 set cancel_event 让本地
    # run_process 秒级 kill(避免 12h 长命令自然 timeout),再发远程 pkill 释放资源。
    cancel_stop = threading.Event()
    cancel_detected = threading.Event()
    if cancel_check:

        def _cancel_watcher() -> None:
            while not cancel_stop.wait(15):
                if cancel_stop.is_set():
                    return
                try:
                    if cancel_check():
                        if cancel_event is not None:
                            cancel_event.set()
                        case_cancel_event.set()
                        _stop_remote_mugen(control)
                        cancel_detected.set()
                        cancel_stop.set()
                        return
                except Exception:  # noqa: BLE001
                    logger.debug("cancel watcher check failed", exc_info=True)

        threading.Thread(target=_cancel_watcher, daemon=True).start()

    hung = False
    try:
        script = (
            "cd /opt/mugen && "
            f"bash mugen.sh -f {shlex.quote(case_run.suite_name)} "
            f"-r {shlex.quote(case_run.case_name)} -x"
        )
        if getattr(job, "mugen_exec_command", None):
            script = job.mugen_exec_command.format(
                suite=shlex.quote(case_run.suite_name),
                case=shlex.quote(case_run.case_name),
            )
        try:
            command_timeout = job_step_timeout(job, CASE_COMMAND_TIMEOUT_SECONDS)
            result = run_control_command(
                control=control,
                script=script,
                timeout_seconds=command_timeout,
                cancel_event=case_cancel_event,
                cancel_events=(cancel_event,) if cancel_event is not None else (),
            )
        except TestJobExecutionError as exc:
            if cancel_detected.is_set():
                case_run.status = TestCaseRunStatus.NOT_EXECUTED.value
                case_run.completed_at = utc_now()
                db.commit()
                return
            mark_case_execution_error(
                db, job=job, case_run=case_run, detail=str(exc), error_code=exc.code
            )
            raise
        except RemoteCommandError as exc:
            if cancel_detected.is_set():
                case_run.status = TestCaseRunStatus.NOT_EXECUTED.value
                case_run.completed_at = utc_now()
                db.commit()
                return
            mark_case_execution_error(db, job=job, case_run=case_run, detail=str(exc))
            raise
    finally:
        if detector.is_hung():
            hung = True
        detector.stop()
        cancel_stop.set()

    # 命令返回后按优先级分派取消/挂死/超时。
    # 1) DB cancel → 保留原 not_executed 语义(用户主动放弃本 case)。
    if cancel_detected.is_set() or (cancel_check and cancel_check()):
        if not cancel_detected.is_set():
            # TestJob 级 watcher 可能已先杀掉本地 SSH；这里仍需停止远端 mugen.sh。
            _stop_remote_mugen(control)
        case_run.status = TestCaseRunStatus.NOT_EXECUTED.value
        case_run.completed_at = utc_now()
        record_test_job_event(
            db,
            job=job,
            phase="case_cancelled",
            message=f"用例因取消中断 {case_run.suite_name}/{case_run.case_name}",
        )
        db.commit()
        return

    # 2) 挂死 → 保留原 EnvSetHangError 路径。
    if hung:
        _capture_and_store_console(db, job=job, control=control, case_run=case_run)
        detail = f"VM/物理机挂死（心跳连续失败{heartbeat_stats.summary()}）"
        if getattr(detector, "bmc_declared", False) and hang_gate is not None:
            detail += (
                f"；{hang_gate.off_evidence}，"
                f"{int(WATCH_POWER_OFF_DEADLINE_SECONDS // 60)} 分钟内 SSH 未恢复"
            )
        elif getattr(detector, "watch_duration", None) is not None:
            detail += f"；观察期 {int(detector.watch_duration)} 秒未见恢复"
        mark_case_execution_error(
            db,
            job=job,
            case_run=case_run,
            detail=detail,
            error_code="vm_hang",
        )
        raise EnvSetHangError(f"VM 挂死 {case_run.suite_name}/{case_run.case_name}")

    # 3) 本地被 cancel_event 打断(如主线程 SoftTimeLimit 或兄弟 env_set 触发),
    #    与"用户通过 DB 主动取消"的语义一致 → 本 case 收敛为 not_executed,
    #    抛 job_cancelled 让 `_run_env_set_thread` 短路让主线程独占终态决定权。
    if result.cancelled:
        case_run.status = TestCaseRunStatus.NOT_EXECUTED.value
        case_run.completed_at = utc_now()
        record_test_job_event(
            db,
            job=job,
            phase="case_cancelled",
            message=f"用例因终止中断 {case_run.suite_name}/{case_run.case_name}",
            level="warning",
        )
        db.commit()
        _raise_cancelled()

    case_run.exit_code = result.returncode
    case_run.stdout_summary = result.stdout
    case_run.stderr_summary = result.stderr
    case_run.completed_at = utc_now()
    if result.timed_out and command_timeout < CASE_COMMAND_TIMEOUT_SECONDS:
        detail = "测试任务超过 15 小时总超时"
        mark_case_execution_error(
            db, job=job, case_run=case_run, detail=detail, error_code="task_timeout"
        )
        raise TestJobExecutionError("task_timeout", detail)
    if result.transport_failed:
        detail = result.stderr or result.stdout or "SSH command timed out"
        mark_case_execution_error(db, job=job, case_run=case_run, detail=detail)
        raise RemoteCommandError(detail)
    if result.returncode == 0:
        case_run.status = TestCaseRunStatus.PASSED.value
        level = "info"
        message = f"用例通过 {case_run.suite_name}/{case_run.case_name}"
    elif result.returncode == 124:
        case_run.status = TestCaseRunStatus.TIMEOUT.value
        level = "error"
        message = f"用例超时 {case_run.suite_name}/{case_run.case_name}"
    else:
        case_run.status = TestCaseRunStatus.FAILED.value
        level = "error"
        message = f"用例失败 {case_run.suite_name}/{case_run.case_name}"

    # Override PASSED → SKIPPED: mugen exit code 0 doesn't mean pass —
    # check results/{suite}/skipped/ dir to see if mugen actually skipped it.
    if case_run.status == TestCaseRunStatus.PASSED.value:
        if getattr(job, "mugen_exec_command", None):
            check_script = (
                f"docker exec openEuler_test ls -1 "
                f"/home/mugen/results/{shlex.quote(case_run.suite_name)}/skipped/ 2>/dev/null"
            )
        else:
            check_script = (
                f"ls -1 /opt/mugen/results/{shlex.quote(case_run.suite_name)}/skipped/ 2>/dev/null"
            )
        try:
            check_result = run_control_command(
                control=control,
                script=check_script,
                timeout_seconds=30,
            )
            if check_result.returncode == 0 and check_result.stdout:
                skipped = {
                    line.strip() for line in check_result.stdout.splitlines() if line.strip()
                }
                if case_run.case_name in skipped:
                    case_run.status = TestCaseRunStatus.SKIPPED.value
                    level = "info"
                    message = f"用例跳过 {case_run.suite_name}/{case_run.case_name}"
        except Exception:  # noqa: BLE001
            logger.debug("case skip check failed", exc_info=True)

    record_test_job_event(db, job=job, phase="case_completed", message=message, level=level)
    db.commit()

    # 子用例解析（正常结束才解析，超时/挂死不解析）
    _parse_and_store_subcases(db, job=job, control=control, case_run=case_run)

    # Per-case result collection: append to module log immediately (before
    # next case overwrites mugen results dir). Only for modules that need it.
    _per_case_collect_log(db, job=job, control=control, case_run=case_run)

    # 逐 case 日志原子上传（ADR 0048）：正常收敛路径至此，机器仍可达；
    # 挂死/取消/传输失败路径在此之前已 return/raise，不会走到这里。
    upload_case_logs(db, job=job, control=control, case_run=case_run)

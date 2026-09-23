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

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
import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.core.process_runner import run_process

logger = logging.getLogger(__name__)

# 远程命令执行：基于 sshpass+ssh/scp 在测试节点上跑命令与传文件。
# 输出统一截断到 SUMMARY_LIMIT 防止巨量 stdout 撑爆 worker 内存。

SUMMARY_LIMIT = 16 * 1024


@dataclass(frozen=True)
class RemoteTarget:
    """SSH 连接三元组：主机、账号、密码。"""

    host: str
    username: str
    password: str


@dataclass(frozen=True)
class RemoteRunOptions:
    """远程命令执行控制选项。"""

    verify_host_key: bool = True
    output_limit_bytes: int = SUMMARY_LIMIT
    on_line: Callable[[str], None] | None = None
    cancel_event: threading.Event | None = None
    cancel_events: Sequence[threading.Event] = ()


@dataclass(frozen=True)
class RemoteCommandResult:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False

    @property
    def transport_failed(self) -> bool:
        """
        传输层失败：超时或 SSH exit 255(连不上)。与用例返回码区分，
        transport_failed 走 RemoteCommandError 链路，不按用例失败处理。
        cancelled(外部主动打断)不算传输失败——调用方要显式判并走取消分支。
        """


class RemoteCommandError(Exception):
    """远程命令传输失败(SSH 连不上、命令缺失等)，区别于用例本身的退出码。"""


def ssh_target(*, username: str, host: str) -> str:
    return f"{username}@{host}"


def run_ssh_command(
    *,
    target: RemoteTarget,
    command: str,
    timeout_seconds: int,
    stdin: str | None = None,
    options: RemoteRunOptions = RemoteRunOptions(),
) -> RemoteCommandResult:
    """用 sshpass 跑一次 SSH 命令。密码经 SSHPASS 环境变量传递(-e)，不入 argv。

    verify_host_key=False 时关闭主机密钥校验(测试节点临时机器可接受)；
    生产侧远程命令应保持 True。命令缺失抛 RemoteCommandError。

    传入任一取消事件时，run_process 会按 2 秒分片轮询；命中即 kill 本地
    sshpass 并返回 `cancelled=True`，上层据此走取消收敛而不是 transport_failed。
    """
    host = target.host
    username = target.username
    password = target.password
    verify_host_key = options.verify_host_key
    output_limit_bytes = options.output_limit_bytes
    on_line = options.on_line
    cancel_event = options.cancel_event
    cancel_events = options.cancel_events
    env = {**os.environ, "SSHPASS": password}
    host_key_opts = (
        ["-o", "StrictHostKeyChecking=accept-new"]
        if verify_host_key
        else [
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]
    )
    argv = [
        "sshpass",
        "-e",
        "ssh",
        "-o",
        "BatchMode=no",
        "-o",
        "ConnectTimeout=10",
        *host_key_opts,
        "-o",
        "GSSAPIAuthentication=no",
        "-o",
        "PreferredAuthentications=password",
        ssh_target(username=username, host=host),
        command,
    ]
    try:
        completed = run_process(
            argv,
            stdin=stdin,
            timeout_seconds=timeout_seconds,
            output_limit_bytes=output_limit_bytes,
            env=env,
            on_line=on_line,
            cancel_event=cancel_event,
            cancel_events=cancel_events,
        )
    except FileNotFoundError as exc:
        command_name = exc.filename or argv[0]
        raise RemoteCommandError(f"worker command is missing: {command_name}") from exc
    return RemoteCommandResult(
        returncode=completed.exit_code,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=completed.timed_out,
        cancelled=completed.cancelled,
    )


def run_remote_bash(
    *,
    target: RemoteTarget,
    script: str,
    timeout_seconds: int,
) -> RemoteCommandResult:
    return run_ssh_command(
        target=target,
        command="bash -s",
        timeout_seconds=timeout_seconds,
        stdin=script,
    )


def run_remote_bash_command(
    *,
    target: RemoteTarget,
    script: str,
    timeout_seconds: int,
    options: RemoteRunOptions = RemoteRunOptions(),
) -> RemoteCommandResult:
    return run_ssh_command(
        target=target,
        command=f"bash -lc {shlex.quote(script)}",
        timeout_seconds=timeout_seconds,
        options=options,
    )


def write_remote_file(
    *,
    target: RemoteTarget,
    path: str,
    content: str,
    timeout_seconds: int = 30,
    options: RemoteRunOptions = RemoteRunOptions(),
) -> RemoteCommandResult:
    """
    把内容写到远程文件：先建目录，umask 077 + chmod 600 保证文件仅属主可读，
    适配脚本与凭据文件的安全要求。
    """
    return run_ssh_command(
        target=target,
        command=(
            f"mkdir -p {shlex.quote(directory)} && "
            f"umask 077 && cat > {shlex.quote(path)} && chmod 600 {shlex.quote(path)}"
        ),
        timeout_seconds=timeout_seconds,
        stdin=content,
        options=RemoteRunOptions(verify_host_key=verify_host_key, cancel_event=cancel_event),
    )


def scp_directory(
    *,
    target: RemoteTarget,
    remote_path: str,
    local_dir: str,
    timeout_seconds: int = 300,
    verify_host_key: bool = True,
) -> bool:
    """用 scp -r 把远端目录拉到 local_dir，成功返回 True。"""
    host = target.host
    username = target.username
    password = target.password
    env = {**os.environ, "SSHPASS": password}
    os.makedirs(local_dir, exist_ok=True)
    host_key_opts = (
        ["-o", "StrictHostKeyChecking=accept-new"]
        if verify_host_key
        else ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    )
    argv = [
        "sshpass",
        "-e",
        "scp",
        "-r",
        "-o",
        "BatchMode=no",
        "-o",
        "ConnectTimeout=10",
        *host_key_opts,
        "-o",
        "GSSAPIAuthentication=no",
        "-o",
        "PreferredAuthentications=password",
        f"{username}@{host}:{shlex.quote(remote_path)}",
        local_dir,
    ]
    try:
        completed = run_process(
            argv,
            timeout_seconds=timeout_seconds,
            output_limit_bytes=4096,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        # scp 目录失败按软失败返回 False(调用方处理),留 debug 便于排查传输失败。
        logger.debug("scp directory failed", exc_info=True)
        return False
    return completed.exit_code == 0


def scp_file(
    *,
    target: RemoteTarget,
    remote_path: str,
    local_path: str,
    timeout_seconds: int = 300,
    verify_host_key: bool = True,
) -> bool:
    """scp a single remote file to local_path. Returns True on success.

    local_path's parent dir must exist (caller ensures). Downloads the full file
    to disk — no stdout capture, no truncation (unlike ``cat`` via run_ssh_command
    which is capped at SUMMARY_LIMIT). Used by _self_collect_logs for log files
    (mugen logs / ltp.txt) so large files aren't truncated to 16KB.
    """
    host = target.host
    username = target.username
    password = target.password
    env = {**os.environ, "SSHPASS": password}
    host_key_opts = (
        ["-o", "StrictHostKeyChecking=accept-new"]
        if verify_host_key
        else ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    )
    argv = [
        "sshpass",
        "-e",
        "scp",
        "-o",
        "BatchMode=no",
        "-o",
        "ConnectTimeout=10",
        *host_key_opts,
        "-o",
        "GSSAPIAuthentication=no",
        "-o",
        "PreferredAuthentications=password",
        f"{username}@{host}:{shlex.quote(remote_path)}",
        local_path,
    ]
    try:
        completed = run_process(
            argv,
            timeout_seconds=timeout_seconds,
            output_limit_bytes=4096,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        # scp 单文件失败按软失败返回 False,留 debug 便于排查传输失败。
        logger.debug("scp file failed", exc_info=True)
        return False
    return completed.exit_code == 0

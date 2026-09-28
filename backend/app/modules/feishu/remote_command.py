# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass

from app.core.process_runner import run_process

# 飞书远程命令执行：经 sshpass + ssh 用资源台账中的 SSH 凭据在目标机上跑
# 一条命令。凭据通过 SSHPASS 环境变量传入(不出现在命令行/进程列表)。
# ssh 选项固定禁用公钥、强制密码、不校验 host key(内网一次性执行)，输出
# 截断到 8192 字节防止卡片超限。超时 60 秒。这是信任边界内的执行能力，
# 命令文本来源(飞书卡片输入)必须经上层鉴权与审计。

REMOTE_COMMAND_TIMEOUT_SECONDS = 60
REMOTE_COMMAND_OUTPUT_LIMIT_BYTES = 8192


class RemoteCommandUnavailableError(Exception):
    """sshpass/ssh 可执行缺失，远程命令无法执行。"""


@dataclass(frozen=True)
class RemoteCommandResult:
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    stdout_length: int = 0
    stderr_length: int = 0
    output_truncated: bool = False


@dataclass(frozen=True)
class RemoteCommandRequest:
    """远程命令请求：连接凭据、命令与超时/截断设置。"""

    host: str
    username: str
    password: str
    command: str
    timeout_seconds: int = REMOTE_COMMAND_TIMEOUT_SECONDS
    output_limit_bytes: int = REMOTE_COMMAND_OUTPUT_LIMIT_BYTES


def execute_remote_command(
    *,
    request: RemoteCommandRequest,
) -> RemoteCommandResult:
    host = request.host
    username = request.username
    password = request.password
    command = request.command
    timeout_seconds = request.timeout_seconds
    output_limit_bytes = request.output_limit_bytes
    """在目标资源上经 ssh 执行一条命令(sh -lc 包裹)。

    密码经 SSHPASS 环境变量传递，ssh 强制密码认证、禁用公钥、忽略 host key。
    超时与输出截断由 run_process 处理。sshpass 缺失抛
    RemoteCommandUnavailableError。
    """
    env = {**os.environ, "SSHPASS": password}
    args = [
        "sshpass",
        "-e",
        "ssh",
        "-o",
        "BatchMode=no",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "NumberOfPasswordPrompts=1",
        "-o",
        "PreferredAuthentications=password",
        "-o",
        "PubkeyAuthentication=no",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{username}@{host}",
        "sh",
        "-lc",
        shlex.quote(command),
    ]
    try:
        result = run_process(
            args,
            timeout_seconds=timeout_seconds,
            output_limit_bytes=output_limit_bytes,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RemoteCommandUnavailableError(f"missing command: {exc.filename}") from exc
    return RemoteCommandResult(
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        duration_ms=result.duration_ms,
        timed_out=result.timed_out,
        stdout_length=result.stdout_length,
        stderr_length=result.stderr_length,
        output_truncated=result.output_truncated,
    )

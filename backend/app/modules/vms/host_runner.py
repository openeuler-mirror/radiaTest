# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import base64
import json
import shlex
import subprocess
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Generic, Any, TypeVar, overload

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

HostPayload = BaseModel | Mapping[str, Any]
HostEventSink = Callable[[str, str], None]
ResultT = TypeVar("ResultT", bound=BaseModel)
EVENT_PREFIX = "KRONOS_EVENT\t"
DIAGNOSTIC_LINE_LIMIT = 20
DIAGNOSTIC_CHAR_LIMIT = 2000
IGNORED_STDERR_PREFIXES = ("Warning: Permanently added ",)
IGNORED_STDERR_LINES = ("Authorized users only. All activities may be monitored and reported.",)


class HostScriptError(Exception):
    def __init__(self, code: str, message: str, detail: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


def _script_path(script_name: str) -> Path:
    return Path(__file__).with_name("host_scripts") / script_name


def _payload_data(payload: HostPayload) -> dict[str, Any]:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    return dict(payload)


def _text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _emit_host_event_line(line: str, event_sink: HostEventSink | None) -> None:
    if event_sink is None or not line.startswith(EVENT_PREFIX):
        return
    parts = line.rstrip("\r\n").split("\t", 2)
    if len(parts) != 3:
        return
    _prefix, phase, message = parts
    event_sink(phase[:64], message[:2000])


def _stderr_diagnostic(stderr: str) -> str:
    lines = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if not stripped or line.startswith(EVENT_PREFIX):
            continue
        if line.startswith(IGNORED_STDERR_PREFIXES) or line in IGNORED_STDERR_LINES:
            continue
        lines.append(stripped)
    if not lines:
        return ""
    diagnostic = "\n".join(lines[-DIAGNOSTIC_LINE_LIMIT:])
    return diagnostic[-DIAGNOSTIC_CHAR_LIMIT:]


def _with_stderr_diagnostic(message: str, stderr: str) -> str:
    diagnostic = _stderr_diagnostic(stderr)
    if not diagnostic or diagnostic in message:
        return message
    return f"{message}\n宿主命令 stderr:\n{diagnostic}"


def _parse_host_stdout(stdout: str) -> object:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as original_exc:
        for line in reversed(stdout.splitlines()):
            candidate = line.strip()
            if not (candidate.startswith("{") and candidate.endswith("}")):
                continue
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise original_exc


def _run_host_process(
    command: list[str],
    *,
    script: str,
    timeout_seconds: int,
    event_sink: HostEventSink | None,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        raise RuntimeError("subprocess pipes must be captured")

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def write_stdin() -> None:
        try:
            process.stdin.write(script)
            process.stdin.close()
        except (OSError, ValueError):
            pass

    def read_stdout() -> None:
        for line in iter(process.stdout.readline, ""):
            stdout_lines.append(line)
        process.stdout.close()

    def read_stderr() -> None:
        for line in iter(process.stderr.readline, ""):
            stderr_lines.append(line)
            _emit_host_event_line(line, event_sink)
        process.stderr.close()

    threads = [
        threading.Thread(target=write_stdin, daemon=True),
        threading.Thread(target=read_stdout, daemon=True),
        threading.Thread(target=read_stderr, daemon=True),
    ]
    for thread in threads:
        thread.start()

    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        for thread in threads:
            thread.join(timeout=1)
        raise subprocess.TimeoutExpired(
            command,
            timeout_seconds,
            output="".join(stdout_lines),
            stderr="".join(stderr_lines),
        ) from exc

    for thread in threads:
        thread.join()

    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
    )


@dataclass(frozen=True)
class HostRunOptions(Generic[ResultT]):
    """宿主脚本执行选项：结果模型、事件池与超时。"""

    result_model: type[ResultT] | None = None
    event_sink: HostEventSink | None = None
    timeout_seconds: int | None = None


@overload
def run_host_script(
    *,
    host_ip: str,
    script_name: str,
    payload: HostPayload,
    options: HostRunOptions[type[ResultT]],
) -> ResultT:
    ...


@overload
def run_host_script(
    *,
    host_ip: str,
    script_name: str,
    payload: HostPayload,
    options: HostRunOptions[None],
 ) -> dict[str, Any]:
    ...


def run_host_script(
    *,
    host_ip: str,
    script_name: str,
    payload: HostPayload,
    options: HostRunOptions[type[ResultT] | None] = HostRunOptions(),
) -> dict[str, Any] | ResultT:
    result_model = options.result_model
    event_sink = options.event_sink
    timeout_seconds = options.timeout_seconds
    settings = get_settings()
    script = _script_path(script_name).read_text(encoding="utf-8")
    encoded_payload = base64.b64encode(
        json.dumps(_payload_data(payload), ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).decode("ascii")
    remote_command = f"KRONOS_PAYLOAD_B64={shlex.quote(encoded_payload)} bash -s"
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    if not settings.vm_host_ssh_key_path:
        raise HostScriptError(
            "vm_host_ssh_key_missing",
            "VM host SSH key path is not configured",
        )
    command.extend(["-i", settings.vm_host_ssh_key_path, "-o", "IdentitiesOnly=yes"])
    command.extend(
        [
            f"root@{host_ip}",
            remote_command,
        ]
    )

    try:
        completed = _run_host_process(
            command,
            script=script,
            timeout_seconds=min(
                timeout_seconds or settings.vm_host_script_timeout_seconds,
                settings.vm_host_script_timeout_seconds,
            ),
            event_sink=event_sink,
        )
    except FileNotFoundError as exc:
        command_name = exc.filename or command[0]
        raise HostScriptError(
            "worker_dependency_missing",
            f"worker command is missing: {command_name}",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HostScriptError(
            "timeout",
            "Host script timed out",
            {"stdout": _text(exc.output), "stderr": _text(exc.stderr)},
        ) from exc

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    result: object | None = None
    if stdout:
        try:
            result = _parse_host_stdout(stdout)
        except json.JSONDecodeError as exc:
            if completed.returncode != 0:
                code = (
                    "host_connection_failed"
                    if completed.returncode == 255
                    else "host_script_failed"
                )
                raise HostScriptError(
                    code,
                    stderr or f"Host script exited with {completed.returncode}",
                    {"returncode": completed.returncode, "stdout": stdout, "stderr": stderr},
                ) from exc
            raise HostScriptError(
                "invalid_host_response",
                "Host script did not return valid JSON",
                {"stdout": stdout, "stderr": stderr},
            ) from exc

    if completed.returncode != 0 and result is None:
        code = "host_connection_failed" if completed.returncode == 255 else "host_script_failed"
        raise HostScriptError(
            code,
            stderr or f"Host script exited with {completed.returncode}",
            {"returncode": completed.returncode, "stdout": stdout, "stderr": stderr},
        )

    if not isinstance(result, dict):
        raise HostScriptError("invalid_host_response", "Host script JSON must be an object")
    if result.get("status") == "error":
        code = str(result.get("error_code") or "host_script_failed")
        message = _with_stderr_diagnostic(str(result.get("error_message") or code), stderr)
        raise HostScriptError(code, message, result)
    if result_model is None:
        return result
    try:
        return result_model.model_validate(result)
    except ValidationError as exc:
        raise HostScriptError(
            "invalid_host_response",
            "Host script JSON does not match expected schema",
            {"errors": exc.errors(), "result": result},
        ) from exc

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

# 子进程执行器：用 selectors 同时收 stdout/stderr/写入 stdin，超时强制 kill，
# 输出按 output_limit_bytes 截断并把已截断标记回传。用于 VM 宿主脚本执行等
# 需要超时控制和输出上限的场景，避免长输出撑爆任务事件存储。
from __future__ import annotations

import os
import selectors
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessResult:
    """子进程执行结果。

    stdout_length/stderr_length 记录实际产出字节数(可能大于截断后的留存)，
    output_truncated 标记是否触发了截断。
    """

    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    cancelled: bool = False
    stdout_length: int = 0
    stderr_length: int = 0
    output_truncated: bool = False


def decode_output(value: bytes) -> str:
    """用 replace 容错解码，避免非 UTF-8 输出直接抛错。"""
    return value.decode("utf-8", errors="replace")


def append_limited(*, target: bytearray, chunk: bytes, limit: int) -> bool:
    """把 chunk 追加到 target，超过 limit 时从头删多余字节并返回 True(已截断)。

    从头丢弃而非截断尾部，保留最近的输出——对排障更有价值。
    """
    target.extend(chunk)
    overflow = len(target) - limit
    if overflow <= 0:
        return False
    del target[:overflow]
    return True


def run_process(
    args: Sequence[str],
    *,
    timeout_seconds: float,
    output_limit_bytes: int,
    env: Mapping[str, str] | None = None,
    stdin: str | None = None,
    on_line: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    cancel_events: Sequence[threading.Event] = (),
) -> ProcessResult:
    """运行子进程并流式收发 IO，超时 kill、输出按上限截断。

    超时时 exit_code 置 None、timed_out=True；输出超限不中断进程，继续运行到
    结束或超时，只截断留存部分。stdin 通过非阻塞写入流式提供，避免大输入
    一次性塞满管道缓冲区造成死锁。

    传入的任一取消事件命中时按 2 秒片轮询 kill 子进程，标 `cancelled=True`
    与 timed_out 区分——用于跨层"取消/挂死打断"的短响应，而不是步骤自然
    超时。未传取消事件时行为与原实现一致(一次 select 走完剩余时间)。
    """
    started_at = time.monotonic()
    stdin_data = stdin.encode() if stdin is not None else None
    process = subprocess.Popen(
        list(args),
        stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(env) if env is not None else None,
    )
    if process.stdout is None or process.stderr is None:
        raise RuntimeError("subprocess stdout/stderr must be captured")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    stdin_offset = 0
    if process.stdin is not None:
        if stdin_data:
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        else:
            process.stdin.close()
    stdout = bytearray()
    stderr = bytearray()
    stdout_line_buffer = ""
    stdout_length = 0
    stderr_length = 0
    output_truncated = False
    timed_out = False
    cancelled = False

    try:
        while selector.get_map():
            remaining_timeout = timeout_seconds - (time.monotonic() - started_at)
            if remaining_timeout <= 0:
                timed_out = True
                process.kill()
                break
            if (cancel_event is not None and cancel_event.is_set()) or any(
                event.is_set() for event in cancel_events
            ):
                cancelled = True
                process.kill()
                break
            # 任一取消事件存在时用 2s 片轮询，保证取消信号 ≤2s 内被 kill；
            # 无取消事件时保留原语义，一次 select 走完整个剩余时间。
            wait_slice = (
                min(remaining_timeout, 2.0)
                if cancel_event is not None or cancel_events
                else remaining_timeout
            )
            for key, _ in selector.select(timeout=wait_slice):
                if key.data == "stdin":
                    try:
                        stdin_offset += os.write(
                            key.fileobj.fileno(),
                            stdin_data[stdin_offset:stdin_offset + 65536],
                        )
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        stdin_offset = len(stdin_data)
                    if stdin_offset >= len(stdin_data):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    continue
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    stdout_length += len(chunk)
                    truncated = append_limited(
                        target=stdout,
                        chunk=chunk,
                        limit=output_limit_bytes,
                    )
                    if on_line:
                        stdout_line_buffer += decode_output(chunk)
                        while "\n" in stdout_line_buffer:
                            line, stdout_line_buffer = stdout_line_buffer.split(
                                "\n", 1
                            )
                            on_line(line)
                else:
                    stderr_length += len(chunk)
                    truncated = append_limited(
                        target=stderr,
                        chunk=chunk,
                        limit=output_limit_bytes,
                    )
                output_truncated = output_truncated or truncated
    finally:
        selector.close()
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()

    if on_line and stdout_line_buffer:
        on_line(stdout_line_buffer)

    exit_code = process.wait()
    return ProcessResult(
        exit_code=None if (timed_out or cancelled) else exit_code,
        stdout=decode_output(bytes(stdout)),
        stderr=decode_output(bytes(stderr)),
        duration_ms=int((time.monotonic() - started_at) * 1000),
        timed_out=timed_out,
        cancelled=cancelled,
        stdout_length=stdout_length,
        stderr_length=stderr_length,
        output_truncated=output_truncated,
    )

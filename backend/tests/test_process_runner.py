# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import sys
import threading

from app.core.process_runner import run_process


def test_run_process_limits_captured_output() -> None:
    result = run_process(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('x' * 9000 + 'END'); sys.stderr.write('e' * 100)",
        ],
        timeout_seconds=10,
        output_limit_bytes=1024,
    )

    assert result.exit_code == 0
    assert len(result.stdout.encode()) <= 1024
    assert len(result.stderr.encode()) <= 1024
    assert result.stdout.endswith("END")
    assert result.stdout_length == 9003
    assert result.stderr_length == 100
    assert result.output_truncated is True


def test_run_process_stops_after_timeout() -> None:
    result = run_process(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_seconds=0.1,
        output_limit_bytes=1024,
    )

    assert result.exit_code is None
    assert result.timed_out is True
    assert result.duration_ms < 1000


def test_run_process_times_out_when_child_does_not_read_stdin() -> None:
    result = run_process(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        stdin="x" * 1024 * 1024,
        timeout_seconds=0.1,
        output_limit_bytes=1024,
    )

    assert result.exit_code is None
    assert result.timed_out is True
    assert result.duration_ms < 1000


def test_run_process_cancel_event_kills_child_before_timeout() -> None:
    """cancel_event 命中时秒级 kill，标 cancelled 且不算 timed_out。"""
    stop = threading.Event()

    timer = threading.Timer(0.5, stop.set)
    timer.start()
    try:
        result = run_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout_seconds=60,
            output_limit_bytes=1024,
            cancel_event=stop,
        )
    finally:
        timer.cancel()

    assert result.cancelled is True
    assert result.timed_out is False
    assert result.exit_code is None
    assert result.duration_ms < 5000


def test_run_process_additional_cancel_event_kills_child_before_timeout() -> None:
    """附加取消事件也必须按 2 秒分片打断子进程。"""
    stop = threading.Event()

    timer = threading.Timer(0.1, stop.set)
    timer.start()
    try:
        result = run_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout_seconds=4,
            output_limit_bytes=1024,
            cancel_events=(stop,),
        )
    finally:
        timer.cancel()

    assert result.cancelled is True
    assert result.timed_out is False
    assert result.exit_code is None
    assert result.duration_ms < 2500


def test_run_process_cancel_event_absent_preserves_timeout_semantics() -> None:
    """未传 cancel_event 时行为不变：只有 timeout 才 kill。"""
    result = run_process(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_seconds=0.5,
        output_limit_bytes=1024,
    )

    assert result.cancelled is False
    assert result.timed_out is True

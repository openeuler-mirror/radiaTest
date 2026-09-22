# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""单宿主 VM 创建并发控制，基于 fcntl.flock 文件锁。

每台宿主用 N 个 "slot" 锁文件，允许同一宿主最多
``settings.vm_max_concurrent_per_host`` 个 VM 同时创建，避免多个 pipeline
RunJob 同时指向同一宿主时争抢资源。设计取舍见 ADR 0025。
"""

from __future__ import annotations

import fcntl
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

_LOCK_DIR = Path("/tmp/kronos-host-locks")


def _max_slots() -> int:
    """调用时(而非 import 时)从 settings 读取并发上限。"""
    from app.core.config import get_settings

    return max(1, get_settings().vm_max_concurrent_per_host)


def _lock_path(host_ip: str, slot: int) -> Path:
    safe_ip = host_ip.replace(".", "-")
    return _LOCK_DIR / f"vm-create-{safe_ip}-{slot}.lock"


def _try_slot(host_ip: str, slot: int) -> TextIO | None:
    """非阻塞尝试占用指定 slot，成功返回文件句柄，失败返回 None。"""
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    fh = open(_lock_path(host_ip, slot), "w")  # noqa: SIM115
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fh
    except OSError:
        fh.close()
        return None


def try_host_lock(host_ip: str) -> TextIO | None:
    """非阻塞尝试占用任一可用 slot。

    成功返回文件句柄(调用方须调 ``release_host_lock`` 释放)，所有 slot
    被占用时返回 None。
    """
    for slot in range(_max_slots()):
        fh = _try_slot(host_ip, slot)
        if fh is not None:
            return fh
    return None


def release_host_lock(fh: TextIO) -> None:
    """释放由 ``try_host_lock`` 或 ``host_create_lock`` 取得的锁。"""
    fcntl.flock(fh, fcntl.LOCK_UN)
    fh.close()


@contextmanager
def host_create_lock(
    host_ip: str,
    *,
    on_wait: Callable[[], None] | None = None,
) -> Iterator[bool]:
    """为 *host_ip* 上的 VM 创建占用一个可用 slot。

    先非阻塞尝试所有 slot；均不可用时调 *on_wait*(用于状态日志)，然后
    循环轮询所有 slot 直到有空闲。等待后取得返回 ``True``，首次即取得
    返回 ``False``。
    """
    # 阶段1：非阻塞尝试所有 slot。
    for slot in range(_max_slots()):
        fh = _try_slot(host_ip, slot)
        if fh is not None:
            try:
                yield False
            finally:
                release_host_lock(fh)
            return

    # 阶段2：所有 slot 忙——循环轮询所有 slot 直到有空闲。
    # 不在单个文件上阻塞(flock 按文件互斥；阻塞在 slot 0 会让其他等待者
    # 在 slot 1+ 空闲时仍卡住)。
    if on_wait is not None:
        on_wait()
    while True:
        for slot in range(_max_slots()):
            fh = _try_slot(host_ip, slot)
            if fh is not None:
                try:
                    yield True
                finally:
                    release_host_lock(fh)
                return
        time.sleep(1)

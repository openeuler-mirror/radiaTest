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
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

# 观察模式参数：阈值+复核失败后，有 BMC(带外)的物理机不立即判死，进入观察
# 等 SSH 自愈——LTP oom/cgroup 类用例会把控制面压到分钟级失联且可自愈
# (ADR 0044)。判死只信电源状态：观察到电源 off 即锚定断电宽限
# (正常重启 10 分钟内必回)；全程电源 on 或查询失败则等观察上限兜底。
# 测试可直接覆盖这些常量缩短节奏。
WATCH_TIMEOUT_SECONDS = 1800.0
WATCH_CONFIRM_INTERVAL_SECONDS = 180.0
WATCH_POWER_OFF_DEADLINE_SECONDS = 600.0


class HangDetector:
    """后台心跳探活器：在用例执行期间周期性调 check_fn 判断节点是否挂死。

    状态机：正常 → 连续 max_failures 次失败后先等一个 interval 复核一次
    (瞬断恢复常压在阈值线上，见 ADR 0042) → 两分支：
    - confirm_fn 缺失(VM/无 BMC)：判死，fire on_hung 一次；
    - confirm_fn 存在：三态均进观察模式——心跳照常，confirm 按
      watch_confirm_interval 降频复查电源状态。BMC 报电源 off 时锚定
      断电宽限 power_off_deadline(默认 10 分钟)，宽限取代观察上限；
      全程电源 on 或查询失败则等 watch_timeout 上限。SSH 恢复则 fire
      on_recovered 后回到正常；判死条件到点则 fire on_hung 一次。
    用例结束后由调用方查 is_hung() 决定是否抓 console 诊断。
    """

    def __init__(
        self,
        check_fn: Callable[[], bool],
        *,
        interval: float = 30.0,
        max_failures: int = 5,
        on_hung: Callable[[], None] | None = None,
        confirm_fn: Callable[[], bool | None] | None = None,
        on_watch_start: Callable[[], None] | None = None,
        on_recovered: Callable[[], None] | None = None,
        watch_timeout: float | None = None,
        watch_confirm_interval: float | None = None,
        power_off_deadline: float | None = None,
    ) -> None:
        self._check_fn = check_fn
        self._interval = interval
        self._max_failures = max_failures
        self._on_hung = on_hung
        self._confirm_fn = confirm_fn
        self._on_watch_start = on_watch_start
        self._on_recovered = on_recovered
        self._watch_timeout = (
            watch_timeout if watch_timeout is not None else WATCH_TIMEOUT_SECONDS
        )
        self._watch_confirm_interval = (
            watch_confirm_interval
            if watch_confirm_interval is not None
            else WATCH_CONFIRM_INTERVAL_SECONDS
        )
        self._power_off_deadline = (
            power_off_deadline
            if power_off_deadline is not None
            else WATCH_POWER_OFF_DEADLINE_SECONDS
        )
        self._stop_event = threading.Event()
        self._hung = False
        self._watching = False
        self._watch_started_monotonic: float | None = None
        self._watch_duration: float | None = None
        self._power_off_monotonic: float | None = None
        self._bmc_declared = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._hung = False
        self._watching = False
        self._watch_started_monotonic = None
        self._watch_duration = None
        self._power_off_monotonic = None
        self._bmc_declared = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        consecutive_failures = 0
        last_confirm = 0.0
        while not self._stop_event.wait(self._interval):
            if self._stop_event.is_set():
                return
            alive = self._probe()
            if alive:
                consecutive_failures = 0
                self._hung = False
                # 恢复即清除断电锚定与判死标记：检测器可能跨 episode 复用，
                # 过期宽限不得影响后续判定（含判死后短暂恢复的窗口）。
                self._power_off_monotonic = None
                self._bmc_declared = False
                if self._watching:
                    self._watching = False
                    self._watch_started_monotonic = None
                    self._watch_duration = None
                    # stop 后不再发事件：case 已收敛，迟到的恢复事件会污染取证时间线。
                    if not self._stop_event.is_set() and self._on_recovered is not None:
                        self._on_recovered()
                continue
            consecutive_failures += 1
            if self._hung:
                # 已判过死（一个挂死 episode 只 fire 一次）。
                continue
            if self._watching:
                if self._stop_event.is_set():
                    return
                now = time.monotonic()
                # 判死时刻：断电宽限(首次 off + power_off_deadline)取代观察
                # 上限，可晚于 watch_timeout；未见 off 则用 watch_timeout 兜底。
                if self._power_off_monotonic is not None:
                    declare_at = self._power_off_monotonic + self._power_off_deadline
                else:
                    # _watching 与 _watch_started_monotonic 由本线程成对置位，
                    # 此处必非 None；显式校验防止未来改动引入永不判死的静默退化。
                    if self._watch_started_monotonic is None:
                        raise RuntimeError("_watch_started_monotonic 未置位，挂起检测状态机异常")
                    declare_at = self._watch_started_monotonic + self._watch_timeout
                if now >= declare_at:
                    declared_by_power = self._power_off_monotonic is not None
                    self._finish_watch()
                    self._bmc_declared = declared_by_power
                    self._declare_hung()
                    continue
                if now - last_confirm >= self._watch_confirm_interval:
                    last_confirm = now
                    if self._confirm() is False and self._power_off_monotonic is None:
                        # 首次观察到电源断开：只锚定宽限，不立即判死
                        # (ADR 0044 修订，job 10232 实证 SEL/单次读数不可全信)。
                        self._power_off_monotonic = now
                continue
            if consecutive_failures < self._max_failures:
                continue
            # 达阈值先复核一次（见 ADR 0042）：恢复则清零，避免把压线瞬断判死。
            if self._stop_event.wait(self._interval) or self._stop_event.is_set():
                return
            if self._probe():
                consecutive_failures = 0
                self._hung = False
                continue
            if self._confirm_fn is None:
                self._declare_hung()
                continue
            verdict = self._confirm()
            if self._stop_event.is_set():
                # confirm 可能耗时较长（ipmitool），期间 case 可能已结束；
                # stop 后不得再进入观察模式或发出事件。
                return
            last_confirm = time.monotonic()
            # 三态均进观察模式(ADR 0044 修订)：首查电源 off 也只锚定宽限，
            # 宽限内 SSH 恢复则继续，不再立即判死。
            self._watching = True
            self._watch_started_monotonic = time.monotonic()
            if verdict is False:
                self._power_off_monotonic = self._watch_started_monotonic
            if self._on_watch_start is not None:
                self._on_watch_start()

    def _probe(self) -> bool:
        try:
            return self._check_fn()
        except Exception:
            # 心跳探活异常既可能是节点不可达(预期),也可能是 check_fn 自身 bug;
            # 记 debug 留痕,避免在守护线程里完全静默吞错。
            logger.debug("hang detector check_fn raised", exc_info=True)
            return False

    def _confirm(self) -> bool | None:
        """三态确认；confirm_fn 异常等价于查询失败(None)，交由观察模式兜底。"""
        if self._confirm_fn is None:
            return None
        try:
            return self._confirm_fn()
        except Exception:
            logger.debug("hang detector confirm_fn raised", exc_info=True)
            return None

    def _finish_watch(self) -> None:
        if self._watch_started_monotonic is not None:
            self._watch_duration = time.monotonic() - self._watch_started_monotonic
        self._watching = False
        self._watch_started_monotonic = None
        # 判死收敛后同样清除锚定，与恢复路径保持一致的 episode 卫生。
        self._power_off_monotonic = None

    def _declare_hung(self) -> None:
        self._hung = True
        if self._on_hung is not None:
            # on_hung 通常就是 cancel_event.set，只做一次不可逆取消。
            self._on_hung()

    def is_hung(self) -> bool:
        return self._hung

    def is_watching(self) -> bool:
        return self._watching

    @property
    def watch_duration(self) -> float | None:
        """观察期时长（秒）；未进入观察模式时为 None。"""
        return self._watch_duration

    @property
    def bmc_declared(self) -> bool:
        """判死是否由电源断开证据触发（观察期内 BMC 报告过电源 off）。"""
        return self._bmc_declared

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

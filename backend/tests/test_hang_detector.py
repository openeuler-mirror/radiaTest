# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import time

from app.modules.test_management.hang_detector import HangDetector


def test_hang_detector_reports_not_hung_when_healthy() -> None:
    detector = HangDetector(
        check_fn=lambda: True,
        interval=0.05,
        max_failures=3,
    )
    detector.start()
    time.sleep(0.3)
    detector.stop()
    assert not detector.is_hung()


def test_hang_detector_reports_hung_after_consecutive_failures() -> None:
    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
    )
    detector.start()
    time.sleep(0.5)
    detector.stop()
    assert detector.is_hung()


def test_hang_detector_resets_failures_on_success() -> None:
    call_count = [0]

    def check_fn() -> bool:
        call_count[0] += 1
        return call_count[0] % 2 == 0

    detector = HangDetector(
        check_fn=check_fn,
        interval=0.05,
        max_failures=3,
    )
    detector.start()
    time.sleep(0.5)
    detector.stop()
    assert not detector.is_hung()


def test_hang_detector_stop_terminates_thread() -> None:
    detector = HangDetector(
        check_fn=lambda: True,
        interval=0.05,
        max_failures=3,
    )
    detector.start()
    time.sleep(0.1)
    detector.stop()
    assert not detector.is_alive()


def test_hang_detector_recovers_after_transient_failure() -> None:
    call_count = [0]

    def check_fn() -> bool:
        call_count[0] += 1
        return call_count[0] > 3

    detector = HangDetector(check_fn=check_fn, interval=0.05, max_failures=3)
    detector.start()
    time.sleep(0.5)
    detector.stop()
    assert not detector.is_hung()


def test_hang_detector_fires_on_hung_callback_when_hang_breaches_threshold() -> None:
    """连续失败达阈值时 on_hung(用于外部取消)被调用一次;健康路径不调用。"""
    fired: list[int] = []

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
    )
    detector.start()
    time.sleep(0.5)
    detector.stop()

    assert detector.is_hung()
    assert len(fired) == 1


def test_hang_detector_does_not_fire_on_hung_when_healthy() -> None:
    fired: list[int] = []

    detector = HangDetector(
        check_fn=lambda: True,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
    )
    detector.start()
    time.sleep(0.3)
    detector.stop()

    assert not detector.is_hung()
    assert fired == []


def test_hang_detector_recheck_success_after_threshold_avoids_hang() -> None:
    """达阈值后先复核一次：复核成功则计数清零，不判死不杀 case（9/9 压线瞬断场景）。"""
    fired: list[int] = []
    call_count = [0]

    def check_fn() -> bool:
        call_count[0] += 1
        return call_count[0] > 3

    detector = HangDetector(
        check_fn=check_fn,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
    )
    detector.start()
    time.sleep(0.5)
    detector.stop()

    assert not detector.is_hung()
    assert fired == []


def test_hang_detector_hangs_only_when_recheck_also_fails() -> None:
    """复核也失败才判挂死；判死后不重复 fire。"""
    fired: list[int] = []
    call_count = [0]

    def check_fn() -> bool:
        call_count[0] += 1
        return False

    detector = HangDetector(
        check_fn=check_fn,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
    )
    detector.start()
    time.sleep(0.5)
    detector.stop()

    assert detector.is_hung()
    assert fired == [1]
    # 阈值 3 次 + 复核 1 次都失败才判死，调用数必须至少 4。
    assert call_count[0] >= 4


# ---------- BMC 交叉确认门（观察模式） ----------


def test_confirm_alive_enters_watch_mode_instead_of_hang() -> None:
    """阈值+复核失败后 BMC 确认机器未重启 → 进入观察模式，不判死不取消。"""
    fired: list[int] = []
    watch_started: list[int] = []

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: True,
        on_watch_start=lambda: watch_started.append(1),
        watch_timeout=5.0,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(0.5)
    detector.stop()

    assert not detector.is_hung()
    assert detector.is_watching()
    assert fired == []
    assert watch_started == [1]


def test_watch_mode_recovers_when_heartbeat_succeeds() -> None:
    """观察期内 SSH 恢复 → 不判死，on_recovered 恰一次，退出观察状态。"""
    fired: list[int] = []
    recovered: list[int] = []
    watch_started: list[int] = []
    call_count = [0]

    def check_fn() -> bool:
        call_count[0] += 1
        return call_count[0] > 8

    detector = HangDetector(
        check_fn=check_fn,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: True,
        on_watch_start=lambda: watch_started.append(1),
        on_recovered=lambda: recovered.append(1),
        watch_timeout=10.0,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(0.9)
    detector.stop()

    assert not detector.is_hung()
    assert not detector.is_watching()
    assert fired == []
    assert watch_started == [1]
    assert recovered == [1]


def test_watch_mode_declares_hang_at_timeout_even_if_bmc_alive() -> None:
    """BMC 一直说活着但 SSH 不恢复 → 观察上限兜底判死。"""
    fired: list[int] = []

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: True,
        watch_timeout=0.3,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(0.8)
    detector.stop()

    assert detector.is_hung()
    assert len(fired) == 1
    assert detector.watch_duration is not None
    assert not detector.bmc_declared


def test_watch_mode_power_off_deadline_declares_hang() -> None:
    """观察期内读到电源 off → 锚定断电宽限，到点未恢复判死，不等 30 分钟上限。"""
    fired: list[int] = []
    verdicts = iter([True, False, False, False])

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: next(verdicts, False),
        watch_timeout=30.0,
        watch_confirm_interval=0.05,
        power_off_deadline=0.1,
    )
    detector.start()
    time.sleep(0.6)
    detector.stop()

    assert detector.is_hung()
    assert len(fired) == 1
    assert detector.bmc_declared


def test_confirm_unknown_keeps_watching_until_timeout() -> None:
    """BMC 查询失败(None)不下结论：先观察，直到上限才判死。"""
    fired: list[int] = []

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: None,
        watch_timeout=0.3,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(0.8)
    detector.stop()

    assert detector.is_hung()
    assert len(fired) == 1
    assert not detector.bmc_declared


def test_confirm_power_off_at_threshold_enters_watch_and_declares() -> None:
    """阈值首查即电源 off → 也进观察模式锚定宽限；到点未恢复判死（ADR 0044 修订）。"""
    fired: list[int] = []
    watch_started: list[int] = []

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: False,
        on_watch_start=lambda: watch_started.append(1),
        watch_timeout=30.0,
        watch_confirm_interval=0.05,
        power_off_deadline=0.15,
    )
    detector.start()
    time.sleep(0.6)
    detector.stop()

    assert detector.is_hung()
    assert detector.bmc_declared
    assert watch_started == [1]
    assert detector.watch_duration is not None


def test_confirm_power_off_recovers_within_deadline() -> None:
    """断电宽限内 SSH 恢复 → 得救：不判死、不取消、on_recovered 恰一次。"""
    fired: list[int] = []
    recovered: list[int] = []
    call_count = [0]

    def check_fn() -> bool:
        call_count[0] += 1
        return call_count[0] > 8

    detector = HangDetector(
        check_fn=check_fn,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: False,
        on_recovered=lambda: recovered.append(1),
        watch_timeout=30.0,
        watch_confirm_interval=0.05,
        power_off_deadline=5.0,
    )
    detector.start()
    time.sleep(0.9)
    detector.stop()

    assert not detector.is_hung()
    assert fired == []
    assert recovered == [1]


def test_power_off_deadline_replaces_watch_timeout() -> None:
    """off 锚定后断电宽限取代观察上限：cap 已过仍观察，宽限到点才判死。"""
    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.05,
        max_failures=3,
        confirm_fn=lambda: False,
        watch_timeout=0.2,
        watch_confirm_interval=0.05,
        power_off_deadline=0.5,
    )
    detector.start()
    # 观察约 0.20s 进入并锚定；cap≈0.40s 已过、宽限≈0.70s 未到 → 仍在观察。
    time.sleep(0.55)
    assert detector.is_watching()
    assert not detector.is_hung()
    time.sleep(0.5)
    detector.stop()

    assert detector.is_hung()
    assert detector.bmc_declared
    assert detector.watch_duration is not None
    assert detector.watch_duration >= 0.4


def test_power_off_anchor_resets_after_recovery() -> None:
    """恢复后 off 锚定必须清除：后续 episode 走观察上限而非过期宽限。"""
    calls = [0]
    verdicts = iter([False])  # 第一 episode 首查 off；此后全部电源开启

    def check_fn() -> bool:
        calls[0] += 1
        return calls[0] in (9, 10)

    detector = HangDetector(
        check_fn=check_fn,
        interval=0.03,
        max_failures=2,
        confirm_fn=lambda: next(verdicts, True),
        watch_timeout=0.3,
        watch_confirm_interval=0.02,
    )
    detector.start()
    time.sleep(1.2)
    detector.stop()

    # 第一 episode 首查 off 锚定宽限(默认 600s)，SSH 及时恢复得救；
    # 第二 episode 首查电源 on → 按观察上限判死。若锚定未清除，第二
    # episode 会沿用 600s 宽限，测试时间内不会判死。
    assert detector.is_hung()
    assert not detector.bmc_declared


def test_watch_mode_no_late_callbacks_after_stop() -> None:
    """stop 后不得再进入观察模式或发出事件——case 结束后不留迟到事件。"""
    fired: list[int] = []
    watch_started: list[int] = []

    def slow_confirm() -> bool | None:
        time.sleep(0.4)
        return True

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.02,
        max_failures=2,
        on_hung=lambda: fired.append(1),
        confirm_fn=slow_confirm,
        on_watch_start=lambda: watch_started.append(1),
        watch_timeout=30.0,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(0.1)  # 线程已进入 slow_confirm
    detector.stop()  # join(5s) 覆盖 confirm 完成，返回后不应有任何观察态副作用

    assert not detector.is_watching()
    assert watch_started == []
    assert fired == []


def test_watch_mode_re_enters_after_recovery_and_reloss() -> None:
    """恢复后再次失联 → 重新走阈值并再次进入观察；两个 episode 各一次事件。"""
    fired: list[int] = []
    watch_started: list[int] = []
    recovered: list[int] = []
    calls = [0]

    def check_fn() -> bool:
        calls[0] += 1
        return calls[0] in (9, 10)

    detector = HangDetector(
        check_fn=check_fn,
        interval=0.05,
        max_failures=3,
        on_hung=lambda: fired.append(1),
        confirm_fn=lambda: True,
        on_watch_start=lambda: watch_started.append(1),
        on_recovered=lambda: recovered.append(1),
        watch_timeout=10.0,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(1.0)
    detector.stop()

    assert not detector.is_hung()
    assert fired == []
    assert recovered == [1]
    assert watch_started == [1, 1]


def test_start_resets_watch_state() -> None:
    """复用实例时 start() 必须清掉上一轮的观察态。"""
    healthy = [False]

    detector = HangDetector(
        check_fn=lambda: healthy[0],
        interval=0.02,
        max_failures=2,
        confirm_fn=lambda: True,
        watch_timeout=0.1,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(0.4)
    detector.stop()
    assert detector.is_hung()
    assert detector.watch_duration is not None

    healthy[0] = True
    detector.start()
    time.sleep(0.1)
    detector.stop()

    assert not detector.is_hung()
    assert not detector.is_watching()
    assert detector.watch_duration is None
    assert not detector.bmc_declared


def test_confirm_exception_treated_as_unknown() -> None:
    """confirm_fn 抛异常等价于查询失败，不判死先观察。"""
    def broken_confirm() -> bool | None:
        raise RuntimeError("bmc down")

    detector = HangDetector(
        check_fn=lambda: False,
        interval=0.03,
        max_failures=3,
        confirm_fn=broken_confirm,
        watch_timeout=0.3,
        watch_confirm_interval=0.05,
    )
    detector.start()
    time.sleep(0.2)

    assert detector.is_watching()
    assert not detector.is_hung()
    detector.stop()

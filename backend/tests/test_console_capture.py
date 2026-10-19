# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from app.modules.test_management.console_capture import (
    bmc_power_on,
    capture_bmc_diagnostics,
    capture_vm_console_output,
    vm_domstate_alive,
    vm_hard_reset,
)


def _power_mock(power: str = "Chassis Power is on\n"):
    def mock_run(args, **kwargs):
        cmd_str = " ".join(args)
        if "chassis power status" in cmd_str:
            return _mock_completed(stdout=power)
        return _mock_completed(stdout="")

    return mock_run


def test_bmc_power_on_true_when_power_on() -> None:
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=_power_mock(),
    ):
        result = bmc_power_on(bmc_ip="192.0.2.10", username="ADMIN", password="pw")
    assert result is True


def test_bmc_power_on_false_when_power_off() -> None:
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=_power_mock(power="Chassis Power is off\n"),
    ):
        result = bmc_power_on(bmc_ip="192.0.2.10", username="ADMIN", password="pw")
    assert result is False


def test_bmc_power_on_none_when_query_fails() -> None:
    def mock_run(args, **kwargs):
        if "chassis power status" in " ".join(args):
            return _mock_completed(returncode=1, stderr="Unable to send command")
        return _mock_completed(stdout="")

    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=mock_run,
    ):
        result = bmc_power_on(bmc_ip="192.0.2.10", username="ADMIN", password="pw")
    assert result is None


def test_bmc_power_on_none_when_output_ambiguous() -> None:
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=_power_mock(power="garbage\n"),
    ):
        result = bmc_power_on(bmc_ip="192.0.2.10", username="ADMIN", password="pw")
    assert result is None


def test_bmc_power_on_ignores_sel_events() -> None:
    """job 10232 回归锁：SEL 全是虚构重启事件（且查询失败）也不参与判定。

    电源 on 即 True——SEL 时间戳与事件内容在现场均不可信（BMC RTC 狂奔、
    虚构 System Boot Initiated），判死只信电源状态（ADR 0044 修订）。
    """
    def mock_run(args, **kwargs):
        cmd_str = " ".join(args)
        if "chassis power status" in cmd_str:
            return _mock_completed(stdout="Chassis Power is on\n")
        if "sel list" in cmd_str:
            raise subprocess.TimeoutExpired(cmd="ipmitool", timeout=10)
        return _mock_completed(stdout="")

    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=mock_run,
    ):
        result = bmc_power_on(bmc_ip="192.0.2.10", username="ADMIN", password="pw")
    assert result is True


def test_run_ipmitool_pins_locale_and_timezone() -> None:
    """ipmitool 环境必须钉死 LC_ALL/TZ：BMC 渲染稳定，输出才可比较。"""
    captured_kwargs: list[dict] = []

    def mock_run(args, **kwargs):
        captured_kwargs.append(kwargs)
        return _mock_completed(stdout="Chassis Power is on\n")

    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=mock_run,
    ):
        result = bmc_power_on(bmc_ip="192.0.2.10", username="ADMIN", password="pw")

    assert result is True
    for kwargs in captured_kwargs:
        assert kwargs["env"]["LC_ALL"] == "C"
        assert kwargs["env"]["TZ"] == "UTC"


def _mock_completed(stdout: str = "", returncode: int = 0, stderr: str = ""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


def test_capture_vm_console_output_returns_combined_diagnostics() -> None:
    domstate_output = "running\n"
    console_output = "kernel panic - not syncing: Fatal exception\n"

    def mock_run(args, **kwargs):
        cmd_str = " ".join(args)
        if "domstate" in cmd_str:
            return _mock_completed(stdout=domstate_output)
        if "console" in cmd_str:
            return _mock_completed(stdout=console_output)
        return _mock_completed(stdout="")

    with patch("app.modules.test_management.console_capture.subprocess.run", side_effect=mock_run):
        result = capture_vm_console_output(
            host_ip="10.0.0.1",
            vm_name="test-vm",
            ssh_key_path="/etc/kronos/ssh/id_rsa",
        )

    assert "running" in result
    assert "kernel panic" in result


def test_capture_vm_console_output_handles_ssh_failure() -> None:
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        return_value=_mock_completed(stdout="", returncode=255),
    ):
        result = capture_vm_console_output(
            host_ip="10.0.0.1",
            vm_name="test-vm",
            ssh_key_path="/etc/kronos/ssh/id_rsa",
        )

    assert "255" in result or "failed" in result.lower()


def test_capture_vm_console_output_uses_ssh_key() -> None:
    captured_args = []

    def mock_run(args, **kwargs):
        captured_args.append(args)
        return _mock_completed(stdout="shut off\n")

    with patch("app.modules.test_management.console_capture.subprocess.run", side_effect=mock_run):
        capture_vm_console_output(
            host_ip="10.0.0.1",
            vm_name="test-vm",
            ssh_key_path="/custom/key/path",
        )

    assert len(captured_args) > 0
    assert "/custom/key/path" in captured_args[0]


def test_capture_bmc_diagnostics_returns_combined_sections() -> None:
    captured_args: list[list[str]] = []
    captured_kwargs: list[dict] = []

    def mock_run(args, **kwargs):
        captured_args.append(args)
        captured_kwargs.append(kwargs)
        cmd_str = " ".join(args)
        if "sel list" in cmd_str:
            return _mock_completed(stdout=" 163 | 09/09/26 | System Restart | Asserted\n")
        if "chassis status" in cmd_str:
            return _mock_completed(stdout="System Power         : on\n")
        if "sdr elist" in cmd_str:
            return _mock_completed(stdout="CPU Temp     | 45 degrees C  | ok\n")
        return _mock_completed(stdout="")

    with patch("app.modules.test_management.console_capture.subprocess.run", side_effect=mock_run):
        result = capture_bmc_diagnostics(bmc_ip="192.0.2.10", username="ADMIN", password="pw")

    assert "System Restart" in result
    assert "System Power" in result
    assert "CPU Temp" in result
    assert any("-H" in args and "192.0.2.10" in args for args in captured_args)
    assert any("-I" in args and "lanplus" in args for args in captured_args)
    # 密码经 stdin 传入，不得出现在 argv 中。
    assert all("-P" not in args for args in captured_args)
    assert any("-f" in args and "/dev/stdin" in args for args in captured_args)
    assert all(kwargs.get("input") == "pw\n" for kwargs in captured_kwargs)


def test_capture_bmc_diagnostics_placeholder_when_ipmitool_missing() -> None:
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        result = capture_bmc_diagnostics(bmc_ip="192.0.2.10", username="ADMIN", password="pw")

    assert "failed to capture BMC diagnostics" in result


def test_capture_bmc_diagnostics_timeout_is_reported() -> None:
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ipmitool", timeout=30),
    ):
        result = capture_bmc_diagnostics(bmc_ip="192.0.2.10", username="ADMIN", password="pw")

    assert "timeout after 30s" in result


def test_capture_bmc_diagnostics_all_empty_output_is_not_failure() -> None:
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        return_value=_mock_completed(stdout=""),
    ):
        result = capture_bmc_diagnostics(bmc_ip="192.0.2.10", username="ADMIN", password="pw")

    assert "no BMC diagnostics output" in result


def test_capture_bmc_diagnostics_partial_failure_keeps_collected_sections() -> None:
    def mock_run(args, **kwargs):
        if "sel list" in " ".join(args):
            return _mock_completed(stdout="sel-line\n")
        return _mock_completed(stdout="", returncode=1, stderr="Unable to send command")

    with patch("app.modules.test_management.console_capture.subprocess.run", side_effect=mock_run):
        result = capture_bmc_diagnostics(bmc_ip="192.0.2.10", username="ADMIN", password="pw")

    assert "sel-line" in result
    assert "ipmitool sel list" in result


# ---------- VM 带外判活与硬复位（ADR 0046） ----------


def test_vm_domstate_alive_true_for_live_states() -> None:
    """domstate 活态（running/paused/in shutdown）→ True：VM 活着，观察模式等自愈。"""
    for state in ("running\n", "paused\n", "in shutdown\n", "pmsuspended\n"):
        with patch(
            "app.modules.test_management.console_capture.subprocess.run",
            return_value=_mock_completed(stdout=state),
        ):
            result = vm_domstate_alive(host_ip="10.0.0.1", vm_name="vm-1", ssh_key_path="/k")
        assert result is True


def test_vm_domstate_alive_false_for_dead_states() -> None:
    """domstate 死态（shut off/crashed/dying）→ False：锚定关机宽限后判死。"""
    for state in ("shut off\n", "shutted down\n", "crashed\n", "dying\n"):
        with patch(
            "app.modules.test_management.console_capture.subprocess.run",
            return_value=_mock_completed(stdout=state),
        ):
            result = vm_domstate_alive(host_ip="10.0.0.1", vm_name="vm-1", ssh_key_path="/k")
        assert result is False


def test_vm_domstate_alive_none_when_query_fails_or_unknown() -> None:
    """宿主 SSH 失败/空输出/未识别状态 → None：不下结论，回退观察上限兜底。"""
    # SSH 连接失败（rc=255）
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        return_value=_mock_completed(stdout="", returncode=255),
    ):
        assert vm_domstate_alive(host_ip="10.0.0.1", vm_name="vm-1", ssh_key_path="/k") is None
    # 空输出（如域名不存在，virsh rc=1 无 stdout）
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        return_value=_mock_completed(stdout=""),
    ):
        assert vm_domstate_alive(host_ip="10.0.0.1", vm_name="vm-1", ssh_key_path="/k") is None
    # 未识别输出
    with patch(
        "app.modules.test_management.console_capture.subprocess.run",
        return_value=_mock_completed(stdout="some random text\n"),
    ):
        assert vm_domstate_alive(host_ip="10.0.0.1", vm_name="vm-1", ssh_key_path="/k") is None


def test_vm_hard_reset_destroys_then_starts() -> None:
    """硬复位 = virsh destroy → start，复位后 domstate 活态收口成功判据。"""
    commands: list[str] = []

    def mock_run(args, **kwargs):
        cmd = " ".join(args)
        commands.append(cmd)
        if "domstate" in cmd:
            return _mock_completed(stdout="running\n")
        return _mock_completed(stdout="")

    with patch("app.modules.test_management.console_capture.subprocess.run", side_effect=mock_run):
        ok = vm_hard_reset(host_ip="10.0.0.1", vm_name="vm-1", ssh_key_path="/k")

    assert ok is True
    destroy_index = next(i for i, c in enumerate(commands) if "virsh destroy vm-1" in c)
    start_index = next(i for i, c in enumerate(commands) if "virsh start vm-1" in c)
    assert destroy_index < start_index


def test_vm_hard_reset_fails_when_domain_stays_off() -> None:
    """start 无效（domstate 仍 shut off）→ False：不进入 SSH 等待，直接判恢复失败。"""
    def mock_run(args, **kwargs):
        cmd = " ".join(args)
        if "domstate" in cmd:
            return _mock_completed(stdout="shut off\n")
        return _mock_completed(stdout="")

    with patch("app.modules.test_management.console_capture.subprocess.run", side_effect=mock_run):
        ok = vm_hard_reset(host_ip="10.0.0.1", vm_name="vm-1", ssh_key_path="/k")

    assert ok is False

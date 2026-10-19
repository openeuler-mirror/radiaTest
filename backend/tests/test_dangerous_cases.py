# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import pytest

from app.modules.test_management.frameworks.dangerous_cases import (
    EXTRA_DANGEROUS_CASES,
    collect_dangerous_scan_reasons,
    name_rule_reason,
    resolve_case_danger,
    script_scan_reason,
)


@pytest.mark.parametrize(
    "case_name",
    [
        "oe_test_service_initrd-cleanup",
        "oe_test_service_initrd-parse-etc",
        "oe_test_service_initrd-switch-root",
        "oe_test_service_initrd-udevadm-cleanup-db",
        "oe_test_target_initrd-root-fs",
        "oe_test_target_initrd",
        "oe_test_service_systemd-reboot",
        "oe_test_target_reboot",
        "oe_test_service_systemd-poweroff",
        "oe_test_target_poweroff",
        "oe_test_service_systemd-halt",
        "oe_test_target_halt",
        "oe_test_service_systemd-kexec",
        "oe_test_target_kexec",
        "oe_test_target_shutdown",
        "oe_test_service_systemd-suspend",
        "oe_test_service_systemd-hibernate",
        "oe_test_service_systemd-suspend-then-hibernate",
        "oe_test_service_systemd-hybrid-sleep",
        "oe_test_service_systemd-soft-reboot",
        "oe_test_target_soft-reboot",
        "oe_test_service_systemd-exit",
        "oe_test_target_exit",
        "oe_test_telinit",
        "oe_test_target_ctrl-alt-del",
        "oe_test_target_runlevel0",
        "oe_test_target_runlevel6",
    ],
)
def test_name_rule_blocks_known_dangerous_units(case_name: str) -> None:
    assert name_rule_reason(case_name) is not None


@pytest.mark.parametrize(
    "case_name",
    [
        "oe_test_service_pcp-reboot-init",
        "oe_test_service_systemd-update-utmp-runlevel",
        "oe_test_service_systemd-journald",
        "oe_test_service_sssd-nss",
        "oe_test_target_multi-user",
        "oe_test_service_emergency",
        "oe_test_service_rescue",
        "oe_test_service_debug-shell",
        "oe_test_ltp",
        "oe_test_socket_systemd-journald",
    ],
)
def test_name_rule_spares_safe_cases(case_name: str) -> None:
    assert name_rule_reason(case_name) is None


def test_builtin_list_blocks_exact_names() -> None:
    assert EXTRA_DANGEROUS_CASES, "内置名单不应为空"
    for case_name in EXTRA_DANGEROUS_CASES:
        reason = name_rule_reason(case_name)
        assert reason is not None
        assert "内置" in reason


def test_resolve_combines_name_rule_and_scan_flag() -> None:
    assert resolve_case_danger("oe_test_service_xxx", scanned_reason=None) is None
    assert (
        resolve_case_danger(
            "oe_test_service_xxx", scanned_reason="脚本伪造 initrd 环境"
        )
        == "脚本伪造 initrd 环境"
    )
    assert (
        resolve_case_danger("oe_test_service_initrd-cleanup", scanned_reason=None)
        is not None
    )


def test_script_scan_flags_initrd_release_forgery() -> None:
    script = (
        "#!/usr/bin/bash\n"
        "function pre_test() {\n"
        "    LOG_INFO \"Start environment preparation.\"\n"
        "    touch /etc/initrd-release\n"
        "    systemctl start initrd-cleanup.service\n"
        "}\n"
    )
    assert script_scan_reason(script) is not None


def test_script_scan_flags_explicit_systemctl_destructive_verbs() -> None:
    assert script_scan_reason("systemctl --no-block isolate rescue.target\n")
    assert script_scan_reason("systemctl isolate initrd-switch-root.target\n")
    assert script_scan_reason("systemctl switch-root /sysroot\n")
    assert script_scan_reason("systemctl kexec\n")


def test_script_scan_flags_bare_shutdown_commands() -> None:
    assert script_scan_reason("reboot\n")
    assert script_scan_reason("  sudo poweroff\n")
    assert script_scan_reason("foo && halt\n")


def test_script_scan_spares_mentions_and_innocent_commands() -> None:
    assert script_scan_reason('LOG_INFO "reboot later"\n') is None
    assert script_scan_reason("# reboot the machine here\n") is None
    assert script_scan_reason("systemctl restart systemd-journald.service\n") is None
    assert script_scan_reason("systemctl start initrd-cleanup.service\n") is None
    assert script_scan_reason("cat /etc/initrd-release\n") is None
    assert script_scan_reason("rm -rf /etc/initrd-release\n") is None


def test_collect_dangerous_scan_reasons_reads_suite_scripts(tmp_path) -> None:
    suite_dir = tmp_path / "testcases" / "cli-test" / "systemd"
    suite_dir.mkdir(parents=True)
    (suite_dir / "oe_test_service_initrd-cleanup.sh").write_text(
        "touch /etc/initrd-release\nsystemctl start initrd-cleanup.service\n",
        encoding="utf-8",
    )
    (suite_dir / "oe_test_service_systemd-journald.sh").write_text(
        "systemctl restart systemd-journald.service\n", encoding="utf-8"
    )
    suites = {
        "systemd": {
            "path": "$OET_PATH/testcases/cli-test/systemd",
            "cases": [
                {"name": "oe_test_service_initrd-cleanup"},
                {"name": "oe_test_service_systemd-journald"},
                {"name": "oe_test_service_missing-script"},
            ],
        },
        "pathless": {"cases": [{"name": "oe_test_service_initrd-cleanup"}]},
    }

    reasons = collect_dangerous_scan_reasons(tmp_path, suites)

    assert reasons == {
        ("systemd", "oe_test_service_initrd-cleanup"): (
            "脚本伪造 initrd 环境(/etc/initrd-release)"
        )
    }

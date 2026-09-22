# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""pxe_install 装机校验/网卡采集（T4/T5）单元测试。"""

from __future__ import annotations

import types
from unittest.mock import patch

import pytest

from app.modules.test_management.remote import RemoteCommandError
from app.modules.vms.pxe_install import _collect_nic_macs, _verify_install_os

OS_RELEASE_OK = "PRETTY_NAME=\"openEuler 26.09 (DevStation)\"\nVERSION_ID=\"26.09\"\n"
MARKER_OK = "openEuler-26.09-DevStation rc3_openeuler-2026-08-28-04-39-54"
MARKER_OFFICIAL = "openEuler-24.03-LTS-SP4 official"


class _Result:

    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


def _resource(ip: str = "172.168.131.71") -> types.SimpleNamespace:
    return types.SimpleNamespace(primary_ip=ip)


def _image(os_version: str, round_: str | None) -> types.SimpleNamespace:
    return types.SimpleNamespace(os_version=os_version, round=round_)


def _fake_ssh(files: dict[str, str]) -> None:

    def fake_run_ssh_command(**kwargs: object) -> _Result:
        path = str(kwargs["command"]).split(" ", 1)[1]
        return _Result(0, files.get(path, ""))

    return fake_run_ssh_command


def test_verify_rejects_old_os() -> None:
    with patch(
        "app.modules.vms.pxe_install.run_ssh_command",
        side_effect=_fake_ssh(
            {
                "/etc/os-release": "PRETTY_NAME=\"openEuler 22.03 (LTS-SP4)\"\n",
                "/root/.kronos-install-marker": "",
            }
        ),
    ):
        with pytest.raises(RuntimeError):
            _verify_install_os(
                _resource(),
                _image(
                    "openEuler-26.09-DevStation",
                    "rc3_openeuler-2026-08-28-04-39-54",
                ),
            )


def test_verify_ok_with_marker() -> None:
    with patch(
        "app.modules.vms.pxe_install.run_ssh_command",
        side_effect=_fake_ssh(
            {
                "/etc/os-release": OS_RELEASE_OK,
                "/root/.kronos-install-marker": MARKER_OK,
            }
        ),
    ):
        _verify_install_os(
            _resource(), _image("openEuler-26.09-DevStation", "rc3_openeuler-2026-08-28-04-39-54")
        )


def test_verify_marker_mismatch_rejected() -> None:
    with patch(
        "app.modules.vms.pxe_install.run_ssh_command",
        side_effect=_fake_ssh(
            {
                "/etc/os-release": OS_RELEASE_OK,
                "/root/.kronos-install-marker": "openEuler-26.09-DevStation rc2_xxx",
            }
        ),
    ):
        with pytest.raises(RuntimeError):
            _verify_install_os(
                _resource(),
                _image(
                    "openEuler-26.09-DevStation",
                    "rc3_openeuler-2026-08-28-04-39-54",
                ),
            )


def test_verify_official_requires_official_marker() -> None:
    os_release = 'PRETTY_NAME="openEuler 24.03 (LTS-SP4)"\nVERSION_ID="24.03"\n'
    with patch(
        "app.modules.vms.pxe_install.run_ssh_command",
        side_effect=_fake_ssh(
            {
                "/etc/os-release": os_release,
                "/root/.kronos-install-marker": MARKER_OFFICIAL,
            }
        ),
    ):
        _verify_install_os(_resource(), _image("openEuler-24.03-LTS-SP4", None))


def test_collect_nic_macs_filters_loopback() -> None:
    with patch(
        "app.modules.vms.pxe_install.run_ssh_command",
        return_value=_Result(
            0, "b0:08:75:a3:fc:c4\n00:00:00:00:00:00\nb0:08:75:a3:fc:c5\n"
        ),
    ):
        assert _collect_nic_macs("1.2.3.4", "root", "p") == [
            "b0:08:75:a3:fc:c4",
            "b0:08:75:a3:fc:c5",
        ]


def test_collect_nic_macs_tolerates_failure() -> None:
    with patch(
        "app.modules.vms.pxe_install.run_ssh_command",
        side_effect=RemoteCommandError("ssh fail"),
    ):
        assert _collect_nic_macs("1.2.3.4", "root", "p") == []
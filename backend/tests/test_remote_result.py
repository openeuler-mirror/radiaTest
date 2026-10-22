# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from app.modules.test_management.remote import RemoteCommandResult


def test_transport_failed_covers_timeout_and_ssh_exit_255() -> None:
    """传输层失败只在超时或 SSH exit 255 时为真。

    255 以外的非零退出码是用例自身的失败，必须留在用例失败链路里，
    否则 mugen 用例失败会被误判成 SSH 断连。
    """
    assert RemoteCommandResult(
        returncode=None, stdout="", stderr="", timed_out=True
    ).transport_failed is True
    assert RemoteCommandResult(returncode=255, stdout="", stderr="").transport_failed is True


def test_transport_failed_is_false_for_case_level_exit_codes() -> None:
    """用例返回码 0/1/124 都不是传输层失败。"""
    assert RemoteCommandResult(returncode=0, stdout="ok", stderr="").transport_failed is False
    assert RemoteCommandResult(returncode=1, stdout="", stderr="assert").transport_failed is False
    assert RemoteCommandResult(returncode=124, stdout="", stderr="").transport_failed is False

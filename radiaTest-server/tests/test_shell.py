# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    : 2026/09/09
# @License : Mulan PSL v2
#####################################
import pytest

from server.utils.shell import add_escape, check_cmd, run_cmd, standard_cmd


def test_check_cmd_rejects_shell_interpreter():
    with pytest.raises(RuntimeError, match="unsupported command"):
        check_cmd([["bash", "run.sh"]])


def test_check_cmd_rejects_dash_c_option():
    with pytest.raises(RuntimeError, match="unsupported command"):
        check_cmd([["ls", "-c", "value"]])


def test_standard_cmd_splits_on_and_operator():
    assert standard_cmd("echo a && echo b") == [["echo", "a"], ["echo", "b"]]


def test_standard_cmd_accepts_plain_string():
    assert standard_cmd("ls -l") == [["ls", "-l"]]


def test_standard_cmd_rejects_invalid_type():
    assert standard_cmd(123) == []
    assert standard_cmd([1, 2]) == []


def test_add_escape_escapes_reserved_chars():
    assert add_escape("a?b&c") == r"a\?b\&c"


def test_run_cmd_executes_command():
    returncode, output, error = run_cmd("echo hello")
    assert returncode == 0
    assert output == "hello\n"
    assert error == ""


def test_run_cmd_rejects_invalid_type():
    assert run_cmd(123) == (1, "", "unsupported input type")

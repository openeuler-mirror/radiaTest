# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from app.modules.test_management.result_parser import (
    parse_ltp_log,
    parse_mugen_results_dir,
)


def test_parse_ltp_log_extracts_pass_and_fail() -> None:
    log = """syscalls        1       TPASS   : Test 1 passed
syscalls        2       TPASS   : Test 2 passed
syscalls        3       TFAIL   : Test 3 failed
faccessat       1       TPASS   : Test passed
faccessat       2       TFAIL   : Test failed
"""

    results = parse_ltp_log(log)

    assert len(results) == 2
    by_name = {r.sub_test_name: r for r in results}

    assert by_name["syscalls"].status == "failed"
    assert by_name["faccessat"].status == "failed"


def test_parse_ltp_log_all_pass() -> None:
    log = """epoll01         1       TPASS   : ok
epoll02         1       TPASS   : ok
"""

    results = parse_ltp_log(log)

    assert len(results) == 2
    assert all(r.status == "passed" for r in results)


def test_parse_ltp_log_empty() -> None:
    results = parse_ltp_log("")
    assert results == []


def test_parse_mugen_results_dir_basic() -> None:
    listing = {
        "suite_name": "bash",
        "succeed": ["oe_test_bash_01", "oe_test_bash_02"],
        "failed": ["oe_test_bash_03"],
        "skipped": ["oe_test_bash_04"],
    }

    results = parse_mugen_results_dir(listing)

    assert len(results) == 4
    by_name = {r.sub_test_name: r for r in results}

    assert by_name["oe_test_bash_01"].status == "passed"
    assert by_name["oe_test_bash_02"].status == "passed"
    assert by_name["oe_test_bash_03"].status == "failed"
    assert by_name["oe_test_bash_04"].status == "skipped"


def test_parse_mugen_results_dir_empty() -> None:
    listing = {
        "suite_name": "bash",
        "succeed": [],
        "failed": [],
        "skipped": [],
    }

    results = parse_mugen_results_dir(listing)
    assert results == []

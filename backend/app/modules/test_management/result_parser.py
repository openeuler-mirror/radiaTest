# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import re
from dataclasses import dataclass

# Mugen/LTP/pkgmanage 结果解析器：把各类测试产物(ltp 日志、mugen results 目录
# 列表、pkgmanage 日志)归一化为 SubTestResult 列表，写 TestCaseRunDetail。
# 全部 best-effort：解析失败不应阻断任务，调用方已 try/except 吞掉。


@dataclass(frozen=True)
class SubTestResult:
    sub_test_name: str
    status: str


def parse_ltp_log(log_text: str) -> list[SubTestResult]:
    """从 ltp 日志按 "<name> <n> TPASS/TFAIL" 提取子测试结果。

    同名多次出现时只要一次 FAIL 即记 failed(失败优先)，避免重跑掩盖首败。
    """
    results_by_name: dict[str, str] = {}
    pattern = re.compile(r"^(\S+)\s+\d+\s+T(PASS|FAIL)\b", re.MULTILINE)
    for match in pattern.finditer(log_text):
        name = match.group(1)
        outcome = match.group(2)
        if name in results_by_name:
            if outcome == "FAIL" and results_by_name[name] != "failed":
                results_by_name[name] = "failed"
        else:
            results_by_name[name] = "passed" if outcome == "PASS" else "failed"
    return [
        SubTestResult(sub_test_name=name, status=status)
        for name, status in results_by_name.items()
    ]


def parse_mugen_results_dir(listing: dict) -> list[SubTestResult]:
    """把 mugen results 目录的 succeed/failed/skipped 列表转成子测试结果。"""
    results: list[SubTestResult] = []
    for name in listing.get("succeed", []):
        results.append(SubTestResult(sub_test_name=name, status="passed"))
    for name in listing.get("failed", []):
        results.append(SubTestResult(sub_test_name=name, status="failed"))
    for name in listing.get("skipped", []):
        results.append(SubTestResult(sub_test_name=name, status="skipped"))
    return results


def parse_pkgmanage_log(log_text: str) -> list[SubTestResult]:
    """从 pkgmanage 日志的 fail_list 段落提取失败的包名。"""
    failed: list[str] = []
    seen: set[str] = set()
    in_fail_section = False
    for line in log_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "no fail_list":
            return []
        if stripped.endswith(":") and line.startswith("    ") and not line.startswith("        "):
            in_fail_section = True
            continue
        if in_fail_section and line.startswith("        "):
            name = stripped
            if name and name not in seen:
                seen.add(name)
                failed.append(name)
    return [SubTestResult(sub_test_name=pkg, status="failed") for pkg in failed]

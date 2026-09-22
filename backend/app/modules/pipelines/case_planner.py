# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.test_management.models import MugenCase, TestEnvType

# Case-to-package 规划：把 update 仓库的源码包名映射成可执行的 mugen 用例。


@dataclass(frozen=True)
class CaseMatch:
    """一条命中的 mugen 用例，携带 suite/case/env_type 供 builder 分流到对应 env_set。"""

    suite_name: str
    case_name: str
    env_type: str


@dataclass(frozen=True)
class CasePlan:
    """plan_cases 的产物：按 env_type 拆分的待执行用例 + 没有对应用例的包名。

    no_case_packages 不会进 env_set 执行，而是由 builder 建成 NO_CASE 的
    TestCaseRun（挂第一个 env_set，run_case 阶段跳过），用于在页面上呈现
    "该包无 mugen 用例"的事实，而不是静默丢弃。
    """

    vm_cases: list[CaseMatch]
    physical_cases: list[CaseMatch]
    no_case_packages: list[str]


def plan_cases(
    db: Session,
    *,
    packages: list[str],
    suite_name_prefix: str = "",
) -> CasePlan:
    """把包名列表规划成 (vm_cases, physical_cases, no_case_packages)。

    每个包名按 suite_name 精确匹配 mugen_cases 表：命中则按其 env_type 归入
    vm 或 physical 组；未命中则进 no_case_packages（保留事实，不静默丢弃）。
    入参为空时直接返回空三元组。
    """
    if not packages:
        return CasePlan(
            vm_cases=[],
            physical_cases=[],
            no_case_packages=[],
        )

    matched: list[CaseMatch] = []
    no_case: list[str] = []

    for pkg in packages:
        rows = db.execute(
            select(MugenCase).where(MugenCase.suite_name == pkg)
        ).scalars().all()

        if not rows:
            no_case.append(pkg)
            continue

        for row in rows:
            matched.append(CaseMatch(
                suite_name=row.suite_name,
                case_name=row.case_name,
                env_type=row.env_type,
            ))

    vm_cases = [m for m in matched if m.env_type == TestEnvType.VM.value]
    physical_cases = [m for m in matched if m.env_type == "physical"]

    return CasePlan(
        vm_cases=vm_cases,
        physical_cases=physical_cases,
        no_case_packages=no_case,
    )

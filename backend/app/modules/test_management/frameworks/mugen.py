# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.test_management.models import TestEnvType

# Mugen suite2cases 文档解析器：把 mugen 仓库的 JSON 文档归一化为
# MugenCaseDefinition 列表。容错设计——字段缺失或类型不符时取默认值，
# 不抛异常跳过该用例，避免单条脏数据阻断整次同步。


@dataclass(frozen=True)
class MugenCaseDefinition:
    suite_name: str
    case_name: str
    env_type: str = TestEnvType.VM.value
    node_num: int = 1
    add_disk_num: int = 0
    add_nic_num: int = 0
    raw_data: dict[str, object] = field(default_factory=dict)


def normalize_env_type(value: object) -> str:
    """把 mugen 的 machine type 归一化为 physical/vm/unknown。kvm 视作 vm。"""
    if value is None:
        return TestEnvType.VM.value
    normalized = str(value).strip().casefold()
    if normalized in {"", "vm", "kvm"}:
        return TestEnvType.VM.value
    if normalized in {"physical", "baremetal", "bare-metal"}:
        return "physical"
    return "unknown"


def positive_int(value: object, *, default: int = 0) -> int:
    """容错取正整数：非数字返回 default，负数截断为 0。"""
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, str) and value.strip().isdigit():
        return max(int(value.strip()), 0)
    return default


def boolish_count(value: object) -> int:
    """把 mugen 里形态各异的 add disk / add network interface 取值归一化为计数。

    mugen 文档里该字段可能是 true/"yes"/数字/列表，统一算成加磁盘/网卡数量。
    """
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"", "false", "no", "none", "0"}:
            return 0
        if normalized.isdigit():
            return max(int(normalized), 0)
        return 1
    if isinstance(value, list):
        return len(value)
    return 0


def lookup_case_value(
    case_data: dict[str, object], suite_data: dict[str, object], key: str
) -> object:
    if key in case_data:
        return case_data[key]
    return suite_data.get(key)


def parse_case_name(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("name", "case", "case_name"):
            name = value.get(key)
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def parse_suite_cases(
    *,
    suite_name: str,
    document: object,
) -> list[MugenCaseDefinition]:
    suite_name = suite_name.strip()
    if not suite_name:
        return []

    suite_data = document if isinstance(document, dict) else {}
    raw_cases = suite_data.get("cases") if isinstance(suite_data, dict) else document
    if raw_cases is None and isinstance(suite_data, dict):
        raw_cases = suite_data.get("case")
    if not isinstance(raw_cases, list):
        return []

    definitions: list[MugenCaseDefinition] = []
    for raw_case in raw_cases:
        case_name = parse_case_name(raw_case)
        if case_name is None:
            continue
        case_data = raw_case if isinstance(raw_case, dict) else {}
        env_type = normalize_env_type(lookup_case_value(case_data, suite_data, "machine type"))
        node_num = positive_int(
            lookup_case_value(case_data, suite_data, "machine num"),
            default=1,
        )
        definitions.append(
            MugenCaseDefinition(
                suite_name=suite_name,
                case_name=case_name,
                env_type=env_type,
                node_num=max(node_num, 1),
                add_disk_num=boolish_count(
                    lookup_case_value(case_data, suite_data, "add disk")
                ),
                add_nic_num=boolish_count(
                    lookup_case_value(case_data, suite_data, "add network interface")
                ),
                raw_data=dict(case_data),
            )
        )
    return definitions


def parse_suite_documents(suites: dict[str, object]) -> list[MugenCaseDefinition]:
    """解析全部 suite 文档，返回按 (suite_name, case_name) 排序的用例定义列表。"""
    definitions: list[MugenCaseDefinition] = []
    for suite_name, document in suites.items():
        definitions.extend(parse_suite_cases(suite_name=suite_name, document=document))
    return sorted(definitions, key=lambda item: (item.suite_name, item.case_name))

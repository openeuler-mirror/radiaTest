# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""RPM 文件名解析与版本比较工具（复刻 radiaTest/pkg_compare 生产语义）。

对外比对口径与负责人交付工具 `atomgit.com/zjl_long/pkg_compare` 逐项一致：
- compare_str_version：按 `.` 分段、数字段按数值、`oe*` 段逐字符特判（0/1/2）；
- 键：binary/source 用 `name.arch`（source 用 name），同名多版本取最高；
- 重复包（同名同架构多版本）单独收集。

不采用 rpmvercmp：会改变对外比对口径、破坏与交付对账（见 ADR 0041）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RpmCompareStatus(StrEnum):
    SAME = "SAME"
    VER_UP = "VER_UP"
    VER_DOWN = "VER_DOWN"
    REL_UP = "REL_UP"
    REL_DOWN = "REL_DOWN"
    ADD = "ADD"
    DEL = "DEL"
    LACK = "LACK"
    DIFFERENT = "DIFFERENT"
    ERROR = "ERROR"
    REPEAT = "REPEAT"


@dataclass(frozen=True)
class RpmName:
    name: str
    version: str
    release: str
    arch: str
    file: str

    @classmethod
    def parse(cls, rpm_file_name: str) -> RpmName | None:
        """解析 <name>-<version>-<release>.<arch>.rpm；格式不符返回 None。"""
        if not rpm_file_name:
            return None
        body = rpm_file_name.strip().rsplit(".", 2)
        if len(body) != 3 or body[-1] != "rpm":
            return None
        head = body[0].rsplit("-", 2)
        if len(head) != 3:
            return None
        name, version, release = head
        return cls(
            name=name, version=version, release=release,
            arch=body[1], file=rpm_file_name.strip(),
        )


def compare_str_version(version_a: str, version_b: str) -> int:
    """生产语义版本比较：0 相等 / 1 a>b / 2 a<b。

    e.g. v1.11.1 < 1.12.1；4.oe2203sp1 < 4.oe2209。
    """
    va = version_a.split(".")
    vb = version_b.split(".")
    cnt = max(len(va), len(vb))
    for i in range(cnt):
        if i == len(va):
            return 2
        if i == len(vb):
            return 1
        if va[i] == vb[i]:
            continue
        if va[i].startswith("oe") and vb[i].startswith("oe"):
            ta, tb = va[i], vb[i]
            for j in range(min(len(ta), len(tb))):
                if ta[j] != tb[j]:
                    return 1 if ta[j] > tb[j] else 2
            if len(ta) != len(tb):
                return 1 if len(ta) > len(tb) else 2
            continue
        a_num = int("".join(ch for ch in va[i] if ch.isdigit()) or "-1")
        b_num = int("".join(ch for ch in vb[i] if ch.isdigit()) or "-1")
        if a_num != b_num:
            return 1 if a_num > b_num else 2
    return 0


def select_high_pkg(pkg_list: list[RpmName]) -> RpmName:
    """同名同架构多版本中取版本最高项（version 优先，再 release）。"""
    max_index = 0
    for index, rpm in enumerate(pkg_list):
        if index == 0:
            continue
        is_eq = compare_str_version(pkg_list[max_index].version, rpm.version)
        if is_eq == 0:
            if compare_str_version(pkg_list[max_index].release, rpm.release) == 2:
                max_index = index
        elif is_eq == 2:
            max_index = index
    return pkg_list[max_index]


def rpmlist2rpmdict(
    rpmlist: list[str],
    *,
    arch: str | None = None,
) -> tuple[dict[str, list[RpmName]], dict[str, list[RpmName]]]:
    """解析清单为 {key: [RpmName]}。

    arch 为 None（binary/source 合并全量）时 key=name.arch，重复包单独收集并保留最高版；
    arch 指定（同名异构）时 key=name，只保留该架构与 noarch。
    """
    rpm_dict: dict[str, list[RpmName]] = {}
    for rpm_name in rpmlist:
        info = RpmName.parse(rpm_name)
        if info is None:
            continue
        if arch and info.arch not in (arch, "noarch"):
            continue
        key = info.name if arch else f"{info.name}.{info.arch}"
        rpm_dict.setdefault(key, []).append(info)

    repeat_map: dict[str, list[RpmName]] = {}
    for key, val in rpm_dict.items():
        if len(val) > 1:
            repeat_map[key] = val
            rpm_dict[key] = [select_high_pkg(val)]
    return rpm_dict, repeat_map


def rpmlist2rpmdict_by_name(rpmlist: list[str]) -> dict[str, list[RpmName]]:
    rpm_dict: dict[str, list[RpmName]] = {}
    for rpm_name in rpmlist:
        info = RpmName.parse(rpm_name)
        if info is None:
            continue
        rpm_dict.setdefault(info.name, []).append(info)
    return rpm_dict


def _get_first(rpm_dict: dict[str, list[RpmName]], key: str) -> RpmName | None:
    val = rpm_dict.get(key)
    return val[0] if val else None


def compare_rpm_name_cls(r1: RpmName | None, r2: RpmName | None) -> str:
    if r1 is not None and r2 is not None:
        if r1.version == r2.version:
            if r1.release == r2.release:
                return RpmCompareStatus.SAME.value
            return (
                RpmCompareStatus.REL_DOWN.value
                if compare_str_version(r1.release, r2.release) == 1
                else RpmCompareStatus.REL_UP.value
            )
        return (
            RpmCompareStatus.VER_DOWN.value
            if compare_str_version(r1.version, r2.version) == 1
            else RpmCompareStatus.VER_UP.value
        )
    if r1 is not None:
        return RpmCompareStatus.DEL.value
    if r2 is not None:
        return RpmCompareStatus.ADD.value
    return RpmCompareStatus.ERROR.value


def compare_rpm_dict(
    dict1: dict[str, list[RpmName]],
    dict2: dict[str, list[RpmName]],
) -> list[dict[str, str]]:
    """binary/source 轮次间对比：key 并集逐项得出
    {arch, rpm_list_1, rpm_list_2, compare_result}。
    """
    rows: list[dict[str, str]] = []
    for key in set(dict1) | set(dict2):
        r1 = _get_first(dict1, key)
        r2 = _get_first(dict2, key)
        rows.append(
            {
                "arch": (r1.arch if r1 else r2.arch) or "",
                "rpm_list_1": r1.file if r1 else "",
                "rpm_list_2": r2.file if r2 else "",
                "compare_result": compare_rpm_name_cls(r1, r2),
            }
        )
    return rows


def compare_rpm_dict2(
    dict1: dict[str, list[RpmName]],
    dict2: dict[str, list[RpmName]],
) -> list[dict[str, str]]:
    """同名异构：同一轮内 x86_64 vs aarch64 同名包一致/不同/缺失。

    dict1 为 x86 侧（rpm_x86），dict2 为 aarch64 侧（rpm_arm）。
    """
    rows: list[dict[str, str]] = []
    for key in set(dict1) | set(dict2):
        r1 = _get_first(dict1, key)
        r2 = _get_first(dict2, key)
        if r1 is None or r2 is None:
            status = RpmCompareStatus.LACK.value
        else:
            status = (
                RpmCompareStatus.SAME.value
                if r1.version == r2.version and r1.release == r2.release
                else RpmCompareStatus.DIFFERENT.value
            )
        rows.append(
            {
                "rpm_name": key,
                "rpm_x86": r1.file if r1 else "",
                "rpm_arm": r2.file if r2 else "",
                "compare_result": status,
            }
        )
    return rows

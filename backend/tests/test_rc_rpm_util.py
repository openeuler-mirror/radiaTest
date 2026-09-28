# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""rpm_util T3 测试：解析、版本比较语义（含 oe*/数字特判）、多版本取高、
重复包收集、compare_rpm_dict / compare_rpm_dict2 状态。
"""

from __future__ import annotations

from app.modules.rc_management.rpm_util import (
    RpmName,
    compare_rpm_dict,
    compare_rpm_dict2,
    compare_rpm_name_cls,
    compare_str_version,
    rpmlist2rpmdict,
    rpmlist2rpmdict_by_name,
    select_high_pkg,
)


def test_parse_rpm_file_name() -> None:
    info = RpmName.parse("kernel-6.18.0-0.rc2.oe2609.x86_64.rpm")
    assert info is not None
    assert (info.name, info.version, info.release, info.arch) == (
        "kernel",
        "6.18.0",
        "0.rc2.oe2609",
        "x86_64",
    )
    assert RpmName.parse("bad-name.rpm") is None
    assert RpmName.parse("") is None


def test_compare_str_version_semantics() -> None:
    # 数字段数值比较：单→双位数不误判
    assert compare_str_version("8.oe2609", "10.oe2609") == 2
    assert compare_str_version("10", "8") == 1
    # 普通数字版本
    assert compare_str_version("0.19.3", "0.19.4") == 2
    assert compare_str_version("0.19.4", "0.19.4") == 0
    # oe* 段逐字符特判
    assert compare_str_version("4.oe2203sp1", "4.oe2209") == 2
    assert compare_str_version("4.oe2209", "4.oe2203sp1") == 1
    # 字母版本段 vs 数字
    assert compare_str_version("rc1", "rc2") == 2


def test_multiversion_select_high() -> None:
    low = RpmName.parse("llvm-bolt-17.0.6-9.oe2609.x86_64.rpm")
    high = RpmName.parse("llvm-bolt-17.0.6-67.oe2609.x86_64.rpm")
    assert low is not None and high is not None
    assert select_high_pkg([low, high]) == high


def test_rpmlist2rpmdict_repeat_and_high() -> None:
    names = [
        "llvm-bolt-17.0.6-9.oe2609.x86_64.rpm",
        "llvm-bolt-17.0.6-67.oe2609.x86_64.rpm",
        "llvm-bolt-17.0.6-9.oe2609.aarch64.rpm",
        "kernel-6.18.0-0.rc2.oe2609.x86_64.rpm",
    ]
    d, repeats = rpmlist2rpmdict(names)
    # repeat：只收集同名同架构多版本的 name.arch
    assert "llvm-bolt.x86_64" in repeats
    assert len(repeats["llvm-bolt.x86_64"]) == 2
    assert "llvm-bolt.aarch64" not in repeats
    # 去重后保留最高版
    assert d["llvm-bolt.x86_64"][0].release == "67.oe2609"

    # arch 指定：key=name，只留该架构+noarch
    d2, _ = rpmlist2rpmdict(names, arch="x86_64")
    assert "llvm-bolt" in d2
    assert "kernel" in d2


def test_compare_rpm_dict_statuses() -> None:
    base = [
        "aide-0.19.3-1.oe2609.x86_64.rpm",
        "libxcrypt-4.4.36-1.oe2609.x86_64.rpm",
        "oldpkg-1-1.oe2609.x86_64.rpm",
    ]
    target = [
        "aide-0.19.4-1.oe2609.x86_64.rpm",
        "libxcrypt-4.4.36-2.oe2609.x86_64.rpm",
        "newpkg-1-1.oe2609.x86_64.rpm",
    ]
    d1, _ = rpmlist2rpmdict(base)
    d2, _ = rpmlist2rpmdict(target)
    result = {r["compare_result"] for r in compare_rpm_dict(d1, d2)}
    assert result == {"VER_UP", "REL_UP", "DEL", "ADD"}


def test_compare_rpm_dict2_isomer() -> None:
    x86 = ["libogg-devel-1.3.6-1.oe2609.x86_64.rpm", "only-x86-1-1.oe2609.x86_64.rpm"]
    arm = ["libogg-devel-1.3.6-1.oe2609.aarch64.rpm", "libogg-devel-1.3.7-1.oe2609.aarch64.rpm"]
    rows = compare_rpm_dict2(
        rpmlist2rpmdict_by_name(x86), rpmlist2rpmdict_by_name(arm)
    )
    status_by_name = {r["rpm_name"]: r["compare_result"] for r in rows}
    assert status_by_name["libogg-devel"] == "SAME"
    assert status_by_name["only-x86"] == "LACK"


def test_compare_rpm_name_cls_relative() -> None:
    a = RpmName.parse("fence-agents-4.17.0-8.oe2609.x86_64.rpm")
    b = RpmName.parse("fence-agents-4.17.0-10.oe2609.x86_64.rpm")
    assert compare_rpm_name_cls(a, b) == "REL_UP"  # 8→10 是升级，非 REL_DOWN
    assert compare_rpm_name_cls(None, b) == "ADD"
    assert compare_rpm_name_cls(a, None) == "DEL"
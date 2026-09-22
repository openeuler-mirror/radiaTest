# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""危险用例识别：把"在活体机器上执行会关机/重启/打死机器"的用例拦在流水线外。

背景：mugen systemd suite 的部分用例(如 oe_test_service_initrd-cleanup)脚本
故意伪造 /etc/initrd-release 绕过 systemd ConditionPathExists 保护，强行启动
会 isolate 到 switch-root 的单元，导致被 SSH 驱动的流水线 VM 永久挂死
(2026-09-08 prod 14 个任务异常的根因)。

三道判据命中任一即判危险：
1. 名字规则——用例名对应 systemd 单元名，关机重启类单元是固定集合；
2. 高精度脚本扫描——只匹配几乎不可能误报的模式，宁漏勿误伤(误伤是静默的，
   会无声缩水测试覆盖；漏网是可见失败，可快速补名单)；
3. 内置兜底名单——规则覆盖不到的个例，走代码发版维护，不建管理界面。

不可破坏约束：误伤一个正常用例的代价是静默丢失测试覆盖，因此新增模式必须
先证明对现有索引零误伤。
"""

from __future__ import annotations

import re

# 内置兜底名单：精确用例名。2026-09-08 事故的元凶预置在内，规则覆盖不到的
# 新个例经代码评审后追加。
EXTRA_DANGEROUS_CASES: frozenset[str] = frozenset(
    {
        "oe_test_service_initrd-cleanup",
        "oe_test_service_initrd-parse-etc",
        "oe_test_service_initrd-switch-root",
        "oe_test_service_initrd-udevadm-cleanup-db",
    }
)

# 精确危险单元集合(用例名去掉 oe_test_ 前缀和 service/target/socket 等类型段
# 后的单元名)。整词匹配,不做子串,避免误伤 pcp-reboot-init 之类无辜用例。
_DANGEROUS_UNITS: frozenset[str] = frozenset(
    {
        "reboot",
        "poweroff",
        "halt",
        "kexec",
        "shutdown",
        "suspend",
        "hibernate",
        "suspend-then-hibernate",
        "hybrid-sleep",
        "soft-reboot",
        "exit",
        "systemd-exit",
        "systemd-reboot",
        "systemd-poweroff",
        "systemd-halt",
        "systemd-kexec",
        "systemd-soft-reboot",
        "systemd-suspend",
        "systemd-hibernate",
        "systemd-suspend-then-hibernate",
        "systemd-hybrid-sleep",
        "telinit",
        "ctrl-alt-del",
        "runlevel0",
        "runlevel1",
        "runlevel2",
        "runlevel3",
        "runlevel4",
        "runlevel5",
        "runlevel6",
    }
)

# mugen 用例名里可能的类型段;不是类型段时整个剩余部分就是单元名。
_CASE_TYPE_WORDS: frozenset[str] = frozenset(
    {
        "service",
        "target",
        "socket",
        "timer",
        "path",
        "device",
        "mount",
        "automount",
        "slice",
        "scope",
        "swap",
    }
)

_INITRD_REASON = "危险单元:initrd 阶段专用单元,在正常运行系统上执行会触发 switch-root"
_UNIT_REASON = "危险单元:关机/重启/休眠类单元,在流水线机器上执行会终止系统"
_EXTRA_REASON = "内置危险用例名单命中"

# 高精度脚本扫描模式。只匹配命令位置的真实动作,注释/字符串/参数名不误伤。
_FORGE_INITRD_PATTERN = re.compile(
    r"\btouch\s+(?:.+\s+)?/etc/initrd-release\b|>\s*/etc/initrd-release\b"
)
_SYSTEMCTL_DESTRUCTIVE_PATTERN = re.compile(
    r"\bsystemctl\s+(?:--no-block\s+)?(?:-{1,2}[\w-]+\s+)*"
    r"(?:isolate|switch-root|kexec|halt|poweroff|reboot|suspend|hibernate)\b"
)
_BARE_SHUTDOWN_PATTERN = re.compile(r"^(?:sudo\s+)?(reboot|poweroff|halt|kexec)\b")
_COMMAND_SPLIT_PATTERN = re.compile(r"&&|\|\||;")

_FORGE_REASON = "脚本伪造 initrd 环境(/etc/initrd-release)"
_SYSTEMCTL_REASON = "脚本执行 systemctl isolate/switch-root/关机类命令"
_BARE_REASON = "脚本直接执行关机命令(reboot/poweroff/halt/kexec)"


def _unit_of(case_name: str) -> str:
    """从 oe_test_<type>_ <unit> 形态提取单元名;无类型段时取整个剩余部分。"""
    unit = case_name
    if unit.startswith("oe_test_"):
        unit = unit[len("oe_test_"):]
    first, sep, rest = unit.partition("_")
    if sep and first in _CASE_TYPE_WORDS:
        return rest
    return unit


def name_rule_reason(case_name: str) -> str | None:
    """名字规则 + 内置名单。危险返回稳定原因文本,安全返回 None。"""
    if case_name in EXTRA_DANGEROUS_CASES:
        return _EXTRA_REASON
    unit = _unit_of(case_name)
    if unit.startswith("initrd"):
        return _INITRD_REASON
    if unit in _DANGEROUS_UNITS:
        return _UNIT_REASON
    return None


def script_scan_reason(script_content: str) -> str | None:
    """高精度扫描用例脚本内容。危险返回原因,安全返回 None。

    精度约束：逐行匹配命令位置;注释行与字符串提及(如 LOG_INFO "reboot")
    不算;`systemctl start/restart <危险单元>` 不在此拦(由名字规则覆盖)。
    """
    for line in script_content.splitlines():
        if _FORGE_INITRD_PATTERN.search(line):
            return _FORGE_REASON
        if _SYSTEMCTL_DESTRUCTIVE_PATTERN.search(line):
            return _SYSTEMCTL_REASON
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if any(
            _BARE_SHUTDOWN_PATTERN.match(segment.strip())
            for segment in _COMMAND_SPLIT_PATTERN.split(stripped)
        ):
            return _BARE_REASON
    return None


def resolve_case_danger(case_name: str, *, scanned_reason: str | None) -> str | None:
    """合并判据：名字规则/内置名单优先,其次同步扫描标记。"""
    return name_rule_reason(case_name) or scanned_reason


def collect_dangerous_scan_reasons(
    repo_dir,  # noqa: ANN001 - Path;避免与 frameworks 模块循环导入
    suites: dict[str, object],
) -> dict[tuple[str, str], str]:
    """扫描 mugen 仓库内各 suite 的用例脚本，返回 {(suite, case): 原因}。

    只产出脚本扫描结果；名字规则在过滤时动态计算，不落库，便于规则随代码
    演进而不需要重新同步。suite 文档缺 path 字段或脚本文件不存在时跳过
    (此时该用例只有名字规则保护)。
    """
    from pathlib import Path

    from app.modules.test_management.frameworks.mugen import parse_suite_cases

    repo = Path(repo_dir)
    reasons: dict[tuple[str, str], str] = {}
    for suite_name, document in suites.items():
        if not isinstance(document, dict):
            continue
        raw_path = document.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        rel_path = raw_path.strip()
        if rel_path.startswith("$OET_PATH/"):
            rel_path = rel_path[len("$OET_PATH/"):]
        suite_dir = repo / rel_path.strip("/")
        for definition in parse_suite_cases(suite_name=suite_name, document=document):
            script = suite_dir / f"{definition.case_name}.sh"
            if not script.is_file():
                continue
            reason = script_scan_reason(
                script.read_text(encoding="utf-8", errors="replace")
            )
            if reason:
                reasons[(suite_name, definition.case_name)] = reason
    return reasons

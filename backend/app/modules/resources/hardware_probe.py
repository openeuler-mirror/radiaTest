# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""基于 SSH 的物理机硬件探测。

一次 SSH 往返执行一个以标记分隔的脚本，采集 lscpu / dmidecode / lsblk / uname
输出；``parse_probe_output`` 把它解析成 dict，由 ``apply_hardware_probe`` 写回
Resource + PhysicalResourceSpec。在 PXE 安装成功后(此时 SSH 已就绪)以及
手工"刷新硬件"API 中调用。
"""

from __future__ import annotations

import re

from app.modules.test_management.remote import RemoteRunOptions, RemoteTarget, run_ssh_command

PROBE_SCRIPT = """echo '===ARCH==='; uname -m
echo '===KERNEL==='; uname -r
echo '===OS==='; . /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-}"
echo '===CPU==='; lscpu 2>/dev/null
echo '===MEM==='; dmidecode -t memory 2>/dev/null
echo '===DISK==='; lsblk -dbPpo NAME,SIZE,TYPE,ROTA,MODEL 2>/dev/null
echo '===BOARD==='; dmidecode -t baseboard 2>/dev/null
echo '===MAC==='; ip link show | awk '/ether/{print $2}' | head -1
"""

_DISK_FIELD_RE = re.compile(r'(\w+)="([^"]*)"')


def _split_sections(output: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    name = ""
    buf: list[str] = []
    for line in output.splitlines():
        m = re.match(r"^===(\w+)===$", line)
        if m:
            if name:
                sections[name] = "\n".join(buf)
            name = m.group(1)
            buf = []
        else:
            buf.append(line)
    if name:
        sections[name] = "\n".join(buf)
    return sections


def _first_line(text: str) -> str | None:
    for line in text.splitlines():
        v = line.strip()
        if v:
            return v
    return None


def _grep(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _parse_cpu(cpu_text: str) -> dict[str, object]:
    model = _grep(cpu_text, r"^Model name:\s*(.+)$")
    count_raw = _grep(cpu_text, r"^CPU\(s\):\s*(\d+)$")
    return {
        "cpu_model": model,
        "cpu_count": int(count_raw) if count_raw else None,
    }


def _parse_memory(mem_text: str) -> dict[str, object]:
    groups: dict[tuple[str, str, str], int] = {}
    for block in re.split(r"^Handle ", mem_text, flags=re.MULTILINE):
        if "Memory Device" not in block:
            continue
        size_m = re.search(r"^\s*Size:\s*(\d+)\s*(\w+)", block, re.MULTILINE)
        if not size_m:
            continue
        size_str = f"{size_m.group(1)}{size_m.group(2)}"
        mtype = _grep(block, r"^\s*Type:\s*(\S+)") or ""
        speed = _grep(block, r"^\s*Speed:\s*(.+)$") or ""
        key = (size_str, mtype, speed)
        groups[key] = groups.get(key, 0) + 1
    if not groups:
        return {"memory_count": None, "memory_spec": None}
    count = sum(groups.values())
    parts = []
    for (size_str, mtype, speed), n in groups.items():
        fields = [f for f in (mtype, speed, size_str) if f]
        s = " ".join(fields)
        parts.append(f"{s} * {n}" if n > 1 else s)
    return {"memory_count": count or None, "memory_spec": ", ".join(parts) or None}


def _parse_disks(disk_text: str) -> dict[str, object]:
    buckets: dict[str, dict[tuple[str, int], int]] = {
        "hdd": {},
        "ssd": {},
        "ssd_card": {},
    }
    for line in disk_text.splitlines():
        fields = dict(_DISK_FIELD_RE.findall(line))
        if fields.get("TYPE") != "disk":
            continue
        size_bytes = int(fields.get("SIZE", "0") or "0")
        size_gb = size_bytes // (1024**3)
        model = fields.get("MODEL") or ""
        rota = fields.get("ROTA")
        name = fields.get("NAME", "")
        if rota == "1":
            bucket = buckets["hdd"]
        elif "nvme" in name.lower():
            bucket = buckets["ssd_card"]
        else:
            bucket = buckets["ssd"]
        key = (model, size_gb)
        bucket[key] = bucket.get(key, 0) + 1

    def _spec(bucket: dict[tuple[str, int], int]) -> str | None:
        if not bucket:
            return None
        parts = []
        for (model, size_gb), n in bucket.items():
            s = f"{model} {size_gb}GB".strip()
            parts.append(f"{s} * {n}" if n > 1 else s)
        return ", ".join(parts)

    return {
        "hdd_count": sum(buckets["hdd"].values()) or None,
        "hdd_spec": _spec(buckets["hdd"]),
        "ssd_count": sum(buckets["ssd"].values()) or None,
        "ssd_spec": _spec(buckets["ssd"]),
        "ssd_card_count": sum(buckets["ssd_card"].values()) or None,
        "ssd_card_spec": _spec(buckets["ssd_card"]),
    }


def parse_probe_output(output: str) -> dict[str, object]:
    sections = _split_sections(output)
    result: dict[str, object] = {
        "arch": _first_line(sections.get("ARCH", "")),
        "kernel_version": _first_line(sections.get("KERNEL", "")),
        "os_version": _first_line(sections.get("OS", "")),
    }
    result.update(_parse_cpu(sections.get("CPU", "")))
    result.update(_parse_memory(sections.get("MEM", "")))
    result.update(_parse_disks(sections.get("DISK", "")))
    result["board_sn"] = _grep(sections.get("BOARD", ""), r"^\s*Serial Number:\s*(\S+)")
    result["mac_address"] = _first_line(sections.get("MAC", ""))
    return result


def probe_physical_hardware(
    *,
    host: str,
    username: str,
    password: str,
    timeout_seconds: int = 60,
) -> dict[str, object]:
    """经 SSH 运行探测脚本并返回解析后的硬件字段。

    SSH 失败时抛 RuntimeError，由调用方决定是中止(手工刷新)还是跳过
    (安装后尽力而为)。
    """
    result = run_ssh_command(
        target=RemoteTarget(host=host, username=username, password=password),
        command="bash -s",
        stdin=PROBE_SCRIPT,
        timeout_seconds=timeout_seconds,
        options=RemoteRunOptions(verify_host_key=False, output_limit_bytes=512 * 1024),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"hardware probe SSH failed (exit={result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()[:200]}"
        )
    return parse_probe_output(result.stdout)

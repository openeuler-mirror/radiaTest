# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import os
import shlex
import subprocess

# VM 挂死诊断采集：通过宿主机 virsh 抓 domstate 与 console 输出，存为
# console_diagnostic 产物供排查。best-effort，采集失败只记占位文本不阻断。
# 物理机无宿主，改由 BMC(ipmitool) 抓 SEL/电源/传感器，BMC 独立于 OS，
# 整机挂死仍可读，用于区分真断电与 SSH 层窒息(ADR 0032/0042/0044)。
DIAGNOSTIC_TIMEOUT = 30


def bmc_power_on(*, bmc_ip: str, username: str, password: str) -> bool | None:
    """BMC 带外读取机箱电源状态（三态）。

    返回 True(电源开启)/False(电源关闭)/None(查询失败，不下结论)。
    判死只信电源状态：SEL 时间戳依赖 BMC 时钟（现场观测漂移可达小时级且
    会递增），且 BMC 会写入虚构的重启事件，均不可作为判据(ADR 0044 修订，
    job 10232 实证)。SEL 仍随取证产物原样采集，仅作人工排查参考。
    密码经 stdin 传入，与 capture_bmc_diagnostics 同一通道。
    """
    base = [
        "ipmitool",
        "-I", "lanplus",
        "-H", bmc_ip,
        "-U", username,
        "-f", "/dev/stdin",
        "-N", "10",
    ]
    ok_power, power_output = _run_ipmitool(
        [*base, "chassis", "power", "status"], password=password
    )
    if not ok_power:
        return None
    lowered = power_output.lower()
    if "off" in lowered:
        return False
    if "on" not in lowered:
        return None
    return True


def capture_bmc_diagnostics(*, bmc_ip: str, username: str, password: str) -> str:
    """抓取物理机 BMC 的 SEL 事件、电源状态与传感器快照，拼接返回。

    密码经 stdin(``-f /dev/stdin``)传入而非 argv，避免明文出现在进程列表。
    ipmitool 全部失败时返回占位说明；全部成功但无输出时返回空结果说明；
    部分失败保留已采集小节。
    """
    base = [
        "ipmitool",
        "-I", "lanplus",
        "-H", bmc_ip,
        "-U", username,
        "-f", "/dev/stdin",
        "-N", "10",
    ]
    sections = (
        ("ipmitool sel list", ("sel", "list")),
        ("ipmitool chassis status", ("chassis", "status")),
        ("ipmitool sdr elist", ("sdr", "elist")),
    )
    parts: list[str] = []
    failures = 0
    last_failure = ""
    for title, subcmd in sections:
        ok, output = _run_ipmitool([*base, *subcmd], password=password)
        if ok and output:
            parts.append(f"=== {title} ===\n{output}")
        elif ok:
            failures += 1  # 成功但空输出：不算失败，但也不产出小节
        else:
            failures += 1
            last_failure = output or last_failure
    if not parts:
        if failures == len(sections) and not last_failure:
            return "no BMC diagnostics output (empty SEL/sensors)"
        reason = f": {last_failure}" if last_failure else ""
        return f"failed to capture BMC diagnostics (ipmitool failed){reason}"
    return "\n\n".join(parts)


def _run_ipmitool(
    args: list[str], *, password: str, timeout: int = DIAGNOSTIC_TIMEOUT
) -> tuple[bool, str]:
    """执行单条 ipmitool 子命令，返回 (是否成功, 输出或失败原因)。

    密码经 stdin 首行交给 ``-f /dev/stdin``，不出现在 argv/输出中。
    环境钉死 ``LC_ALL=C``、``TZ=UTC``：ipmitool 的输出格式与 SEL 时间戳
    渲染随 locale/时区变化，钉死环境保证电源状态判定与 SEL 取证产物的
    输出确定性（不可破坏的约束，见 ADR 0044）。
    """
    try:
        completed = subprocess.run(
            args,
            input=f"{password}\n",
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except FileNotFoundError:
        return False, "ipmitool command not found"
    if completed.returncode != 0:
        # 部分子命令失败不影响其余小节，带出 stderr 便于定界。
        return False, (completed.stderr or f"ipmitool exit {completed.returncode}").strip()
    return True, (completed.stdout or "").strip()


def capture_vm_console_output(
    *,
    host_ip: str,
    vm_name: str,
    ssh_key_path: str,
) -> str:
    """抓取 VM 的 domstate 与 console 输出拼接返回。SSH 失败时返回占位说明。"""
    parts: list[str] = []

    domstate = _run_host_ssh(
        host_ip, ssh_key_path, f"virsh domstate {shlex.quote(vm_name)}"
    )
    if domstate:
        parts.append(f"=== virsh domstate ===\n{domstate}")

    console = _run_host_ssh(
        host_ip,
        ssh_key_path,
        f"virsh console {shlex.quote(vm_name)} --devnull",
        timeout=10,
    )
    if console:
        parts.append(f"=== virsh console ===\n{console}")

    if not parts:
        parts.append("failed to capture console output (SSH failed)")

    return "\n\n".join(parts)


# domstate 三态映射（ADR 0046）：活态含过渡态(in shutdown 等，下个确认周期
# 自然收敛)；死态为关机/崩溃/消亡。宿主查询失败或未识别输出一律 None，
# 不下结论——与 bmc_power_on 三态语义对齐。
_VM_DOMSTATE_ALIVE = frozenset(
    {
        "running",
        "idle",
        "paused",
        "in shutdown",
        "in migrate",
        "post-copy",
        "pmsuspended",
    }
)
_VM_DOMSTATE_DEAD = frozenset({"shut off", "shutted down", "crashed", "dying"})


def vm_domstate_alive(
    *, host_ip: str, vm_name: str, ssh_key_path: str
) -> bool | None:
    """宿主机带外读取 VM domstate（三态）。

    返回 True(domstate 活态)/False(关机/崩溃/消亡态)/None(查询失败或
    未识别输出，不下结论)。VM 的"机箱电源状态"等价物即 domstate。
    """
    state = _run_host_ssh(
        host_ip, ssh_key_path, f"virsh domstate {shlex.quote(vm_name)}"
    ).strip().lower()
    if state in _VM_DOMSTATE_ALIVE:
        return True
    if state in _VM_DOMSTATE_DEAD:
        return False
    return None


def vm_hard_reset(*, host_ip: str, vm_name: str, ssh_key_path: str) -> bool:
    """宿主机 virsh destroy + start 硬复位：等价拔电重启，磁盘状态保留。

    destroy 容忍失败（VM 可能已处于关机态）；复位后 domstate 活态即视为
    复位成功——真正的成功判据是调用方随后的 SSH 就绪等待。
    """
    _run_host_ssh(host_ip, ssh_key_path, f"virsh destroy {shlex.quote(vm_name)}")
    _run_host_ssh(host_ip, ssh_key_path, f"virsh start {shlex.quote(vm_name)}")
    return (
        vm_domstate_alive(
            host_ip=host_ip, vm_name=vm_name, ssh_key_path=ssh_key_path
        )
        is True
    )


def _run_host_ssh(
    host_ip: str,
    ssh_key_path: str,
    command: str,
    *,
    timeout: int = DIAGNOSTIC_TIMEOUT,
) -> str:
    args = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=accept-new",
        "-i", ssh_key_path,
        "-o", "IdentitiesOnly=yes",
        f"root@{host_ip}",
        command,
    ]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"timeout after {timeout}s"
    except FileNotFoundError:
        return "ssh command not found"

    if completed.returncode == 255:
        return f"SSH connection failed (exit {completed.returncode})"

    return (completed.stdout or "").strip()

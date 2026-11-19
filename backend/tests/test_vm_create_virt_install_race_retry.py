# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""验证 virt-install 域枚举竞争时的定向重试。"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("flock") is None, reason="requires Linux flock")

CREATE_VM_SH = Path(__file__).resolve().parents[1] / "app/modules/vms/host_scripts/create-vm.sh"
VM_NAME = "race-retry-vm"
RACE_STDERR = "ERROR Domain not found: no domain with matching uuid example"
OTHER_STDERR = "ERROR    Unknown --graphics options: ['websocket']"


def _write_stub(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _make_stubs(stub_dir: Path) -> None:
    stub_dir.mkdir(parents=True, exist_ok=True)
    # virt-install：--graphics=? 回应宿主 VNC WebSocket 能力探测（不计数）；真实调用按
    # KRONOS_VIRT_INSTALL_OUTCOMES 逐行脚本化结果（race / other / 其他视为成功），并把
    # 调用序号追加到 KRONOS_VIRT_INSTALL_CALLS。
    _write_stub(
        stub_dir / "virt-install",
        """#!/usr/bin/env bash
if [[ "$1" == "--graphics=?" ]]; then
  echo "--graphics options:"
  echo "  address.base"
  [[ "${KRONOS_STUB_GRAPHICS_WEBSOCKET:-}" == "1" ]] && echo "  websocket"
  exit 0
fi
count_file="$KRONOS_VIRT_INSTALL_CALLS"
count=0
[[ -s "$count_file" ]] && count="$(wc -l < "$count_file")"
echo "$((count + 1))" >> "$count_file"
outcome="$(sed -n "$((count + 1))p" "$KRONOS_VIRT_INSTALL_OUTCOMES")"
case "$outcome" in
  race)
    printf '%s\\n' "$KRONOS_STUB_RACE_STDERR" >&2
    exit 1
    ;;
  other)
    printf '%s\\n' "$KRONOS_STUB_RACE_STDERR"
    printf '%s\\n' "$KRONOS_STUB_OTHER_STDERR" >&2
    exit 1
    ;;
  stdout_only)
    printf '%s\\n' "$KRONOS_STUB_RACE_STDERR"
    exit 1
    ;;
esac
cat "$KRONOS_VIRT_INSTALL_XML"
exit 0
""",
    )
    _write_stub(
        stub_dir / "virsh",
        """#!/usr/bin/env bash
case "$1" in
  domstate) echo running ;;
  dumpxml) cat "$KRONOS_VIRSH_DUMPXML" ;;
  vncdisplay) echo ':0' ;;
  *) exit 0 ;;
esac
""",
    )
    _write_stub(
        stub_dir / "qemu-img",
        "#!/usr/bin/env bash\n"
        'if [[ "$1" == "info" ]]; then echo \'{"virtual-size": 8}\'; fi\n'
        'if [[ "$1" == "create" ]]; then touch "${@: -2:1}"; fi\n'
        "exit 0\n",
    )
    _write_stub(stub_dir / "curl", "#!/usr/bin/env bash\nexit 0\n")
    _write_stub(
        stub_dir / "free",
        "#!/usr/bin/env bash\n"
        "echo 'Mem total used free shared buff avail'\n"
        "echo 'Mem: 65536 1024 64512 0 0 64512'\n",
    )
    _write_stub(
        stub_dir / "df",
        "#!/usr/bin/env bash\n"
        "echo 'Filesystem 1G-blocks Used Available Use% Mounted'\n"
        "echo 'tmpfs 1000 1 999 1% /var/lib/libvirt/images'\n",
    )


def _payload(base_dir: Path, *, install_type: str) -> str:
    data = {
        "vm_uuid": "uuid-race-retry",
        "vm_name": VM_NAME,
        "install_type": install_type,
        "arch": "aarch64",
        "system_disk_size_gb": "8",
        "vcpu_count": "4",
        "memory_mb": "8192",
        "data_disk_count": "1",
        "data_disk_size_gb": "50",
        "extra_nic_num": "0",
        "dhcp_leases_url": "http://example.com/dhcp",
        "network_bridge": "br0",
    }
    data["image_url"] = "http://example.com/img.qcow2"
    data["cache_filename"] = "img.qcow2"
    return base64.b64encode(json.dumps(data).encode()).decode()


def _run_create(
    tmp_path: Path,
    *,
    install_type: str = "manual",
    outcomes: tuple[str, ...] = ("success",),
    host_supports_websocket: bool = False,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    base_dir = tmp_path / "kronos"
    (base_dir / "cache").mkdir(parents=True)
    (base_dir / "instances").mkdir(parents=True)
    # 缓存镜像已存在时跳过下载分支。
    (base_dir / "cache" / "img.qcow2").write_bytes(b"img")

    pre_patch = tmp_path / "virt-install.xml"
    pre_patch.write_text(
        "<domain type='kvm'>\n"
        f"  <name>{VM_NAME}</name>\n"
        "  <os><type arch='aarch64'>hvm</type></os>\n"
        "  <devices>\n"
        "    <interface type='bridge'>\n"
        "      <mac address='52:54:00:12:34:56'/>\n"
        "    </interface>\n"
        "    <graphics type='vnc' port='5901' listen='0.0.0.0'/>\n"
        "  </devices>\n"
        "</domain>\n"
    )
    dumpxml_file = tmp_path / "domain.xml"
    dumpxml_file.write_text(
        "<domain type='kvm'>\n"
        f"  <name>{VM_NAME}</name>\n"
        "  <devices>\n"
        "    <interface type='bridge'>\n"
        "      <mac address='52:54:00:12:34:56'/>\n"
        "    </interface>\n"
        "    <graphics type='vnc' port='5901' websocket='5700' listen='0.0.0.0'/>\n"
        "  </devices>\n"
        "</domain>\n"
    )
    outcomes_file = tmp_path / "outcomes"
    outcomes_file.write_text("\n".join(outcomes) + "\n")
    calls_file = tmp_path / "virt-install-calls"
    calls_file.write_text("")

    stub_dir = tmp_path / "stubs"
    _make_stubs(stub_dir)

    env = os.environ.copy()
    env.pop("BASH_ENV", None)
    env["KRONOS_BASE_DIR"] = str(base_dir)
    env["TMPDIR"] = str(tmp_path)
    env["PATH"] = f"{stub_dir}:{env['PATH']}"
    env["KRONOS_PAYLOAD_B64"] = _payload(base_dir, install_type=install_type)
    env["KRONOS_VIRT_INSTALL_XML"] = str(pre_patch)
    env["KRONOS_VIRSH_DUMPXML"] = str(dumpxml_file)
    env["KRONOS_VIRT_INSTALL_CALLS"] = str(calls_file)
    env["KRONOS_VIRT_INSTALL_OUTCOMES"] = str(outcomes_file)
    env["KRONOS_STUB_RACE_STDERR"] = RACE_STDERR
    env["KRONOS_STUB_OTHER_STDERR"] = OTHER_STDERR
    env["KRONOS_STUB_GRAPHICS_WEBSOCKET"] = "1" if host_supports_websocket else "0"

    result = subprocess.run(
        [str(CREATE_VM_SH)], env=env, capture_output=True, text=True, timeout=120
    )
    return result, calls_file.read_text().splitlines()


def _phases(stderr: str) -> list[str]:
    return [
        line.split("\t")[1]
        for line in stderr.splitlines()
        if line.startswith("KRONOS_EVENT\t") and len(line.split("\t")) >= 3
    ]


def _event_messages(stderr: str, phase: str) -> list[str]:
    prefix = f"KRONOS_EVENT\t{phase}\t"
    return [line[len(prefix):] for line in stderr.splitlines() if line.startswith(prefix)]


def test_manual_print_xml_retries_on_domain_enumeration_race(tmp_path: Path) -> None:
    """print-xml 首次命中域枚举竞态、第二次成功：整体成功且保留首次失败事实。"""
    result, calls = _run_create(tmp_path, outcomes=("race", "success"))

    assert result.returncode == 0, result.stdout + result.stderr
    body = json.loads(result.stdout.strip().splitlines()[-1])
    assert body["status"] == "success"
    assert len(calls) == 2, calls

    phases = _phases(result.stderr)
    assert phases.count("virt_install_retry") == 1, result.stderr
    assert phases.count("host_command_failed") == 1, result.stderr
    failure_events = _event_messages(result.stderr, "host_command_failed")
    assert failure_events[0].startswith("virt-install "), failure_events
    stderr_events = _event_messages(result.stderr, "host_command_stderr")
    assert any(RACE_STDERR in message for message in stderr_events), stderr_events


def test_manual_print_xml_does_not_retry_other_failure(tmp_path: Path) -> None:
    """非竞态错误不重试：virt-install 只调用一次，终态文案与错误码保持原样。"""
    result, calls = _run_create(tmp_path, outcomes=("other",))

    assert result.returncode == 1
    assert len(calls) == 1, calls
    body = json.loads(result.stdout.strip().splitlines()[-1])
    assert body["error_code"] == "vm_create_failed"
    assert "failed to generate VM XML" in body["error_message"]
    assert "virt_install_retry" not in _phases(result.stderr)
    assert _phases(result.stderr).count("host_command_failed") == 1, result.stderr


def test_manual_print_xml_does_not_retry_stdout_only_match(tmp_path: Path) -> None:
    """stderr 为空时，stdout 的匹配文本不触发重试。"""
    result, calls = _run_create(tmp_path, outcomes=("stdout_only",))

    assert result.returncode == 1
    assert len(calls) == 1, calls
    assert "virt_install_retry" not in _phases(result.stderr)


def test_manual_print_xml_stops_retrying_when_error_changes(tmp_path: Path) -> None:
    """重试中途转为非竞态错误时立即停止，终态报告最后一次失败的错误内容。

    补充覆盖，非新增行为：第 1 次竞态失败被重试，第 2 次失败不再是竞态特征，
    重试辅助直接返回失败。
    """
    result, calls = _run_create(tmp_path, outcomes=("race", "other"))

    assert result.returncode == 1
    assert len(calls) == 2, calls
    phases = _phases(result.stderr)
    assert phases.count("virt_install_retry") == 1, result.stderr
    # 每次真实失败恰好一条失败事实；第二次失败由终态 fail_command_output 报告，不重复。
    assert phases.count("host_command_failed") == 2, result.stderr

    body = json.loads(result.stdout.strip().splitlines()[-1])
    assert body["error_code"] == "vm_create_failed"
    assert "failed to generate VM XML" in body["error_message"]

    # 终态 fail_command_output 读 $VIRT_INSTALL_ERR_PATH（每次尝试重定向截断重写），
    # 报告的是最后一次尝试的 stderr，以 host_command_stderr 相位发出。
    stderr_events = _event_messages(result.stderr, "host_command_stderr")
    assert len(stderr_events) == 2, stderr_events
    assert RACE_STDERR in stderr_events[0], stderr_events
    assert OTHER_STDERR in stderr_events[-1], stderr_events
    assert "no domain with matching" not in stderr_events[-1], stderr_events


def test_manual_print_xml_exhausts_race_retries_with_unchanged_failure(tmp_path: Path) -> None:
    """竞态持续时最多尝试 3 次；耗尽后终态文案与错误码与改动前一致。"""
    result, calls = _run_create(tmp_path, outcomes=("race", "race", "race", "race"))

    assert result.returncode == 1
    assert len(calls) == 3, calls
    body = json.loads(result.stdout.strip().splitlines()[-1])
    assert body["error_code"] == "vm_create_failed"
    assert "failed to generate VM XML" in body["error_message"]
    assert _phases(result.stderr).count("virt_install_retry") == 2, result.stderr
    # 3 次真实失败恰好 3 条失败事实：最后一次由终态 fail_command_output 报告，不重复。
    assert _phases(result.stderr).count("host_command_failed") == 3, result.stderr

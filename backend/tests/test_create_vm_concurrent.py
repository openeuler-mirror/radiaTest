# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import base64
import json
import os
import subprocess
import threading
from pathlib import Path

CREATE_VM_SH = (
    Path(__file__).resolve().parents[1]
    / "app/modules/vms/host_scripts/create-vm.sh"
)


def _write_stub(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _make_stubs(stub_dir: Path) -> None:
    stub_dir.mkdir(parents=True, exist_ok=True)
    # virt-install：记录开始/结束时间戳、sleep 模拟耗时、输出最小 XML。
    _write_stub(
        stub_dir / "virt-install",
        "#!/usr/bin/env bash\n"
        'echo "$(date +%s.%N) start" >> "$KRONOS_VIRT_INSTALL_CALLS"\n'
        "sleep 0.5\n"
        'echo "<domain type=\\"kvm\\"><name>test</name></domain>"\n'
        'echo "$(date +%s.%N) end" >> "$KRONOS_VIRT_INSTALL_CALLS"\n',
    )
    _write_stub(stub_dir / "virsh", "#!/usr/bin/env bash\nexit 0\n")
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
    _write_stub(stub_dir / "cp", "#!/usr/bin/env bash\ntouch \"${@: -1}\"\nexit 0\n")


def _payload(vm_name: str) -> str:
    data = {
        "vm_uuid": f"uuid-{vm_name}",
        "vm_name": vm_name,
        "install_type": "auto",
        "image_url": "http://example.com/img.qcow2",
        "cache_filename": "img.qcow2",
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
    return base64.b64encode(json.dumps(data).encode()).decode()


def test_create_vm_serializes_virt_install_under_concurrency(tmp_path: Path) -> None:
    """并发创建多 VM 时 virt-install 必须串行（flock），否则并发 ensure storage
    pool 竞态 / stale domain lookup 导致 vm_create_failed。

    现场实锤：2026-08-05 10:00:22 / 10:03:38，91 宿主上 24.03-SP1/SP3/SP4 aarch64
    VM 并发创建，virt-install --print-xml 并发触发 pool 'instances' already exists
    与 stale SP4 domain not found。
    """
    base_dir = tmp_path / "kronos"
    (base_dir / "cache").mkdir(parents=True)
    (base_dir / "instances").mkdir(parents=True)
    (base_dir / "cache" / "img.qcow2").write_bytes(b"\x00")

    stub_dir = tmp_path / "stubs"
    _make_stubs(stub_dir)
    calls_file = tmp_path / "virt-install-calls"
    calls_file.write_text("")

    env = os.environ.copy()
    env["KRONOS_BASE_DIR"] = str(base_dir)
    env["KRONOS_VIRT_INSTALL_CALLS"] = str(calls_file)
    env["PATH"] = f"{stub_dir}:{env['PATH']}"

    def run_one(vm_name: str) -> None:
        env_vm = dict(env)
        env_vm["KRONOS_PAYLOAD_B64"] = _payload(vm_name)
        subprocess.run(
            ["/bin/bash", str(CREATE_VM_SH)],
            env=env_vm,
            capture_output=True,
            timeout=60,
        )

    threads = [
        threading.Thread(target=run_one, args=("vm-a",)),
        threading.Thread(target=run_one, args=("vm-b",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = calls_file.read_text().splitlines()
    starts = sorted(float(line.split()[0]) for line in lines if line.endswith("start"))
    ends = sorted(float(line.split()[0]) for line in lines if line.endswith("end"))
    assert len(starts) == 2 and len(ends) == 2, f"virt-install calls: {lines}"
    # 串行：第二个 start 不早于第一个 end（无时间重叠）
    assert starts[1] >= ends[0], f"virt-install calls overlap: starts={starts} ends={ends}"


def test_create_vm_cleanup_deletes_libvirt_volumes_on_failure(tmp_path: Path) -> None:
    """
    virt-install 失败时 cleanup 必须 virsh vol-delete 清 libvirt 卷记录，否则 stale
    卷累积导致 virt-install refresh pool 查 stale domain not found（报错1 根因）。
    """
    cache_dir = base_dir / "cache"
    instance_dir = base_dir / "instances"
    cache_dir.mkdir(parents=True)
    instance_dir.mkdir(parents=True)
    (cache_dir / "img.qcow2").write_bytes(b"\x00")

    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    _write_stub(stub_dir / "virt-install", "#!/usr/bin/env bash\nexit 1\n")
    virsh_log = tmp_path / "virsh-calls"
    virsh_log.write_text("")
    _write_stub(
        stub_dir / "virsh",
        f'#!/usr/bin/env bash\necho "$*" >> "{virsh_log}"\nexit 0\n',
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
        "#!/usr/bin/env bash\necho 'Mem total used free shared buff avail'\n"
        "echo 'Mem: 65536 1024 64512 0 0 64512'\n",
    )
    _write_stub(
        stub_dir / "df",
        "#!/usr/bin/env bash\necho 'Filesystem 1G-blocks Used Available Use% Mounted'\n"
        "echo 'tmpfs 1000 1 999 1% /var/lib/libvirt/images'\n",
    )
    _write_stub(stub_dir / "cp", '#!/usr/bin/env bash\ntouch "${@: -1}"\nexit 0\n')

    env = os.environ.copy()
    env["KRONOS_BASE_DIR"] = str(base_dir)
    env["PATH"] = f"{stub_dir}:{env['PATH']}"
    env["KRONOS_PAYLOAD_B64"] = _payload("vm-fail")
    subprocess.run(["/bin/bash", str(CREATE_VM_SH)], env=env, capture_output=True, timeout=60)

    calls = virsh_log.read_text()
    vol_delete_calls = [c for c in calls.splitlines() if "vol-delete" in c]
    assert len(vol_delete_calls) == 2, f"expected 2 vol-delete (system+data disk): {calls}"
    assert any("vol-delete --pool instances vm-fail.qcow2" in c for c in vol_delete_calls), calls
    assert any("vol-delete --pool instances vm-fail.1.qcow2" in c for c in vol_delete_calls), calls


def test_create_vm_lock_file_outside_instances_dir(tmp_path: Path) -> None:
    """
    锁文件必须在 BASE_DIR 不在 INSTANCE_DIR，避免被 libvirt instances pool 识别为
    volume（报错1 副根因：.kronos-create.lock 在 instances 目录被 pool 纳入）。
    """
    cache_dir = base_dir / "cache"
    instance_dir = base_dir / "instances"
    cache_dir.mkdir(parents=True)
    instance_dir.mkdir(parents=True)
    (cache_dir / "img.qcow2").write_bytes(b"\x00")

    stub_dir = tmp_path / "stubs"
    _make_stubs(stub_dir)
    calls_file = tmp_path / "virt-install-calls"
    calls_file.write_text("")

    env = os.environ.copy()
    env["KRONOS_BASE_DIR"] = str(base_dir)
    env["KRONOS_VIRT_INSTALL_CALLS"] = str(calls_file)
    env["PATH"] = f"{stub_dir}:{env['PATH']}"
    env["KRONOS_PAYLOAD_B64"] = _payload("vm-lock")
    subprocess.run(["/bin/bash", str(CREATE_VM_SH)], env=env, capture_output=True, timeout=60)

    assert not (instance_dir / ".kronos-create.lock").exists(), "lock file in instances dir"
    assert (base_dir / ".kronos-create.lock").exists(), "lock file not in base dir"

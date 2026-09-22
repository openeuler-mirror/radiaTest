# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from app.modules.resources.hardware_probe import parse_probe_output

SAMPLE = """===ARCH===
aarch64
===KERNEL===
6.6.0-159.4.3.154.oe2403sp4.aarch64
===OS===
openEuler 24.03 (LTS-SP4)
===CPU===
Architecture:        aarch64
CPU op-mode(s):      32-bit, 64-bit
CPU(s):              96
Model name:          HiSilicon Kunpeng 920
NUMA node(s):        4
===MEM===
Handle 0x0011, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0001
        Error Information Handle: Not Provided
        Total Width: 64 bits
        Data Width: 64 bits
        Size: 16 GB
        Form Factor: DIMM
        Set: 1
        Locator: A1
        Bank Locator: P0_Node0_Channel0_Dimm0
        Type: DDR4
        Speed: 2933 MT/s
Handle 0x0012, DMI type 17, 40 bytes
Memory Device
        Size: 16 GB
        Type: DDR4
        Speed: 2933 MT/s
Handle 0x0013, DMI type 17, 40 bytes
Memory Device
        Size: No Module Installed
===DISK===
NAME="/dev/sda" SIZE="480103981056" TYPE="disk" ROTA="1" MODEL="ST500LM030"
NAME="/dev/sda1" SIZE="524288000" TYPE="part" ROTA="1" MODEL=""
NAME="/dev/nvme0n1" SIZE="512110190592" TYPE="disk" ROTA="0" MODEL="Samsung NVMe SSD"
NAME="/dev/sdb" SIZE="2000398933504" TYPE="disk" ROTA="0" MODEL="Crucial MX500"
===BOARD===
Base Board Information
        Manufacturer: Huawei
        Product Name: BC11GSDE
        Serial Number: SL12345678
"""


def test_parse_arch_kernel_os():
    r = parse_probe_output(SAMPLE)
    assert r["arch"] == "aarch64"
    assert r["kernel_version"] == "6.6.0-159.4.3.154.oe2403sp4.aarch64"
    assert r["os_version"] == "openEuler 24.03 (LTS-SP4)"


def test_parse_cpu():
    r = parse_probe_output(SAMPLE)
    assert r["cpu_model"] == "HiSilicon Kunpeng 920"
    assert r["cpu_count"] == 96


def test_parse_memory_counts_modules_with_size():
    r = parse_probe_output(SAMPLE)
    assert r["memory_count"] == 2
    assert r["memory_spec"] == "DDR4 2933 MT/s 16GB * 2"


def test_parse_disks_classifies_hdd_ssd_nvme():
    r = parse_probe_output(SAMPLE)
    assert r["hdd_count"] == 1
    assert "ST500LM030" in r["hdd_spec"]
    assert "447GB" in r["hdd_spec"]
    assert r["ssd_count"] == 1
    assert "Crucial MX500" in r["ssd_spec"]
    assert r["ssd_card_count"] == 1
    assert "Samsung NVMe SSD" in r["ssd_card_spec"]
    assert "476GB" in r["ssd_card_spec"]


def test_parse_board_sn():
    r = parse_probe_output(SAMPLE)
    assert r["board_sn"] == "SL12345678"


def test_parse_empty_output_returns_none_fields():
    r = parse_probe_output("===ARCH===\n\n===END===\n")
    assert r["arch"] is None
    assert r["cpu_count"] is None
    assert r["hdd_count"] is None


def test_parse_disk_skips_partitions():
    r = parse_probe_output(
        '===DISK===\nNAME="/dev/sda1" SIZE="524288000" TYPE="part" ROTA="1" MODEL=""\n'
    )
    assert r["hdd_count"] is None
    assert r["ssd_count"] is None

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.modules.leases.models import ResourceLease
from app.modules.leases.service import get_active_leases_by_resource_id, lease_to_summary
from app.modules.resources.models import Resource

# 资源 CSV 导出：把序列化资源按固定列顺序写成 CSV 字符串，供下载。

BASE_EXPORT_FIELDS = [
    "resource_code",
    "resource_type",
    "name",
    "management_status",
    "connectivity_status",
    "occupancy_status",
    "is_critical",
    "primary_ip",
    "mac_address",
    "arch",
    "os_version",
    "kernel_version",
    "ssh_username",
    "ssh_password",
    "tags",
    "usage_scenario",
    "extra",
    "device_location",
    "device_distribution",
    "bmc_ip",
    "bmc_username",
    "bmc_password",
    "cpu_model",
    "cpu_count",
    "memory_count",
    "memory_spec",
    "hdd_count",
    "hdd_spec",
    "ssd_count",
    "ssd_spec",
    "ssd_card_count",
    "ssd_card_spec",
    "board_sn",
    "vm_name",
    "vnc_port",
    "vnc_websocket_port",
    "vcpu_count",
    "memory_mb",
    "disk_gb",
    "host_resource_id",
    "system_disk_path",
    "data_disk_count",
    "data_disk_size_gb",
    "data_disk_paths",
    "current_lease_id",
    "current_lease_user_id",
    "current_lease_username",
    "current_lease_purpose",
    "current_lease_expected_ends_at",
]


def csv_value(value: object) -> object:
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return "" if value is None else value


def resource_export_row(
    db: Session,
    resource: Resource,
    *,
    current_lease: ResourceLease | None,
) -> dict[str, object]:
    physical = resource.physical_spec
    virtual = resource.virtual_spec
    lease_summary = lease_to_summary(db, current_lease)
    row: dict[str, object] = {
        "resource_code": resource.resource_code,
        "resource_type": resource.resource_type,
        "name": resource.name,
        "management_status": resource.management_status,
        "connectivity_status": resource.connectivity_status,
        "occupancy_status": resource.occupancy_status,
        "is_critical": resource.is_critical,
        "primary_ip": resource.primary_ip,
        "mac_address": resource.mac_address,
        "arch": resource.arch,
        "os_version": resource.os_version,
        "kernel_version": resource.kernel_version,
        "ssh_username": resource.ssh_username,
        "ssh_password": decrypt_secret(resource.ssh_password_ciphertext),
        "tags": resource.tags,
        "usage_scenario": resource.usage_scenario,
        "extra": resource.extra,
        "device_location": getattr(physical, "device_location", None),
        "device_distribution": getattr(physical, "device_distribution", None),
        "bmc_ip": getattr(physical, "bmc_ip", None),
        "bmc_username": getattr(physical, "bmc_username", None),
        "bmc_password": decrypt_secret(
            physical.bmc_password_ciphertext if physical else None
        ),
        "cpu_model": getattr(physical, "cpu_model", None),
        "cpu_count": getattr(physical, "cpu_count", None),
        "memory_count": getattr(physical, "memory_count", None),
        "memory_spec": getattr(physical, "memory_spec", None),
        "hdd_count": getattr(physical, "hdd_count", None),
        "hdd_spec": getattr(physical, "hdd_spec", None),
        "ssd_count": getattr(physical, "ssd_count", None),
        "ssd_spec": getattr(physical, "ssd_spec", None),
        "ssd_card_count": getattr(physical, "ssd_card_count", None),
        "ssd_card_spec": getattr(physical, "ssd_card_spec", None),
        "board_sn": getattr(physical, "board_sn", None),
        "vm_name": getattr(virtual, "vm_name", None),
        "vnc_port": getattr(virtual, "vnc_port", None),
        "vnc_websocket_port": getattr(virtual, "vnc_websocket_port", None),
        "vcpu_count": getattr(virtual, "vcpu_count", None),
        "memory_mb": getattr(virtual, "memory_mb", None),
        "disk_gb": getattr(virtual, "disk_gb", None),
        "host_resource_id": getattr(virtual, "host_resource_id", None),
        "system_disk_path": getattr(virtual, "system_disk_path", None),
        "data_disk_count": getattr(virtual, "data_disk_count", None),
        "data_disk_size_gb": getattr(virtual, "data_disk_size_gb", None),
        "data_disk_paths": getattr(virtual, "data_disk_paths", None) or [],
        **lease_summary,
    }
    return row


def export_resources_csv(
    db: Session,
    resources: Iterable[Resource],
) -> str:
    resource_list = list(resources)
    active_leases = get_active_leases_by_resource_id(db, resource_list)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=BASE_EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for resource in resource_list:
        row = resource_export_row(
            db,
            resource,
            current_lease=active_leases.get(resource.id),
        )
        writer.writerow({field: csv_value(row.get(field)) for field in BASE_EXPORT_FIELDS})
    return "\ufeff" + output.getvalue()

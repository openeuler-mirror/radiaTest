# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from types import SimpleNamespace

from app.modules.assistant.service import AssistantContext
from app.modules.assistant.tools import resources as resource_tools
from app.modules.resources.models import ManagementStatus, OccupancyStatus, ResourceType


def test_search_resources_filters_and_never_returns_credentials(monkeypatch) -> None:
    resource = SimpleNamespace(
        id="resource-1",
        resource_code="SN001",
        resource_type=ResourceType.PHYSICAL,
        name="test-machine",
        arch="aarch64",
        os_version="openEuler-24.03-LTS",
        cpu_model="Kunpeng",
        cpu_count=16,
        vcpu_count=None,
        memory_mb=None,
        memory_spec="32G * 4",
        hdd_count=0,
        ssd_count=2,
        ssd_card_count=0,
        data_disk_count=None,
        tags=["ci"],
        management_status=ManagementStatus.ACTIVE,
        occupancy_status=OccupancyStatus.IDLE,
        current_lease_username=None,
        ssh_username="root",
        bmc_username="Administrator",
    )
    monkeypatch.setattr(resource_tools, "list_resources", lambda *_args, **_kwargs: [resource])
    monkeypatch.setattr(resource_tools, "serialize_resources", lambda *_args, **_kwargs: [resource])

    result = resource_tools.search_resources(
        SimpleNamespace(),
        AssistantContext(
            user=SimpleNamespace(id="user-1", username="te1", role="TE"),
            channel="feishu",
        ),
        {
            "resource_type": "physical",
            "arch": "aarch64",
            "min_cpu_cores": 8,
            "min_memory_gb": 64,
            "occupancy": "free",
        },
    )

    assert result["count"] == 1
    assert result["resources"][0]["memory_gb"] == 128
    assert "ssh_username" not in result["resources"][0]
    assert "bmc_username" not in result["resources"][0]

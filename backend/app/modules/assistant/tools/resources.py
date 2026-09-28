# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.modules.assistant.service import AssistantContext
from app.modules.assistant.tool_registry import AssistantTool, AssistantToolError
from app.modules.resources.models import ManagementStatus, OccupancyStatus, ResourceType
from app.modules.resources.schemas import ResourceListParams, ResourceRead
from app.modules.resources.service import list_resources, serialize_resources

# 助手只读工具：资源查询，按硬件/占用字段过滤，不暴露凭据等敏感字段。


class SearchResourcesArguments(BaseModel):
    resource_type: Literal["physical", "vm"] | None = None
    arch: str | None = Field(default=None, max_length=32)
    min_cpu_cores: int | None = Field(default=None, ge=1, le=4096)
    min_memory_gb: int | None = Field(default=None, ge=1, le=1_000_000)
    min_disk_count: int | None = Field(default=None, ge=1, le=128)
    tags: list[str] = Field(default_factory=list, max_length=10)
    occupancy: Literal["free", "occupied"] | None = None
    limit: int = Field(default=5, ge=1, le=20)


class ListMyResourcesArguments(BaseModel):
    limit: int = Field(default=10, ge=1, le=20)


def _memory_gb(resource: ResourceRead) -> int | None:
    """
    估算内存 GB：优先用 memory_mb 换算，否则从 memory_spec 文本里抽数字
    (形如 "2*16" 的通道数*单条 GB)。失败返回 None。
    """
    if resource.memory_mb is not None:
        return resource.memory_mb // 1024
    if not resource.memory_spec:
        return None
    numbers = [int(value) for value in re.findall(r"\d+", resource.memory_spec)]
    if not numbers:
        return None
    return numbers[0] * numbers[1] if len(numbers) > 1 else numbers[0]


def _resource_data(resource: ResourceRead) -> dict[str, Any]:
    return {
        "id": resource.id,
        "resource_code": resource.resource_code,
        "resource_type": resource.resource_type.value,
        "name": resource.name,
        "arch": resource.arch,
        "os_version": resource.os_version,
        "cpu_model": resource.cpu_model,
        "cpu_cores": resource.cpu_count or resource.vcpu_count,
        "memory_gb": _memory_gb(resource),
        "disk_count": (
            (resource.hdd_count or 0)
            + (resource.ssd_count or 0)
            + (resource.ssd_card_count or 0)
            if resource.resource_type == ResourceType.PHYSICAL
            else 1 + (resource.data_disk_count or 0)
        ),
        "tags": resource.tags,
        "management_status": resource.management_status.value,
        "occupancy_status": resource.occupancy_status.value,
        "current_lease_username": resource.current_lease_username,
    }


def search_resources(db: Session, _context: AssistantContext, raw: dict[str, Any]) -> dict:
    try:
        arguments = SearchResourcesArguments.model_validate(raw)
    except ValidationError as exc:
        raise AssistantToolError(f"Invalid search_resources arguments: {exc}") from exc
    resources = serialize_resources(
        db,
        list_resources(db, params=ResourceListParams(), limit=None),
    )
    requested_tags = {tag.casefold() for tag in arguments.tags}
    matches: list[dict[str, Any]] = []
    expected_type = {
        "physical": ResourceType.PHYSICAL,
        "vm": ResourceType.VIRTUAL,
    }.get(arguments.resource_type)
    for resource in resources:
        if expected_type and resource.resource_type != expected_type:
            continue
        if arguments.arch and (resource.arch or "").casefold() != arguments.arch.casefold():
            continue
        cores = resource.cpu_count or resource.vcpu_count or 0
        if arguments.min_cpu_cores and cores < arguments.min_cpu_cores:
            continue
        memory_gb = _memory_gb(resource) or 0
        if arguments.min_memory_gb and memory_gb < arguments.min_memory_gb:
            continue
        disk_count = (
            (resource.hdd_count or 0) + (resource.ssd_count or 0) + (resource.ssd_card_count or 0)
            if resource.resource_type == ResourceType.PHYSICAL
            else 1 + (resource.data_disk_count or 0)
        )
        if arguments.min_disk_count and disk_count < arguments.min_disk_count:
            continue
        resource_tags = {tag.casefold() for tag in resource.tags}
        if requested_tags and not requested_tags.issubset(resource_tags):
            continue
        wants_free = arguments.occupancy == "free"
        not_free_state = (
            resource.occupancy_status != OccupancyStatus.IDLE
            or resource.management_status != ManagementStatus.ACTIVE
        )
        if wants_free and not_free_state:
            continue
        if arguments.occupancy == "occupied" and (
            resource.occupancy_status != OccupancyStatus.OCCUPIED
        ):
            continue
        matches.append(_resource_data(resource))
        if len(matches) >= arguments.limit:
            break
    return {"count": len(matches), "resources": matches}


def list_my_resources(db: Session, context: AssistantContext, raw: dict[str, Any]) -> dict:
    try:
        arguments = ListMyResourcesArguments.model_validate(raw)
    except ValidationError as exc:
        raise AssistantToolError(f"Invalid list_my_resources arguments: {exc}") from exc
    resources = serialize_resources(
        db,
        list_resources(db, params=ResourceListParams(), limit=None),
    )
    mine = [
        _resource_data(resource)
        for resource in resources
        if resource.current_lease_user_id == context.user.id
    ][: arguments.limit]
    return {"count": len(mine), "resources": mine}


SEARCH_RESOURCES_TOOL = AssistantTool.from_function(
    name="search_resources",
    description="Search radiaTest resources using non-secret hardware and occupancy fields.",
    parameters=SearchResourcesArguments.model_json_schema(),
    execute=search_resources,
)

LIST_MY_RESOURCES_TOOL = AssistantTool.from_function(
    name="list_my_resources",
    description="List resources currently leased by the current radiaTest user.",
    parameters=ListMyResourcesArguments.model_json_schema(),
    execute=list_my_resources,
)

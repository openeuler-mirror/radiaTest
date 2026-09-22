# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.leases.models import ResourceLease
from app.modules.resources.models import (
    ManagementStatus,
    OccupancyStatus,
    Resource,
    ResourceType,
)
from app.modules.test_management.models import TestEnvNode, TestEnvSet, TestJob, TestJobStatus

_ACTIVE_TEST_JOB_STATUSES = {
    TestJobStatus.PENDING.value,
    TestJobStatus.PREPARING.value,
    TestJobStatus.RUNNING.value,
}


@dataclass(frozen=True)
class PhysicalTestUsage:
    """物理资源当前活动测试的公开关联，供调度、资源 API 和写操作保护复用。"""

    test_job_id: int


def active_physical_test_usages(
    db: Session,
    resource_ids: list[str],
) -> dict[str, PhysicalTestUsage]:
    """批量返回资源正在参与的非终态测试，终态历史节点不占用资源。"""
    if not resource_ids:
        return {}
    rows = db.execute(
        select(TestEnvNode.resource_id, TestJob.id)
        .join(TestEnvSet, TestEnvNode.env_set_id == TestEnvSet.id)
        .join(TestJob, TestEnvSet.job_id == TestJob.id)
        .join(Resource, TestEnvNode.resource_id == Resource.id)
        .where(
            TestEnvNode.resource_id.in_(resource_ids),
            Resource.resource_type == ResourceType.PHYSICAL.value,
            TestJob.status.in_(_ACTIVE_TEST_JOB_STATUSES),
        )
        .order_by(TestJob.created_at.desc())
    ).all()
    usages: dict[str, PhysicalTestUsage] = {}
    for resource_id, test_job_id in rows:
        if resource_id is not None and resource_id not in usages:
            usages[resource_id] = PhysicalTestUsage(test_job_id=test_job_id)
    return usages


def active_physical_test_usage(
    db: Session,
    resource_id: str,
) -> PhysicalTestUsage | None:
    """返回单台资源的活动测试关联。"""
    return active_physical_test_usages(db, [resource_id]).get(resource_id)


def has_available_owned_physical_resource(
    db: Session,
    *,
    actor_id: str,
    arch: str,
    usage_scenario: str,
) -> bool:
    """检查触发者是否有一台用途、架构匹配且未参与活动测试的物理机。"""
    active_resource_ids = (
        select(TestEnvNode.resource_id)
        .join(TestEnvSet, TestEnvNode.env_set_id == TestEnvSet.id)
        .join(TestJob, TestEnvSet.job_id == TestJob.id)
        .where(
            TestEnvNode.resource_id.is_not(None),
            TestJob.status.in_(_ACTIVE_TEST_JOB_STATUSES),
        )
    )
    statement = (
        select(Resource.id)
        .join(ResourceLease, Resource.current_lease_id == ResourceLease.id)
        .where(
            Resource.deleted_at.is_(None),
            Resource.resource_type == ResourceType.PHYSICAL.value,
            Resource.management_status == ManagementStatus.ACTIVE.value,
            Resource.occupancy_status == OccupancyStatus.OCCUPIED.value,
            Resource.arch == arch,
            Resource.usage_scenario == usage_scenario,
            ResourceLease.user_id == actor_id,
            ResourceLease.released_at.is_(None),
            Resource.id.not_in(active_resource_ids),
        )
        .limit(1)
    )
    return db.execute(statement).scalar_one_or_none() is not None


def has_matching_owned_physical_resource(
    db: Session,
    *,
    actor_id: str,
    arch: str,
    usage_scenario: str,
) -> bool:
    """检查匹配的自有机器是否存在；测试中或 PXE maintenance 的机器仍算存在。"""
    statement = (
        select(Resource.id)
        .join(ResourceLease, Resource.current_lease_id == ResourceLease.id)
        .where(
            Resource.deleted_at.is_(None),
            Resource.resource_type == ResourceType.PHYSICAL.value,
            Resource.management_status != ManagementStatus.DISABLED.value,
            Resource.occupancy_status == OccupancyStatus.OCCUPIED.value,
            Resource.arch == arch,
            Resource.usage_scenario == usage_scenario,
            ResourceLease.user_id == actor_id,
            ResourceLease.released_at.is_(None),
        )
        .limit(1)
    )
    return db.execute(statement).scalar_one_or_none() is not None


def claim_available_owned_physical_resource(
    db: Session,
    *,
    node: TestEnvNode,
    actor_id: str,
    arch: str,
    usage_scenario: str,
) -> Resource | None:
    """原子认领一台测试空闲自有机器，并先持久化节点关联作为测试占用事实。"""
    active_resource_ids = (
        select(TestEnvNode.resource_id)
        .join(TestEnvSet, TestEnvNode.env_set_id == TestEnvSet.id)
        .join(TestJob, TestEnvSet.job_id == TestJob.id)
        .where(
            TestEnvNode.resource_id.is_not(None),
            TestJob.status.in_(_ACTIVE_TEST_JOB_STATUSES),
        )
    )
    statement = (
        select(Resource)
        .join(ResourceLease, Resource.current_lease_id == ResourceLease.id)
        .where(
            Resource.deleted_at.is_(None),
            Resource.resource_type == ResourceType.PHYSICAL.value,
            Resource.management_status == ManagementStatus.ACTIVE.value,
            Resource.occupancy_status == OccupancyStatus.OCCUPIED.value,
            Resource.arch == arch,
            Resource.usage_scenario == usage_scenario,
            ResourceLease.user_id == actor_id,
            ResourceLease.released_at.is_(None),
            Resource.id.not_in(active_resource_ids),
        )
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    resource = db.execute(statement).scalars().first()
    if resource is None:
        return None
    node.resource_id = resource.id
    node.primary_ip = resource.primary_ip
    db.commit()
    return resource

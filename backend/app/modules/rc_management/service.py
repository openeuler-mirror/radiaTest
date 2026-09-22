# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""rc_management 领域服务：版本/里程碑 CRUD、pxe 装机源提示、序列化。

Router 为薄层；写路径的幂等/冲突校验在此层用唯一约束兜底。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.rc_management.errors import (
    InvalidBuildUrlError,
    MilestoneDuplicateError,
    MilestoneHasComparesError,
    MilestoneNotFoundError,
    VersionDuplicateError,
    VersionHasMilestonesError,
    VersionNotFoundError,
)
from app.modules.rc_management.models import (
    MilestoneCompare,
    ReleaseMilestone,
    Version,
    VersionStatus,
)
from app.modules.rc_management.schemas import (
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    VersionCreate,
    VersionRead,
    VersionUpdate,
)
from app.modules.resources.service import (
    get_base_kernel_variant,
    install_source_exists,
)

# build_url 中推导轮次标签：rcN_openeuler-<时间戳> 或 alpha_openeuler-<时间戳>
_PXE_ROUND_RE = re.compile(r"(?:rc\d+|[a-z]+)_openeuler-[0-9-]+")

# 轮次命名规则：第一轮 alpha，其后 rc1、rc2…（与交付/导出命名一致）
_ROUND_NAMES_ALPHA_FIRST = True


def round_tag(name: str) -> str:
    """轮次名 → dailybuild 构建目录标签：roundN 兼容映射为 rcN，其余原样。"""
    if name.startswith("round") and name[5:].isdigit():
        return "rc" + name[5:]
    return name


def auto_build_url(base_url: str, product: str, tag: str, kernel_variant: str) -> str:
    """
    按命名规则生成构建根 URL 模板（通配构建时间戳）：
    {base}/EBS-{product}/{tag}_openeuler-*/*-with-kernel-{variant}/
    抓取时由 pkglist_fetcher 列目录解析通配符，取最新匹配构建。
    """
    return (
        f"{base_url.rstrip('/')}/EBS-{product}/"
        f"{tag}_openeuler-*/*-with-kernel-{kernel_variant}/"
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def derive_pxe_round_label(build_url: str) -> str | None:
    m = _PXE_ROUND_RE.search(build_url)
    return m.group(0) if m else None


def validate_build_url(build_url: str) -> str:
    """
    构建根 URL 须指向配置的 dailybuild 根（SSRF 收敛）且含
    /EBS-<product>/<round>/<kernel-variant>/ 结构。
    """
    base = get_settings().rc_dailybuild_base_url.rstrip("/")
    if not build_url.startswith(base):
        raise InvalidBuildUrlError(build_url)
    if not re.search(r"/EBS-[^/]+/[^/]+/[^/]+/?$", build_url):
        raise InvalidBuildUrlError(build_url)
    return build_url


# ---------- 版本 ----------


def list_versions(
    db: Session, *, search: str | None, page: int, page_size: int
) -> tuple[list[VersionRead], int]:
    statement = select(Version).order_by(Version.created_at, Version.name)
    if search:
        statement = statement.where(Version.name.ilike(f"%{search}%"))
    count_stmt = select(func.count(Version.id))
    if statement.whereclause is not None:
        count_stmt = count_stmt.where(statement.whereclause)
    total = db.scalar(count_stmt) or 0
    versions = (
        db.execute(statement.offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return [version_read(db, v) for v in versions], total


def get_version(db: Session, version_id: str) -> Version:
    version = db.get(Version, version_id)
    if version is None:
        raise VersionNotFoundError(version_id)
    return version


def version_read(db: Session, version: Version) -> VersionRead:
    count = db.scalar(
        select(func.count(ReleaseMilestone.id)).where(ReleaseMilestone.version_id == version.id)
    )
    data = VersionRead.model_validate(version).model_dump()
    data["milestone_count"] = count or 0
    return VersionRead.model_validate(data)


def create_version(db: Session, payload: VersionCreate, *, created_by: str) -> VersionRead:
    if db.scalar(select(Version).where(Version.name == payload.name)):
        raise VersionDuplicateError(payload.name)
    version = Version(
        name=payload.name,
        version_type=payload.version_type,
        status=payload.status.value,
        start_time=payload.start_time,
        end_time=payload.end_time,
        remark=payload.remark,
        created_by=created_by,
    )
    db.add(version)
    db.flush()  # 先取 version.id，轮次骨架外键需要
    # 按数量自动生成轮次：alpha + rc1..rcN（N=rc_round_count），基准链到前一轮。
    # 每轮 7 天，从版本开始日期顺排；构建 URL 按命名规则自动生成通配模板，
    # 抓取时解析为最新匹配构建，亦可人工编辑为精确 URL。
    kvar = get_base_kernel_variant(db, version.name) or "6.6"
    previous: ReleaseMilestone | None = None
    total = payload.rc_round_count
    for i in range(total + 1):
        if i == 0:
            name, tag = "alpha", "alpha"
        else:
            name = f"rc{i}"
            tag = f"rc{i}"
        start = (
            payload.start_time + timedelta(days=7 * i) if payload.start_time else None
        )
        end = (
            payload.start_time + timedelta(days=7 * (i + 1))
            if payload.start_time
            else None
        )
        ms = ReleaseMilestone(
            version_id=version.id,
            name=name,
            kernel_variant=None,
            build_url=auto_build_url(
                get_settings().rc_dailybuild_base_url, version.name, tag, kvar
            ),
            pxe_round_label=tag,
            compare_base_milestone_id=previous.id if previous else None,
            start_time=start,
            end_time=end,
            created_by=created_by,
        )
        db.add(ms)
        db.flush()  # 取 ms.id 供下一轮的 compare_base 外键
        previous = ms
    db.commit()
    db.refresh(version)
    return version_read(db, version)


def update_version(db: Session, version_id: str, payload: VersionUpdate) -> VersionRead:
    version = get_version(db, version_id)
    if payload.name is not None and payload.name != version.name:
        if db.scalar(select(Version).where(Version.name == payload.name)):
            raise VersionDuplicateError(payload.name)
        version.name = payload.name
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name":
            continue
        setattr(version, field, value.value if isinstance(value, VersionStatus) else value)
    db.commit()
    db.refresh(version)
    return version_read(db, version)


def delete_version(db: Session, version_id: str) -> None:
    version = get_version(db, version_id)
    has_compares = db.scalar(
        select(func.count(MilestoneCompare.id))
        .join(ReleaseMilestone, MilestoneCompare.milestone_id == ReleaseMilestone.id)
        .where(ReleaseMilestone.version_id == version.id)
    )
    if has_compares:
        raise VersionHasMilestonesError(version.name)
    # 无比对记录：骨架轮次随之级联删除（ORM cascade），可重建
    db.delete(version)
    db.commit()


# ---------- 里程碑 ----------


def latest_compare(db: Session, milestone_id: str) -> dict[str, object] | None:
    compare = db.scalar(
        select(MilestoneCompare)
        .where(MilestoneCompare.milestone_id == milestone_id)
        .order_by(MilestoneCompare.created_at.desc(), MilestoneCompare.id.desc())
        .limit(1)
    )
    if compare is None:
        return None
    return {
        "id": compare.id,
        "status": compare.status,
        "total_changed": compare.total_changed,
        "completed_at": compare.completed_at,
    }


def has_pxe_source(db: Session, version: Version, tag: str | None) -> bool:
    if not tag:
        return False
    return install_source_exists(db, os_version=version.name, round_label=tag)


def milestone_read(db: Session, ms: ReleaseMilestone) -> MilestoneRead:
    base_name = None
    if ms.compare_base_milestone_id:
        base = db.get(ReleaseMilestone, ms.compare_base_milestone_id)
        base_name = base.name if base else None
    data = {**ms.__dict__}
    data["compare_base_name"] = base_name
    data["has_pxe_source"] = has_pxe_source(db, ms.version, ms.name)
    data["latest_compare"] = latest_compare(db, ms.id)
    return MilestoneRead.model_validate(data)


def list_milestones(
    db: Session, version_id: str, *, search: str | None = None
) -> list[MilestoneRead]:
    statement = (
        select(ReleaseMilestone)
        .where(ReleaseMilestone.version_id == version_id)
        .order_by(ReleaseMilestone.created_at, ReleaseMilestone.name)
    )
    if search:
        statement = statement.where(ReleaseMilestone.name.ilike(f"%{search}%"))
    ms_list = db.execute(statement).scalars().all()
    return [milestone_read(db, m) for m in ms_list]


def create_milestone(db: Session, payload: MilestoneCreate, *, created_by: str) -> MilestoneRead:
    version = get_version(db, payload.version_id)
    if payload.build_url:
        validate_build_url(payload.build_url)
    if db.scalar(
        select(ReleaseMilestone).where(
            ReleaseMilestone.version_id == version.id,
            ReleaseMilestone.name == payload.name,
        )
    ):
        raise MilestoneDuplicateError(payload.name)
    if payload.compare_base_milestone_id and not db.get(
        ReleaseMilestone, payload.compare_base_milestone_id
    ):
        raise MilestoneNotFoundError(payload.compare_base_milestone_id)
    # 比对基准默认前一轮（Spec 语义）：未显式指定时取该版本最新轮次
    if payload.compare_base_milestone_id is None:
        latest = db.scalar(
            select(ReleaseMilestone)
            .where(ReleaseMilestone.version_id == version.id)
            .order_by(ReleaseMilestone.created_at.desc(), ReleaseMilestone.name.desc())
            .limit(1)
        )
        payload = payload.model_copy(
            update={"compare_base_milestone_id": latest.id if latest else None}
        )
    ms = ReleaseMilestone(
        version_id=version.id,
        name=payload.name,
        kernel_variant=payload.kernel_variant,
        build_url=payload.build_url,
        pxe_round_label=derive_pxe_round_label(payload.build_url)
        if payload.build_url
        else None,
        compare_base_milestone_id=payload.compare_base_milestone_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        created_by=created_by,
    )
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return milestone_read(db, ms)


def update_milestone(db: Session, milestone_id: str, payload: MilestoneUpdate) -> MilestoneRead:
    ms = get_milestone(db, milestone_id)
    changes = payload.model_dump(exclude_unset=True)
    if "compare_base_milestone_id" in changes and changes["compare_base_milestone_id"]:
        if not db.get(ReleaseMilestone, changes["compare_base_milestone_id"]):
            raise MilestoneNotFoundError(changes["compare_base_milestone_id"])
    if changes.get("name") and changes["name"] != ms.name:
        if db.scalar(
            select(ReleaseMilestone).where(
                ReleaseMilestone.version_id == ms.version_id,
                ReleaseMilestone.name == changes["name"],
            )
        ):
            raise MilestoneDuplicateError(changes["name"])
    build_url = changes.get("build_url")
    if build_url:
        validate_build_url(build_url)
        changes["pxe_round_label"] = derive_pxe_round_label(build_url)
    for field, value in changes.items():
        setattr(ms, field, value)
    db.commit()
    db.refresh(ms)
    return milestone_read(db, ms)


def get_milestone(db: Session, milestone_id: str) -> ReleaseMilestone:
    ms = db.get(ReleaseMilestone, milestone_id)
    if ms is None:
        raise MilestoneNotFoundError(milestone_id)
    return ms


def delete_milestone(db: Session, milestone_id: str) -> None:
    ms = get_milestone(db, milestone_id)
    if db.scalar(select(MilestoneCompare).where(MilestoneCompare.milestone_id == milestone_id)):
        raise MilestoneHasComparesError(ms.name)
    count = db.scalar(
        select(func.count(ReleaseMilestone.id)).where(
            ReleaseMilestone.compare_base_milestone_id == milestone_id
        )
    )
    if count:
        from app.modules.rc_management.errors import MilestoneHasComparesError as _Err

        raise _Err(f"{ms.name} 被作为比对基准，先解除引用")
    db.delete(ms)
    db.commit()


# ---------- 比对实例 ----------


def create_compare(
    db: Session,
    milestone_id: str,
    base_milestone_id: str,
    *,
    triggered_by: str,
) -> MilestoneCompare:
    from app.modules.rc_management.errors import (
        CompareInProgressError,
        CompareVersionMismatchError,
    )

    ms = get_milestone(db, milestone_id)
    base = get_milestone(db, base_milestone_id)
    if base.id == ms.id:
        raise CompareVersionMismatchError()
    if ms.version_id != base.version_id:
        raise CompareVersionMismatchError()
    from app.modules.rc_management.errors import MilestoneBuildUrlMissingError

    if not ms.build_url:
        raise MilestoneBuildUrlMissingError(ms.name)
    if not base.build_url:
        raise MilestoneBuildUrlMissingError(base.name)
    running = db.scalar(
        select(MilestoneCompare).where(
            MilestoneCompare.milestone_id == milestone_id,
            MilestoneCompare.base_milestone_id == base_milestone_id,
            MilestoneCompare.status.in_(["pending", "running"]),
        ).limit(1)
    )
    if running:
        raise CompareInProgressError(ms.name)
    compare = MilestoneCompare(
        milestone_id=milestone_id,
        base_milestone_id=base_milestone_id,
        status="pending",
        triggered_by=triggered_by,
    )
    db.add(compare)
    db.commit()
    db.refresh(compare)
    return compare


def get_compare(db: Session, compare_id: str) -> MilestoneCompare:
    from app.modules.rc_management.errors import CompareNotFoundError

    compare = db.get(MilestoneCompare, compare_id)
    if compare is None:
        raise CompareNotFoundError(compare_id)
    return compare

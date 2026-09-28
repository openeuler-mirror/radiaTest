# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""rc_management T1 测试：版本/里程碑数据模型 CRUD、pxe 轮次标签推导、
94 装机源提示、删除保护（先红后绿）。
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.rc_management.errors import (
    MilestoneDuplicateError,
    MilestoneHasComparesError,
    VersionDuplicateError,
    VersionHasMilestonesError,
)
from app.modules.rc_management.models import MilestoneCompare, ReleaseMilestone, Version
from app.modules.rc_management.schemas import MilestoneCreate, VersionCreate, VersionUpdate
from app.modules.rc_management.service import (
    create_milestone,
    create_version,
    delete_milestone,
    delete_version,
    derive_pxe_round_label,
    list_milestones,
    list_versions,
    milestone_read,
    update_version,
)
from app.modules.resources.physical_install_models import PhysicalInstallImage

BUILD_URL = (
    "http://121.36.84.172/dailybuild/EBS-openEuler-26.09-DevStation/"
    "rc4_openeuler-2026-09-07-02-46-54/26.09-with-kernel-6.6/"
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _add_pxe_image(db: Session, *, round_label: str) -> None:
    db.add(
        PhysicalInstallImage(
            os_version="openEuler-26.09-DevStation",
            arch="x86_64",
            round=round_label,
            kernel_variant="6.6",
        )
    )
    db.commit()


def _version(db: Session) -> Version:
    return create_version(db, VersionCreate(name="openEuler-26.09-DevStation"), created_by="u1")


def test_derive_pxe_round_label() -> None:
    assert derive_pxe_round_label(BUILD_URL) == "rc4_openeuler-2026-09-07-02-46-54"
    assert derive_pxe_round_label(
        "http://x/EBS-p/alpha_openeuler-2026-08-11-04-08-15/k1/"
    ) == "alpha_openeuler-2026-08-11-04-08-15"
    assert derive_pxe_round_label("http://x/EBS-p/") is None


def test_version_auto_generates_rounds(db: Session) -> None:
    v = create_version(
        db,
        VersionCreate(
            name="openEuler-26.09-DevStation",
            rc_round_count=8,
            start_time=datetime(2026, 7, 29, tzinfo=UTC),
        ),
        created_by="u1",
    )
    # N=8 → alpha + rc1..rc8，共 9 个轮次
    assert v.milestone_count == 9
    rounds = list_milestones(db, v.id)
    assert [m.name for m in rounds] == ["alpha", *[f"rc{i}" for i in range(1, 9)]]
    # 构建 URL 按命名规则自动生成（通配构建时间戳与内核变体前缀）
    assert "alpha_openeuler-*" in rounds[0].build_url
    assert "rc8_openeuler-*" in rounds[8].build_url
    assert "-with-kernel-6.6/" in rounds[0].build_url
    # 基准链到前一轮；每轮 7 天从版本开始日期顺排
    assert rounds[1].compare_base_name == "alpha"
    assert rounds[0].start_time is not None and rounds[0].end_time > rounds[0].start_time
    assert rounds[2].start_time - rounds[1].start_time == timedelta(days=7)
    # 手动再建 rc9 自动续链
    ms = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="rc9", build_url=BUILD_URL),
        created_by="u1",
    )
    assert ms.compare_base_name == "rc8"


def test_version_crud(db: Session) -> None:
    v = _version(db)
    assert v.name == "openEuler-26.09-DevStation"
    assert v.status == "testing"
    # alpha 始终存在（rc_round_count=0 时也生成 alpha 骨架）
    assert v.milestone_count == 1

    with pytest.raises(VersionDuplicateError):
        create_version(db, VersionCreate(name="openEuler-26.09-DevStation"), created_by="u1")

    updated = update_version(
        db, v.id, VersionUpdate(status="finished", remark="收口")
    )
    assert updated.status == "finished"

    items, total = list_versions(db, search="26.09", page=1, page_size=50)
    assert [x.name for x in items] == ["openEuler-26.09-DevStation"]
    assert total == 1
    # 有比对记录时拒绝删除（骨架轮次无比对记录，可随版本级联删除）
    from app.modules.rc_management.service import create_compare

    rc1 = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="rc1", build_url=BUILD_URL),
        created_by="u1",
    )
    alpha = db.scalar(
        select(ReleaseMilestone).where(ReleaseMilestone.name == "alpha")
    )
    create_compare(db, rc1.id, alpha.id, triggered_by="u1")
    with pytest.raises(VersionHasMilestonesError):
        delete_version(db, v.id)


def test_milestone_crud_and_dedupe(db: Session) -> None:
    v = _version(db)
    ms = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="round4", build_url=BUILD_URL),
        created_by="u1",
    )
    assert ms.pxe_round_label == "rc4_openeuler-2026-09-07-02-46-54"
    assert ms.build_url == BUILD_URL

    with pytest.raises(MilestoneDuplicateError):
        create_milestone(
            db, MilestoneCreate(version_id=v.id, name="round4", build_url=BUILD_URL),
            created_by="u1",
        )
    # invalid build_url 拒绝
    from app.modules.rc_management.errors import InvalidBuildUrlError

    with pytest.raises(InvalidBuildUrlError):
        create_milestone(
            db, MilestoneCreate(version_id=v.id, name="round5", build_url="http://x/"),
            created_by="u1",
        )


def test_pxe_source_hint_and_compare_base(db: Session) -> None:
    v = _version(db)
    r3 = create_milestone(
        db,
        MilestoneCreate(
            version_id=v.id,
            name="rc3",
            build_url=BUILD_URL.replace("rc4_", "rc3_").replace("09-07-02-46-54", "08-28-04-39-54"),
        ),
        created_by="u1",
    )
    r4 = create_milestone(
        db,
        MilestoneCreate(
            version_id=v.id, name="rc4", build_url=BUILD_URL,
            compare_base_milestone_id=r3.id,
        ),
        created_by="u1",
    )
    _add_pxe_image(db, round_label="rc4_openeuler-2026-09-07-02-46-54")

    read = milestone_read(db, db.get(ReleaseMilestone, r4.id))
    assert read.compare_base_name == "rc3"
    # 94 有 rc4 的装机源 -> 提示为 True
    assert read.has_pxe_source is True
    # round3 没有装机源记录 -> False
    assert milestone_read(db, db.get(ReleaseMilestone, r3.id)).has_pxe_source is False

    mlist = list_milestones(db, v.id)
    assert {m.name for m in mlist} == {"alpha", "rc3", "rc4"}


def test_delete_protections(db: Session) -> None:
    v = _version(db)
    r3 = create_milestone(
        db,
        MilestoneCreate(
            version_id=v.id, name="round3",
            build_url=BUILD_URL.replace("rc4_", "rc3_").replace("09-07-02-46-54", "08-28-04-39-54"),
        ),
        created_by="u1",
    )
    delete_milestone(db, r3.id)  # 无比对记录时可直接删
    assert db.scalar(select(ReleaseMilestone).where(ReleaseMilestone.id == r3.id)) is None

    r4 = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="round4", build_url=BUILD_URL), created_by="u1"
    )
    db.add(
        MilestoneCompare(
            milestone_id=r4.id, base_milestone_id=r4.id, status="succeeded",
            triggered_by="u1",
        )
    )
    db.commit()
    with pytest.raises(MilestoneHasComparesError):
        delete_milestone(db, r4.id)
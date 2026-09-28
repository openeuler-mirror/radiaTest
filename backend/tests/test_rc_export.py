# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""export_service T7 测试：离线生成 7 文件交付 zip（含 SAME），成员与内容校验。"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.rc_management.compare_service import compute_compare
from app.modules.rc_management.export_service import build_export_zip
from app.modules.rc_management.models import MilestoneCompare
from app.modules.rc_management.schemas import MilestoneCreate, VersionCreate
from tests.test_rc_compare import (
    BUILD_B,
    BUILD_T,
    _fake_lists,
    _seed_milestones,
    create_milestone,
    create_version,
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


EXPECTED_FILES = {
    "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
    "everything-vs-everything-binary.xls",
    "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
    "everything-vs-everything-source.xls",
    "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
    "everything-vs-everything-同名异构.xls",
    "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
    "everything-vs-everything-same-binary.xls",
    "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
    "EPOL_main-vs-EPOL_main-binary.xls",
    "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
    "EPOL_main-vs-EPOL_main-source.xls",
    "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
    "EPOL_main-vs-EPOL_main-同名异构.xls",
}


def test_export_zip_has_7_full_xls(db: Session) -> None:
    r3, r4 = _seed_milestones(db)
    compare = MilestoneCompare(
        milestone_id=r4.id, base_milestone_id=r3.id, status="pending", triggered_by="u1"
    )
    db.add(compare)
    db.commit()
    del r3, r4

    data, filename = build_export_zip(
        db, compare, fetch=_fake_lists(), cache_dir=Path("/tmp/nx")
    )
    assert filename == "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4.zip"

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        assert names == EXPECTED_FILES
        # 全量（含 SAME）：binary 应包含 SAME 行，字节非空
        for name in names:
            assert zf.getinfo(name).file_size > 0, name
        bin_data = zf.read(
            "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
            "everything-vs-everything-binary.xls"
        )
        assert b"SAME" in bin_data


def test_export_reuses_same_compare_as_compute(db: Session) -> None:
    """导出成员文件名与 DB 变更行同源（同一缓存清单），抽查同名异构含 DIFFERENT/LACK。"""
    r3, r4 = _seed_milestones(db)
    compare = MilestoneCompare(
        milestone_id=r4.id, base_milestone_id=r3.id, status="succeeded", triggered_by="u1"
    )
    db.add(compare)
    db.commit()
    total, _ = compute_compare(db, compare, fetch=_fake_lists(), cache_dir=Path("/tmp/nx"))
    assert total == 12

    data, _ = build_export_zip(db, compare, fetch=_fake_lists(), cache_dir=Path("/tmp/nx"))
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        iso = zf.read(
            "openEuler-26.09-DevStation-rc3-vs-openEuler-26.09-DevStation-rc4/"
            "everything-vs-everything-同名异构.xls"
        )
        # SAME 为主 + LACK（存量差异行）
        assert b"SAME" in iso and b"LACK" in iso
    del r3, r4


def test_export_sanitizes_hostile_version_name(db: Session) -> None:
    """版本名含路径分隔符/引号时必须消毒，不得逃逸导出目录或注入响应头。

    版本名经 TSE/ADMIN 录入、导出登录即可触发（纵深防御）：../ 序列会
    把留档 zip 写出 rc_export_dir 之外，引号会破坏 Content-Disposition。
    """
    v = create_version(
        db, VersionCreate(name='../../tmp/evil"x'), created_by="u1"
    )
    r3 = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="round3", build_url=BUILD_B),
        created_by="u1",
    )
    r4 = create_milestone(
        db, MilestoneCreate(version_id=v.id, name="round4", build_url=BUILD_T),
        created_by="u1",
    )
    compare = MilestoneCompare(
        milestone_id=r4.id, base_milestone_id=r3.id, status="succeeded",
        triggered_by="u1",
    )
    db.add(compare)
    db.commit()
    del r3, r4

    data, filename = build_export_zip(
        db, compare, fetch=_fake_lists(), cache_dir=Path("/tmp/nx")
    )

    assert "/" not in filename and "\\" not in filename
    assert '"' not in filename and not any(c in filename for c in "\r\n")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            parts = name.split("/")
            # 恰一层目录（zip_label/成员名），无路径穿越组件
            assert len(parts) == 2
            assert ".." not in parts
# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""本地安装源登记（T1）红测：按 94 本地 iteration.repo 探测 OS 树并回填。

先写失败测试，再实现 register_local_install_sources。
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.resources.install_sources import register_local_install_sources
from app.modules.resources.physical_install_models import (
    InstallImageBaseVariant,
    PhysicalInstallImage,
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()


def _add_rc_images(db: Session) -> list[PhysicalInstallImage]:
    images: list[PhysicalInstallImage] = []
    for variant in ("6.6", "6.18"):
        img = PhysicalInstallImage(
            os_version="openEuler-26.09-DevStation",
            arch="x86_64",
            round="rc3_openeuler-2026-08-28-04-39-54",
            kernel_variant=variant,
            iso_url=f"http://121.36.84.172/dailybuild/…/{variant}/…dvd.iso",
        )
        db.add(img)
        images.append(img)
    db.commit()
    return images


BASE = "http://172.168.131.94:9400/repo_list/iteration.repo"
ROUND = "rc3_openeuler-2026-08-28-04-39-54"
OS = "openEuler-26.09-DevStation"


def _listing(variant_dirs: list[str] | None) -> str:
    """回归 94 迭代目录的 HTML 列表（列出 with-kernel 变体目录）。"""
    if not variant_dirs:
        return "<html><body><a href='..'>..</a></body></html>"
    links = "".join(f'<a href="{v}/">{v}/</a>' for v in variant_dirs)
    return f"<html><body>{links}</body></html>"


class FakeResp:
    """最小 urlopen 响应：支持 with + read（listing）或仅上下文（HEAD 探测）。"""

    def __init__(self, body: bytes = b"x") -> None:
        self._body = body

    def __enter__(self) -> FakeResp:
        return self

    @staticmethod
    def __exit__(*_: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def _register(images: list[PhysicalInstallImage], db: Session) -> None:
    """执行登记。真实实现会用 urlopen 探测；测试用 patch。"""
    with patch("app.modules.resources.install_sources.urlopen") as mock:

        def fake_urlopen(url: str, /, timeout: int = 10):
            u = str(url)
            if u.endswith(f"{OS}/{ROUND}/"):
                # round 目录同时有 6.6 和 6.18 两个变体目录
                return FakeResp(
                    _listing(
                        ["26.09-with-kernel-6.6", "26.09-with-kernel-6.18"]
                    ).encode()
                )
            if u.endswith("repodata/repomd.xml"):
                # 只有 k6.6 的 OS 树存在；k6.18 的树缺失
                if "with-kernel-6.6" in u:
                    return FakeResp()
                raise OSError("6.18 OS tree not mirrored")
            if "grubx64.efi" in u:
                return FakeResp()
            raise OSError("not found")

        mock.side_effect = fake_urlopen
        register_local_install_sources(db, mirror_base=BASE)


def test_direct_variant_uses_own_tree(db: Session) -> None:
    db.add(InstallImageBaseVariant(os_version=OS, base_kernel_variant="6.6"))
    images = _add_rc_images(db)
    _register(images, db)

    v66 = db.execute(
        select(PhysicalInstallImage).where(
            PhysicalInstallImage.os_version == OS,
            PhysicalInstallImage.kernel_variant == "6.6",
        )
    ).scalar_one()
    assert v66.repo_url == (
        f"{BASE}/{OS}/{ROUND}/26.09-with-kernel-6.6/OS/x86_64/"
    )
    assert v66.efi_url.endswith("grubx64.efi")
    assert v66.swap_kernel_variant is None


def test_missing_variant_falls_to_base_plus_swap(db: Session) -> None:
    db.add(InstallImageBaseVariant(os_version=OS, base_kernel_variant="6.6"))
    images = _add_rc_images(db)
    _register(images, db)

    v618 = db.execute(
        select(PhysicalInstallImage).where(
            PhysicalInstallImage.os_version == OS,
            PhysicalInstallImage.kernel_variant == "6.18",
        )
    ).scalar_one()
    assert v618.repo_url == (
        f"{BASE}/{OS}/{ROUND}/26.09-with-kernel-6.6/OS/x86_64/"
    )
    assert v618.swap_kernel_variant == "26.09-with-kernel-6.18"


def test_variant_dir_missing_is_not_registered(db: Session) -> None:
    """变体目录在本地 round 中整体缺失 → 不登记（不可装），不能误标直装。"""
    db.add(InstallImageBaseVariant(os_version=OS, base_kernel_variant="6.6"))
    _add_rc_images(db)
    with patch("app.modules.resources.install_sources.urlopen") as mock:

        def fake(url: str, /, timeout: int = 10) -> FakeResp:
            if url.endswith(f"{OS}/{ROUND}/"):
                return FakeResp(_listing([]).encode())
            raise OSError("not found")

        mock.side_effect = fake
        register_local_install_sources(db, mirror_base=BASE)
    for img in db.execute(select(PhysicalInstallImage)).scalars():
        assert img.repo_url is None
        assert img.swap_kernel_variant is None
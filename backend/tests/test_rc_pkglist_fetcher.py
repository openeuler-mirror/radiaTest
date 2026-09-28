# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""pkglist_fetcher T4 测试：双正则解析、URL 拼接、缓存、source 404 容忍。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.modules.rc_management.pkglist_fetcher import (
    PkgListFetchError,
    cached_path,
    listing_url,
    pkglist_for,
    scrape_dir,
)
from app.modules.rc_management.rpm_util import RpmName

BUILD = (
    "http://121.36.84.172/dailybuild/EBS-openEuler-26.09-DevStation/"
    "rc4_openeuler-2026-09-07-02-46-54/26.09-with-kernel-6.6/"
)


def test_listing_url() -> None:
    assert listing_url(BUILD, "everything", arch="x86_64") == (
        BUILD + "everything/x86_64/Packages/"
    )
    assert listing_url(BUILD, "everything", source=True) == BUILD + "source/Packages/"
    assert listing_url(BUILD, "EPOL_main", arch="aarch64") == (
        BUILD + "EPOL/main/aarch64/Packages/"
    )
    assert listing_url(BUILD, "EPOL_main", source=True) == BUILD + "EPOL/main/source/Packages/"


def test_scrape_dir_title_and_href() -> None:
    html = (
        '<a href="?C=N;O=D">Name</a>'
        '<a href="kernel-6.18.0-0.rc2.oe2609.x86_64.rpm">kernel-…</a>'
        '<a title="aide-0.19.4-1.oe2609.x86_64.rpm" href="aide-…">aide</a>'
        '<a href="repodata/">repodata</a>'
    )
    assert scrape_dir(html) == {
        "kernel-6.18.0-0.rc2.oe2609.x86_64.rpm",
        "aide-0.19.4-1.oe2609.x86_64.rpm",
    }


def test_cache_read_and_write(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    html = '<a title="a-1-1.oe2609.x86_64.rpm"></a><a title="b-2-2.oe2609.x86_64.rpm"></a>'
    calls: list[str] = []

    def fake_open(url: str, timeout: int) -> str:
        calls.append(url)
        return html

    with patch("app.modules.rc_management.pkglist_fetcher._open", side_effect=fake_open):
        first = pkglist_for(cache, BUILD, "everything", arch="x86_64")
        assert first == ["a-1-1.oe2609.x86_64.rpm", "b-2-2.oe2609.x86_64.rpm"]
        second = pkglist_for(cache, BUILD, "everything", arch="x86_64")
    assert first == second
    assert len(calls) == 1  # 第二次走缓存
    assert cached_path(
        cache, listing_url(BUILD, "everything", arch="x86_64"), "everything", "x86_64"
    ).exists()


def test_source_404_returns_none(tmp_path: Path) -> None:

    def fake_open(url: str, timeout: int):
        raise PkgListFetchError("HTTP 404: " + url)

    with patch("app.modules.rc_management.pkglist_fetcher._open", side_effect=fake_open):
        result = pkglist_for(tmp_path, BUILD, "everything", source=True)
    assert result is None


def test_other_error_raises(tmp_path: Path) -> None:

    def fake_open(url: str, timeout: int):
        raise PkgListFetchError("HTTP 500: " + url)

    with (
        patch("app.modules.rc_management.pkglist_fetcher._open", side_effect=fake_open),
        pytest.raises(PkgListFetchError),
    ):
        pkglist_for(tmp_path, BUILD, "everything", arch="x86_64")


def test_scraped_names_are_valid_rpms(tmp_path: Path) -> None:
    html = '<a title="x-1-1.oe2609.noarch.rpm"></a><a title="y-2-3.oe2609.aarch64.rpm"></a>'
    with patch(
        "app.modules.rc_management.pkglist_fetcher._open",
        return_value=html,
    ):
        names = pkglist_for(tmp_path, BUILD, "EPOL_main", arch="aarch64")
    assert all(RpmName.parse(n) is not None for n in names or [])
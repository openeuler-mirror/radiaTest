# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""RC 包清单抓取器：目录列表 title=/href= 双正则 + 磁盘缓存 + source 404 容忍。

数据源为公网 dailybuild（rc_dailybuild_base_url / EBS-<product>/…/），目录是 apache
autoindex。与交付工具 pkg_compare 的抓取方式一致（title= 正则），额外兼容 href=。

支持通配 URL：构建根 URL 可含 `*` 段（如 `rc4_openeuler-*`、`*-with-kernel-6.6`），
抓取前列目录解析为最新匹配构建；缓存键使用解析后的精确 URL。

缓存键：sha1(解析后 URL) 前缀 + repo/arch，落 rc_pkglist_cache_dir；有缓存不重复抓。
source 目录缺失（404）时返回 None，由调用方决定跳过该块，不影响整体比对。
"""

from __future__ import annotations

PKGLIST_TIMEOUT_SECONDS = 30

import hashlib
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

_RPM_LINK_RE = re.compile(r'(?:title|href)="([^"]+\.rpm)"')


class PkgListFetchError(RuntimeError):
    """清单抓取失败（网络/非 200/目录结构异常）。"""


def _open(url: str, timeout: int = 30) -> str:
    try:
        with urlopen(url, timeout=PKGLIST_TIMEOUT_SECONDS) as resp:  # noqa: S310 (repo 白名单)
            return resp.read().decode("utf-8", "ignore")
    except HTTPError as exc:
        raise PkgListFetchError(f"HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise PkgListFetchError(f"net error: {url}: {exc.reason}") from exc


def listing_url(
    build_url: str,
    repo_path: str,
    *,
    source: bool = False,
    arch: str | None = None,
) -> str:
    """拼目录列表 URL：{build_url}/{repo}{/arch}/Packages/。

    repo_path ∈ {everything, EPOL_main}；source=True 时取该 repo 的 source 路径，
    否则 binary 需给定 arch（aarch64/x86_64）。
    """
    base = build_url.rstrip("/")
    if repo_path == "everything":
        sub = "source" if source else f"everything/{arch}"
    elif repo_path == "EPOL_main":
        sub = "EPOL/main/source" if source else f"EPOL/main/{arch}"
    else:
        raise ValueError(f"unsupported repo_path: {repo_path}")
    return f"{base}/{sub}/Packages/"


def scrape_dir(html: str) -> set[str]:
    """从目录列表 HTML 提取 .rpm 文件名（title= / href= 双正则）。"""
    return {name for name in _RPM_LINK_RE.findall(html)}


def list_subdirs(html: str) -> set[str]:
    """从目录列表 HTML 提取子目录名（相对链接、以 / 结尾）。"""
    names = set()
    for href in re.findall(r'href="([^"]+)"', html):
        if not href.endswith("/") or href.startswith(("/", "?", "..")) or "://" in href:
            continue
        names.add(href.rstrip("/"))
    return names


def resolve_wildcard_url(url: str, timeout: int = 30) -> str | None:
    """解析含 `*` 通配段的 URL：逐段列目录、按模式匹配子目录、取最新一个。

    无通配段时原样返回；任一层无匹配或目录不可达（404）返回 None。
    """
    m = re.match(r"^(https?://[^/]+/)(.*)$", url)
    if not m:
        return url
    base, rest = m.groups()
    for seg in (x for x in rest.split("/") if x):
        if "*" not in seg:
            base = f"{base}{seg}/"
            continue
        try:
            html = _open(base, timeout=PKGLIST_TIMEOUT_SECONDS)
        except PkgListFetchError as exc:
            if "HTTP 404" in exc.args[0]:
                return None
            raise
        pattern = re.compile("^" + re.escape(seg).replace(r"\*", ".*") + "$")
        matches = sorted(n for n in list_subdirs(html) if pattern.match(n))
        if not matches:
            return None
        base = f"{base}{matches[-1]}/"
    return base


def cache_key(build_url: str) -> str:
    return hashlib.sha1(build_url.encode("utf-8")).hexdigest()[:10]


def cached_path(cache_dir: Path, build_url: str, repo_path: str, arch: str) -> Path:
    safe_repo = repo_path.replace("/", "_")
    return cache_dir / cache_key(build_url) / f"{safe_repo}-{arch}.pkgs"


def pkglist_for(
    cache_dir: Path,
    build_url: str,
    repo_path: str,
    *,
    source: bool = False,
    arch: str | None = None,
) -> list[str] | None:
    """取某 (build_url, repo, arch|source) 的 rpm 文件名清单；有缓存直接读。

    构建根 URL 支持通配段（按命名规则自动生成的模板），抓取前解析为最新匹配
    构建，缓存键使用解析后的精确 URL。目录 404（source 缺失等）返回 None；
    其他抓取异常抛 PkgListFetchError。
    """
    url = listing_url(build_url, repo_path, source=source, arch=arch)
    label = "source" if source else (arch or "")
    if "*" in url:
        url = resolve_wildcard_url(url, timeout=PKGLIST_TIMEOUT_SECONDS)
        if url is None:
            return None
    path = cached_path(cache_dir, url, repo_path, label)
    if path.exists() and path.stat().st_size > 0:
        return [line.strip() for line in path.read_text("utf-8").splitlines() if line.strip()]

    try:
        html = _open(url, timeout=PKGLIST_TIMEOUT_SECONDS)
    except PkgListFetchError as exc:
        if exc.args and "HTTP 404" in exc.args[0]:
            return None
        raise

    names = sorted(scrape_dir(html))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
    return names or None
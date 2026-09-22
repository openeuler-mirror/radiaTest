# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import gzip
import json
import re
from urllib.request import urlopen
from xml.etree import ElementTree

METADATA_NS = "http://linux.duke.edu/metadata/common"


def fetch_update_packages(
    *,
    repo_base_url: str,
    version: str,
) -> list[str]:
    base = repo_base_url.rstrip("/")
    version = version.removesuffix("-64k")
    version_str = version if version.startswith("openEuler-") else f"openEuler-{version}"
    version_url = f"{base}/{version_str}"

    # 每轮 source repo(version 级，非累积 update/source)。对应旧脚本
    # `--repo=${version}_source_${test_update_repo}`，取最新 update 轮的
    # source repo，位于 {version}/{update_dir}/source/。
    update_dir = _latest_update_dir(version_url, version_str)
    if not update_dir:
        raise RuntimeError(f"no update round found in {version_str}-update.json")
    repo_url = f"{version_url}/{update_dir}/source"

    primary_href = _primary_location(repo_url)
    primary_url = f"{repo_url}/{primary_href}"

    return _parse_primary_package_names(primary_url)


def _collect_update_dirs(version_url: str, version: str) -> list[str]:
    """返回全部 update 轮次目录(如 ``update_YYYYMMDD``)，升序。

    来源：``${version_url}/${version}-update.json`` JSON 列表。对应
    ``pipelines/seed.py`` 中的 shell 管道(要求含数字、排除 ``test``/``round``
    候选)，但同时从 ``update`` 和 ``history`` 两个数组收集，使仅在
    ``history`` 中的旧轮次也能被枚举到以便回退。
    """
    json_url = f"{version_url}/{version}-update.json"
    with urlopen(json_url, timeout=30) as response:
        raw_text = response.read().decode("utf-8")
        # 容忍 ] 或 } 前的尾逗号(repo 服务器返回的非法 JSON)
        clean_text = re.sub(r",\s*([}\]])", r"\1", raw_text)
        data = json.loads(clean_text)

    dirs: list[str] = []
    for key in ("update", "history"):
        items = data.get(key) if isinstance(data, dict) else None
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("dir"), str):
                d = item["dir"]
                if re.search(r"\d", d) and "test" not in d and "round" not in d:
                    dirs.append(d)

    dirs.sort()
    return dirs


def list_update_dirs(*, repo_base_url: str, version: str) -> list[str]:
    """返回全部 update 轮次目录(``update_YYYYMMDD``)，最新在前。

    供 64k kernel 回退逐轮尝试各 repo。``version`` 缺 ``openEuler-`` 前缀时
    自动补上。
    """
    base = repo_base_url.rstrip("/")
    version_str = version if version.startswith("openEuler-") else f"openEuler-{version}"
    version_url = f"{base}/{version_str}"
    return list(reversed(_collect_update_dirs(version_url, version_str)))


def _latest_update_dir(version_url: str, version: str) -> str:
    dirs = _collect_update_dirs(version_url, version)
    return dirs[-1] if dirs else ""


def round_label_to_date(round_label: str) -> str:
    """把 update repo 轮次标签（如 ``update_20250803``）解析成 ISO 日期 ``2025-08-03``。

    用于 64k "本周转测检查"日志的日期展示，与 repo 源轮次目录日期一致。
    解析不出 YYYYMMDD 时原样返回。
    """
    m = re.search(r"(\d{4})(\d{2})(\d{2})", round_label)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo}-{d}"
    return round_label


def _primary_location(repo_url: str) -> str:
    repomd_url = f"{repo_url}/repodata/repomd.xml"
    with urlopen(repomd_url, timeout=30) as response:
        tree = ElementTree.parse(response)

    root = tree.getroot()
    ns = {"repo": "http://linux.duke.edu/metadata/repo"}
    for data_elem in root.findall("repo:data", ns):
        if data_elem.get("type") == "primary":
            loc = data_elem.find("repo:location", ns)
            if loc is not None and loc.get("href"):
                return loc.get("href")
    raise RuntimeError("primary data not found in repomd.xml")


def _parse_primary_package_names(primary_url: str) -> list[str]:
    with urlopen(primary_url, timeout=60) as response:
        compressed = response.read()

    if primary_url.endswith(".zst"):
        import io

        import zstandard

        dctx = zstandard.ZstdDecompressor()
        with dctx.stream_reader(io.BytesIO(compressed)) as reader:
            raw = reader.read()
    else:
        raw = gzip.decompress(compressed)
    tree = ElementTree.fromstring(raw)

    names: list[str] = []
    seen: set[str] = set()
    for pkg in tree.findall(f"{{{METADATA_NS}}}package"):
        arch_elem = pkg.find(f"{{{METADATA_NS}}}arch")
        if arch_elem is None or arch_elem.text != "src":
            continue
        name_elem = pkg.find(f"{{{METADATA_NS}}}name")
        if name_elem is not None and name_elem.text:
            name = name_elem.text.strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return names


FILELISTS_NS = "http://linux.duke.edu/metadata/filelists"

_SYSTEMD_DIRS = ("/lib/systemd/system/", "/usr/lib/systemd/system/")
_SERVICE_EXTS = (".service", ".target", ".socket")


def fetch_service_packages(
    *,
    repo_base_url: str,
    version: str,
    arch: str,
) -> list[tuple[str, str, str]]:
    """返回 systemd unit 文件对应的 ``(package_name, service_name, service_type)``。

    解析 binary repo 的 ``filelists.xml``，找出含
    ``/lib/systemd/system/*.service|target|socket`` 文件的包。
    """
    base = repo_base_url.rstrip("/")
    version = version.removesuffix("-64k")
    version_str = version if version.startswith("openEuler-") else f"openEuler-{version}"
    version_url = f"{base}/{version_str}"

    update_dir = _latest_update_dir(version_url, version_str)
    if not update_dir:
        raise RuntimeError(f"no update round found in {version_str}-update.json")
    repo_url = f"{version_url}/{update_dir}/{arch}"

    filelists_href = _filelists_location(repo_url)
    filelists_url = f"{repo_url}/{filelists_href}"

    return _parse_filelists_services(filelists_url)


def _filelists_location(repo_url: str) -> str:
    repomd_url = f"{repo_url}/repodata/repomd.xml"
    with urlopen(repomd_url, timeout=30) as response:
        tree = ElementTree.parse(response)

    root = tree.getroot()
    ns = {"repo": "http://linux.duke.edu/metadata/repo"}
    for data_elem in root.findall("repo:data", ns):
        if data_elem.get("type") == "filelists":
            loc = data_elem.find("repo:location", ns)
            if loc is not None and loc.get("href"):
                return loc.get("href")
    raise RuntimeError("filelists data not found in repomd.xml")


def _parse_filelists_services(filelists_url: str) -> list[tuple[str, str, str]]:
    """返回每个 systemd unit 的 (package_name, service_name, service_type)。"""
    with urlopen(filelists_url, timeout=120) as response:
        compressed = response.read()

    if filelists_url.endswith(".zst"):
        import io

        import zstandard

        dctx = zstandard.ZstdDecompressor()
        with dctx.stream_reader(io.BytesIO(compressed)) as reader:
            raw = reader.read()
    else:
        raw = gzip.decompress(compressed)

    tree = ElementTree.fromstring(raw)
    seen: set[tuple[str, str]] = set()
    results: list[tuple[str, str, str]] = []
    for pkg in tree.findall(f"{{{FILELISTS_NS}}}package"):
        pkg_name = pkg.get("name") or ""
        if not pkg_name:
            continue
        for file_elem in pkg.findall(f"{{{FILELISTS_NS}}}file"):
            path = file_elem.text or ""
            matched = False
            for sd in _SYSTEMD_DIRS:
                idx = path.find(sd)
                if idx < 0:
                    continue
                basename = path[idx + len(sd):]
                for ext in _SERVICE_EXTS:
                    if basename.endswith(ext):
                        svc_name = basename[: -len(ext)]
                        if svc_name and (svc_name, ext[1:]) not in seen:
                            seen.add((svc_name, ext[1:]))
                            results.append((pkg_name, svc_name, ext[1:]))
                        matched = True
                        break
                if matched:
                    break
    return results

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import urlopen

from app.core.config import get_settings

# 从内网镜像仓库解析可用 VM 镜像(iteration 轮次 + official 两类目录)。
# 结果按 (dist, os_version, image_round, arch) 唯一化，供前端选择和申请时校验。


@dataclass(frozen=True)
class VMImage:
    """一个可用镜像：dist/os_version/轮次/arch 与下载 URL。"""

    dist: str
    os_version: str
    image_round: str
    arch: str
    url: str


class ImageDiscoveryError(Exception):
    """镜像仓库不可达或解析失败(网络问题或 HTML 结构异常)。"""


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.hrefs.append(value)


_CACHE: dict[str, tuple[float, list[VMImage]]] = {}
CACHE_SECONDS = 300

# Special marker for official (non-RC) images that have no round layer in the
# repo URL structure. Stored on VMRequest.image_round and TestJob.image_round
# so downstream code (env vars, URL lookup) treats it as a real round value.
OFFICIAL_IMAGE_ROUND = "official"


def _read_links(url: str) -> list[str]:
    try:
        with urlopen(url if url.endswith("/") else f"{url}/", timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")
    except OSError as exc:
        raise ImageDiscoveryError(f"Failed to read image index: {url}") from exc

    parser = _HrefParser()
    parser.feed(html)
    links: list[str] = []
    for href in parser.hrefs:
        normalized = href.rstrip("/")
        if not normalized:
            continue
        if normalized.startswith("?"):
            continue
        if normalized.startswith(("http://", "https://", "mailto:")):
            continue
        if normalized in {"../", "..", "./", "."}:
            continue
        links.append(normalized)
    return links


def _normalize_dist_prefix(dist: str, value: str) -> str:
    """规范化可能带 dist 前缀且大小写不一的目录名。

    例：dist='openEuler', value='openeuler-24.03-LTS-SP1' -> 'openEuler-24.03-LTS-SP1'。
    dist 前缀规范化为与 `dist` 完全一致(与下游用 `dist` 做大小写敏感匹配的代码对齐)；
    版本部分原样保留。
    """
    lower_prefix = dist.lower() + "-"
    if value.lower().startswith(lower_prefix):
        return dist + "-" + value[len(lower_prefix):]
    return value


def _discover_iteration(root: str, dist: str) -> list[VMImage]:
    """解析 iteration/<dist>/<dist>-<version>/<round>/<arch>/<file>.qcow2。

    version 目录名已带 `<dist>-` 前缀(源服务器大小写不一，如
    `openeuler-24.03-LTS-SP1`)。规范化为 `<dist>-<version>`，使下游与
    `dist` 精确匹配。
    """
    dist_url = urljoin(root.rstrip("/") + "/", "iteration/" + dist.strip("/") + "/")
    images: list[VMImage] = []
    try:
        version_dirs = _read_links(dist_url)
    except ImageDiscoveryError:
        return images
    for version_dir in version_dirs:
        os_version = _normalize_dist_prefix(dist, version_dir)
        version_url = urljoin(dist_url, version_dir + "/")
        try:
            rounds = _read_links(version_url)
        except ImageDiscoveryError:
            continue
        for image_round in rounds:
            round_url = urljoin(version_url, image_round + "/")
            for arch in _read_links(round_url):
                arch_url = urljoin(round_url, arch + "/")
                try:
                    arch_links = _read_links(arch_url)
                except ImageDiscoveryError:
                    continue
                for expected_name in (
                    f"{os_version}-{arch}.qcow2",
                    f"{os_version}.{arch}.qcow2",
                ):
                    if expected_name in arch_links:
                        images.append(
                            VMImage(
                                dist=dist,
                                os_version=os_version,
                                image_round=image_round,
                                arch=arch,
                                url=urljoin(arch_url, expected_name),
                            )
                        )
                        break
    return images


def _discover_official(root: str, dist: str) -> list[VMImage]:
    """解析 official/<dist>/<version>/<arch>/<dist>-<version>-<arch>.qcow2。

    official 目录没有 round 层——`image_round` 置为 `OFFICIAL_IMAGE_ROUND`
    ("official")作特殊标记。version 目录名不带 `<dist>-` 前缀，故把
    `os_version` 合成为 `f"{dist}-{version_dir}"`，与 iteration 格式对齐。
    """
    dist_url = urljoin(root.rstrip("/") + "/", "official/" + dist.strip("/") + "/")
    images: list[VMImage] = []
    try:
        version_dirs = _read_links(dist_url)
    except ImageDiscoveryError:
        return images
    for version_dir in version_dirs:
        os_version = f"{dist}-{version_dir}"
        version_url = urljoin(dist_url, version_dir + "/")
        for arch in _read_links(version_url):
            arch_url = urljoin(version_url, arch + "/")
            try:
                arch_links = _read_links(arch_url)
            except ImageDiscoveryError:
                continue
            expected_name = None
            for candidate in (
                f"{os_version}-{arch}.qcow2",
                f"{os_version}.{arch}.qcow2",
            ):
                if candidate in arch_links:
                    expected_name = candidate
                    break
            if expected_name is not None:
                images.append(
                    VMImage(
                        dist=dist,
                        os_version=os_version,
                        image_round=OFFICIAL_IMAGE_ROUND,
                        arch=arch,
                        url=urljoin(arch_url, expected_name),
                    )
                )
    return images


def _discover_uncached(root: str, dist: str) -> list[VMImage]:
    """从 iteration 与 official 两处发现镜像。

    同时返回 iteration(带真实 round)与 official 镜像。即使 iteration
    已有相同 (dist, os_version, arch)，official 镜像仍照常包含——用户
    可任选其一。
    """
    iteration_images = _discover_iteration(root, dist)
    official_images = _discover_official(root, dist)
    return iteration_images + official_images


def discover_images(*, dist: str | None = None, force_refresh: bool = False) -> list[VMImage]:
    """
    发现镜像，带 5 分钟内存缓存(force_refresh 强制刷新)。缓存键含仓库根与
    dist，进程内共享；find_image 始终强制刷新以保证最新。
    """
    settings = get_settings()
    resolved_dist = dist or settings.vm_default_dist
    cache_key = f"{settings.vm_image_repo_root.rstrip('/')}/{resolved_dist}"
    cached = _CACHE.get(cache_key)
    now = time.monotonic()
    if not force_refresh and cached and now - cached[0] <= CACHE_SECONDS:
        return cached[1]

    images = _discover_uncached(settings.vm_image_repo_root, resolved_dist)
    _CACHE[cache_key] = (now, images)
    return images


def find_image(*, dist: str, os_version: str, image_round: str, arch: str) -> VMImage | None:
    """
    按 (dist, os_version, image_round, arch) 精确匹配一个镜像。无则返回 None
    (调用方据此抛 VMImageNotFoundError)。强制刷新缓存，不读旧值。
    """
    for image in discover_images(dist=dist, force_refresh=True):
        if (
            image.os_version == os_version
            and image.image_round == image_round
            and image.arch == arch
        ):
            return image
    return None



@dataclass(frozen=True)
class KernelVariant:
    """一个可选内核变体：变体段 + 内核版本前缀。"""

    variant: str  # 26.09-with-kernel-6.18
    kernel_version_prefix: str  # 6.18


def list_kernel_variants(
    *,
    os_version: str,
    image_round: str,
    arch: str,
) -> list[KernelVariant]:
    """枚举 dailybuild 某轮次下 ``*-with-kernel-*`` 变体目录 + 解析内核版本前缀。

    返回变体段（如 ``26.09-with-kernel-6.18``）与内核版本前缀（``6.18``）。
    dailybuild 不可达或该轮次无内核变体时返回空列表（前端走手填 RPM URL 兜底）。
    """
    settings = get_settings()
    root = settings.vm_dailybuild_repo_root.rstrip("/")
    round_dir = f"{root}/EBS-{os_version}/{image_round}/"
    try:
        links = _read_links(round_dir)
    except ImageDiscoveryError:
        return []
    variants: list[KernelVariant] = []
    for href in links:
        if "with-kernel-" in href:
            prefix = href.split("with-kernel-")[-1]
            variants.append(KernelVariant(variant=href, kernel_version_prefix=prefix))
    return variants



@dataclass(frozen=True)
class RCInstallImage:
    """dailybuild 发现的一个 RC ISO 安装镜像。"""

    os_version: str
    arch: str
    round: str
    kernel_variant: str
    iso_url: str


_RC_CACHE: tuple[float, list[RCInstallImage]] | None = None


def discover_rc_install_images() -> list[RCInstallImage]:
    """从 dailybuild 发现 RC ISO 镜像（开发版 ``*-with-kernel-*`` 变体目录）。

    遍历 ``EBS-<dist>/<round>/<变体>/ISO/<arch>/*.iso``，返回 os_version+arch+
    round+kernel_variant+iso_url。official 行不碰（ADMIN 手动维护 efi_url/repo_url）。
    每个 (dist, round, 变体, arch) 取第一个 ``dvd.iso``。取所有轮次（不裁剪）。
    dailybuild 不可达时返回空列表。5 分钟缓存避免频繁 discover（同 discover_images）。
    """
    global _RC_CACHE
    now = time.monotonic()
    if _RC_CACHE is not None and now - _RC_CACHE[0] <= CACHE_SECONDS:
        return _RC_CACHE[1]
    settings = get_settings()
    root = settings.vm_dailybuild_repo_root.rstrip("/")
    images: list[RCInstallImage] = []
    try:
        dist_dirs = _read_links(root)
    except ImageDiscoveryError:
        return images
    for dist_dir in dist_dirs:
        if not dist_dir.startswith("EBS-"):
            continue
        os_version = dist_dir[len("EBS-"):]
        dist_url = f"{root}/{dist_dir}/"
        try:
            rounds = _read_links(dist_url)
        except ImageDiscoveryError:
            continue
        for round_label in sorted(rounds, reverse=True):
            round_url = f"{dist_url}{round_label}/"
            try:
                variants = _read_links(round_url)
            except ImageDiscoveryError:
                continue
            for variant in variants:
                if "with-kernel-" not in variant:
                    continue
                kver = variant.split("with-kernel-")[-1]
                iso_dir_url = f"{round_url}{variant}/ISO/"
                try:
                    archs = _read_links(iso_dir_url)
                except ImageDiscoveryError:
                    continue
                for arch in archs:
                    arch_url = f"{iso_dir_url}{arch}/"
                    try:
                        files = _read_links(arch_url)
                    except ImageDiscoveryError:
                        continue
                    for fname in files:
                        if fname.endswith(".iso") and "dvd" in fname:
                            images.append(
                                RCInstallImage(
                                    os_version=os_version,
                                    arch=arch,
                                    round=round_label,
                                    kernel_variant=kver,
                                    iso_url=f"{arch_url}{fname}",
                                )
                            )
                            break
    _RC_CACHE = (now, images)
    return images


class PrecheckCustomKernelError(Exception):
    """换内核来源预检失败：repo 不可达/包不存在/RPM URL 不可达。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def precheck_custom_kernel(payload) -> None:
    """提交前预校验换内核来源可达 + 包存在，失败 raise PrecheckCustomKernelError。

    变体路径：推断 dailybuild repo baseurl，验证 repomd 可达 + primary.xml.zst
    解析确认存在 ``kernel-<前缀>.*`` 包。
    URL 路径：验证 RPM URL 可达 + 推断同目录 repo 的 repomd 可达。
    两者都未指定时不预检（不换内核）。
    """
    import re

    import zstandard

    settings = get_settings()
    if payload.kernel_variant:
        dailybuild_root = settings.vm_dailybuild_repo_root.rstrip("/")
        repo_baseurl = (
            f"{dailybuild_root}/EBS-{payload.os_version}/{payload.image_round}/"
            f"{payload.kernel_variant}/everything/{payload.arch}/"
        )
        kver_prefix = payload.kernel_variant.split("with-kernel-")[-1]
        _precheck_repo_and_kernel(repo_baseurl, kver_prefix, re, zstandard)
    elif payload.kernel_rpm_url:
        _precheck_url_reachable(payload.kernel_rpm_url)
        repo_baseurl = payload.kernel_rpm_url.rsplit("/Packages/", 1)[0] + "/"
        _precheck_repo_reachable(repo_baseurl)


def _precheck_repo_reachable(repo_baseurl: str) -> None:
    try:
        with urlopen(f"{repo_baseurl}repodata/repomd.xml", timeout=10) as resp:
            resp.read()
    except OSError as exc:
        raise PrecheckCustomKernelError(
            "repo_unreachable", f"repo {repo_baseurl} 不可达: {exc}"
        ) from exc


def _precheck_url_reachable(url: str) -> None:
    try:
        with urlopen(url, timeout=10) as resp:
            resp.read()
    except OSError as exc:
        raise PrecheckCustomKernelError(
            "rpm_url_unreachable", f"RPM URL {url} 不可达: {exc}"
        ) from exc


def _precheck_repo_and_kernel(repo_baseurl, kver_prefix, re, zstandard) -> None:
    _precheck_repo_reachable(repo_baseurl)
    try:
        with urlopen(f"{repo_baseurl}repodata/repomd.xml", timeout=10) as resp:
            repomd = resp.read().decode("utf-8", errors="replace")
    except OSError as exc:
        raise PrecheckCustomKernelError("repo_unreachable", str(exc)) from exc
    match = re.search(r'href="([^"]+primary\.xml\.zst)"', repomd)
    if not match:
        raise PrecheckCustomKernelError(
            "repo_unreachable", "primary.xml.zst 未在 repomd 中"
        )
    primary_href = match.group(1)
    primary_url = (
        f"{repo_baseurl}{primary_href}"
        if primary_href.startswith("repodata/")
        else primary_href
    )
    try:
        with urlopen(primary_url, timeout=30) as resp:
            primary_zst = resp.read()
    except OSError as exc:
        raise PrecheckCustomKernelError("repo_unreachable", str(exc)) from exc
    # decompressobj 兼容流式压缩（无 content size）与有 content size 两种 frame；
    # ZstdDecompressor().decompress() 要求 frame 含 content size，真实 dailybuild
    # 的 primary.xml.zst 是流式压缩，会抛 "could not determine content size"。
    dobj = zstandard.ZstdDecompressor().decompressobj()
    primary_xml = (
        dobj.decompress(primary_zst) + dobj.flush()
    ).decode("utf-8", errors="replace")
    if not re.search(
        rf'<name>kernel</name>.*?<version[^>]*ver="{re.escape(kver_prefix)}\.',
        primary_xml,
        re.DOTALL,
    ):
        raise PrecheckCustomKernelError(
            "kernel_not_found", f"repo {repo_baseurl} 无 kernel-{kver_prefix}.*"
        )

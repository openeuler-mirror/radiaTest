# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""本地安装源登记：扫描 94 iteration.repo，回填 RC 安装镜像的安装源。

安装源模型（对齐 plans/ac仕/physical-pxe-local-tree-install.md 与 radiaTest）：
- 变体自身 OS 树存在 → `repo_url/efi_url` 指向该树（直接装，无 swap）。
- 变体自身 OS 树缺失 → 回退 base 变体树（见 install_image_base_variants），
  `swap_kernel_variant` 记录装后换内核目标（full 变体目录名）。
- base 树缺失 → 不登记（该行不可装，前端禁触发）。
"""

from __future__ import annotations

import logging
import re
import threading
import time
from urllib.request import urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.resources.physical_install_models import (
    InstallImageBaseVariant,
    PhysicalInstallImage,
)
from app.modules.vms.image_discovery import discover_rc_install_images


def _read_links(url: str) -> list[str]:
    """GET 目录页并提取子目录名（href 以 / 结尾）。探测失败返回空。"""
    try:
        with urlopen(url, timeout=10) as resp:  # noqa: S310
            html = resp.read().decode("utf-8", "ignore")
    except OSError:
        return []
    return [
        m.rstrip("/")
        for m in re.findall(r'href="([^"/]+)/"', html)
        if m not in ("", ".", "..")
    ]


def _head_ok(url: str) -> bool:
    try:
        with urlopen(url, timeout=10):  # noqa: S310
            return True
    except OSError:
        return False


def _variant_dir_for(round_links: list[str], kver: str | None) -> str | None:
    if not kver:
        return None
    for link in round_links:
        if link.endswith(f"-with-kernel-{kver}"):
            return link
    return None


def _os_tree_urls(
    mirror_base: str, os_version: str, round_: str, variant_dir: str, arch: str
) -> tuple[str, str]:
    """返回 (repo_url, efi_url)；OS 树不存在返回 (None, None)。"""
    os_url = (
        f"{mirror_base}/{os_version}/{round_}/{variant_dir}/OS/{arch}"
    )
    if not _head_ok(f"{os_url}/repodata/repomd.xml"):
        return None, None
    efi = "grubx64.efi" if arch == "x86_64" else "grubaa64.efi"
    return f"{os_url}/", f"{os_url}/EFI/BOOT/{efi}"


def ensure_default_install_base_variants(db: Session) -> None:
    """幂等种入默认安装基础变体（DevStation→6.6）。"""
    defaults = {
        "openEuler-26.09-DevStation": "6.6",
    }
    for os_version, kver in defaults.items():
        row = db.get(InstallImageBaseVariant, os_version)
        if row is None:
            db.add(InstallImageBaseVariant(os_version=os_version, base_kernel_variant=kver))
    db.commit()


def get_install_image_base_variant(db: Session, os_version: str) -> str | None:
    row = db.get(InstallImageBaseVariant, os_version)
    return row.base_kernel_variant if row else None


def set_install_image_base_variant(
    db: Session, os_version: str, base_kernel_variant: str
) -> None:
    """设置发行版安装基础内核变体。校验目标发行版存在且变体名格式合法。"""
    if not base_kernel_variant or any(ch.isspace() for ch in base_kernel_variant):
        raise ValueError("base_kernel_variant 不能为空或含空白")
    has_os = db.execute(
        select(PhysicalInstallImage.id)
        .where(PhysicalInstallImage.os_version == os_version)
        .limit(1)
    ).scalar_one_or_none()
    if has_os is None:
        raise ValueError(f"发行版不存在于安装镜像表: {os_version}")
    row = db.get(InstallImageBaseVariant, os_version)
    if row is None:
        db.add(
            InstallImageBaseVariant(
                os_version=os_version, base_kernel_variant=base_kernel_variant
            )
        )
    else:
        row.base_kernel_variant = base_kernel_variant
    db.commit()


def register_local_install_sources(db: Session, *, mirror_base: str) -> None:
    """为所有 RC 安装镜像（iso_url 非空）回填本地安装源。幂等。"""
    rows = list(
        db.execute(
            select(PhysicalInstallImage).where(PhysicalInstallImage.iso_url.is_not(None))
        ).scalars()
    )
    for img in rows:
        if not img.round or not img.arch:
            continue
        round_dir = f"{mirror_base}/{img.os_version}/{img.round}/"
        round_links = _read_links(round_dir)
        variant_dir = _variant_dir_for(round_links, img.kernel_variant)
        repo_url: str | None = None
        efi_url: str | None = None
        swap_kernel_variant: str | None = None
        if variant_dir is None:
            # 变体目录整个缺失（本地连 ISO/repo 目录都没有）→ 不知道 swap 目标变体名，
            # 不登记（不可装），避免被误标为"本地直装"。
            img.repo_url = None
            img.efi_url = None
            img.swap_kernel_variant = None
            continue
        repo_url, efi_url = _os_tree_urls(
            mirror_base, img.os_version, img.round, variant_dir, img.arch
        )
        if repo_url is None:
            # 变体树缺失 → base 变体树 + 装后换内核
            base_kver = get_install_image_base_variant(db, img.os_version)
            base_dir = _variant_dir_for(round_links, base_kver)
            if base_dir and base_dir != variant_dir:
                repo_url, efi_url = _os_tree_urls(
                    mirror_base, img.os_version, img.round, base_dir, img.arch
                )
                if repo_url is not None and variant_dir:
                    swap_kernel_variant = variant_dir
        img.repo_url = repo_url
        img.efi_url = efi_url
        img.swap_kernel_variant = swap_kernel_variant
    db.commit()


def sync_install_image_catalog(db: Session, *, mirror_base: str) -> int:
    """发现 dailybuild RC 镜像 + 本地安装源登记，一次性收敛安装镜像表（幂等）。

    供后台刷新与 seed 复用：先按 dailybuild 同步 RC 行（os/arch/round/kernel_variant
    唯一），再 `register_local_install_sources` 回填本地 OS 树来源。
    """
    ensure_default_install_base_variants(db)
    rc_images = discover_rc_install_images()
    rc_keys: set[tuple[str, str, str, str]] = set()
    for rc in rc_images:
        key = (rc.os_version, rc.arch, rc.round, rc.kernel_variant)
        rc_keys.add(key)
        existing = db.execute(
            select(PhysicalInstallImage).where(
                PhysicalInstallImage.os_version == rc.os_version,
                PhysicalInstallImage.arch == rc.arch,
                PhysicalInstallImage.round == rc.round,
                PhysicalInstallImage.kernel_variant == rc.kernel_variant,
            )
        ).scalars().first()
        if existing:
            existing.iso_url = rc.iso_url
        else:
            db.add(
                PhysicalInstallImage(
                    os_version=rc.os_version,
                    arch=rc.arch,
                    round=rc.round,
                    kernel_variant=rc.kernel_variant,
                    iso_url=rc.iso_url,
                )
            )
    # 删除 dailybuild 已不返回的 RC 行（official 行 iso_url 为 NULL 不受影响）；
    # dailybuild 不可达(rc_images 空)时不删，保留已有数据。
    if rc_images:
        stale = db.execute(
            select(PhysicalInstallImage).where(
                PhysicalInstallImage.iso_url.isnot(None)
            )
        ).scalars().all()
        for img in stale:
            key = (img.os_version, img.arch, img.round or "", img.kernel_variant or "")
            if key not in rc_keys:
                db.delete(img)
    db.commit()
    register_local_install_sources(db, mirror_base=mirror_base)
    return len(rc_images)


CATALOG_REFRESH_INTERVAL = 300
_catalog_refresh_lock = threading.Lock()
_catalog_last_refresh = 0.0


def schedule_catalog_refresh() -> None:
    """每 5 分钟最多触发一次后台镜像目录刷新；请求从不等待该扫描。"""
    global _catalog_last_refresh
    now = time.monotonic()
    if now - _catalog_last_refresh <= CATALOG_REFRESH_INTERVAL:
        return
    with _catalog_refresh_lock:
        if now - _catalog_last_refresh <= CATALOG_REFRESH_INTERVAL:
            return
        _catalog_last_refresh = now
    threading.Thread(target=_refresh_catalog_background, daemon=True).start()


def _refresh_catalog_background() -> None:
    """独立会话跑 sync_install_image_catalog（dailybuild 发现 + 本地登记）。"""
    from app.core.config import get_settings
    from app.db.session import SessionLocal

    try:
        with SessionLocal() as db:
            sync_install_image_catalog(
                db, mirror_base=get_settings().install_mirror_base
            )
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("install image catalog refresh failed")
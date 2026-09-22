# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""导出交付 zip：与 pkg_compare 交付一致，7 个 .xls 全量（含 SAME）。

- 二进制/源码：compare_rpm_dict，全部行含 SAME；
- 同名异构：compare_rpm_dict2（当前轮 x86 vs arm）；
- 重复包：同名同架构多版本清单（三列）。
文件与表头格式对齐 `atomgit.com/zjl_long/pkg_compare`，打包为 zip。
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import xlwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.rc_management.compare_service import REPOS, FetchFn, load_repo_lists
from app.modules.rc_management.models import MilestoneCompare, ReleaseMilestone
from app.modules.rc_management.pkglist_fetcher import pkglist_for
from app.modules.rc_management.rpm_util import (
    compare_rpm_dict,
    compare_rpm_dict2,
    rpmlist2rpmdict,
    rpmlist2rpmdict_by_name,
)

COL_W = (256 * 15, 256 * 70, 256 * 70, 256 * 20)


def _new_wb(sheet_name: str, widths: tuple[int, ...]) -> tuple[xlwt.Workbook, object]:
    wb = xlwt.Workbook()
    ws = wb.add_sheet(sheet_name)
    for i, w in enumerate(widths):
        ws.col(i).width = w
    return wb, ws


def _write_header(ws: object, values: list[str]) -> None:
    for col, value in enumerate(values):
        ws.write(0, col, value)


def _build_binary_ws(
    product_base: str, product_target: str, rows: list[dict[str, str]], title: str
) -> bytes:
    wb, ws = _new_wb(title, COL_W)
    _write_header(ws, [title, product_base, product_target, "比对结果"])
    for i, row in enumerate(rows, 1):
        ws.write(i, 0, row["arch"])
        ws.write(i, 1, row["rpm_list_1"])
        ws.write(i, 2, row["rpm_list_2"])
        ws.write(i, 3, row["compare_result"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _build_isomer_ws(rows: list[dict[str, str]]) -> bytes:
    wb, ws = _new_wb("二进制对比", COL_W)
    _write_header(ws, ["包名", "x86_64", "aarch64", "比对结果"])
    for i, row in enumerate(rows, 1):
        ws.write(i, 0, row["rpm_name"])
        ws.write(i, 1, row["rpm_x86"])
        ws.write(i, 2, row["rpm_arm"])
        ws.write(i, 3, row["compare_result"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _build_repeat_ws(
    product_base: str,
    product_target: str,
    repeat_base: dict[str, list[object]],
    repeat_target: dict[str, list[object]],
) -> bytes:
    wb, ws = _new_wb("二进制对比", (256 * 15, 256 * 70, 256 * 70))
    _write_header(ws, ["二进制对比", product_base, product_target])
    for i, key in enumerate(sorted(set(repeat_base) | set(repeat_target)), 1):
        b_files = "\n".join(sorted(x.file for x in repeat_base.get(key, [])))
        t_files = "\n".join(sorted(x.file for x in repeat_target.get(key, [])))
        ws.write(i, 0, key)
        ws.write(i, 1, b_files)
        ws.write(i, 2, t_files)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _short_name(ms: ReleaseMilestone) -> str:
    """交付命名习惯：round3 → rc3；alpha/release 原样。"""
    if ms.name.startswith("round") and ms.name[5:].isdigit():
        return "rc" + ms.name[5:]
    return ms.name


def _labels(db: Session, compare: MilestoneCompare) -> tuple[str, str, str]:
    target = db.get(ReleaseMilestone, compare.milestone_id)
    base = db.get(ReleaseMilestone, compare.base_milestone_id)
    if target is None or base is None:
        raise ValueError("比对关联的里程碑不存在")
    vname = target.version.name
    b, t = _short_name(base), _short_name(target)
    return (
        f"{vname}-{b}",
        f"{vname}-{t}",
        _sanitize_label(f"{vname}-{b}-vs-{vname}-{t}"),
    )


def _sanitize_label(label: str) -> str:
    """中和 zip 路径三处用途（zip 条目、留档落盘、Content-Disposition）的
    不安全字符：路径分隔符会让 ../ 把留档写出 rc_export_dir 之外，引号/
    控制符破坏响应头（版本名经 TSE/ADMIN 录入、导出登录即可触发，纵深
    防御）。保留 Unicode 词字符与 . -，中文版本名不受影响。
    """
    return re.sub(r"[^\w.-]", "_", label)


def build_export_zip(
    db: Session,
    compare: MilestoneCompare,
    *,
    fetch: FetchFn | None = None,
    cache_dir: Path | None = None,
) -> tuple[bytes, str]:
    """生成完整交付 zip，返回 (字节, 文件名)。清单来自缓存（有缓存不重复抓）。"""

    cache_dir = cache_dir or Path(get_settings().rc_pkglist_cache_dir)
    fetch = fetch or pkglist_for
    product_base, product_target, zip_label = _labels(db, compare)
    target = db.get(ReleaseMilestone, compare.milestone_id)
    base = db.get(ReleaseMilestone, compare.base_milestone_id)
    if target is None or base is None:
        raise ValueError("比对关联的里程碑不存在")

    # (文件名, bytes)
    files: list[tuple[str, bytes]] = []
    for repo in REPOS:
        t_x, t_a, t_src = load_repo_lists(target.build_url, repo, fetch, cache_dir)
        b_x, b_a, b_src = load_repo_lists(base.build_url, repo, fetch, cache_dir)
        if None in (t_x, t_a, b_x, b_a):
            raise ValueError(f"{repo} 二进制清单缺失，无法导出")
        label = repo

        # binary（含 SAME）
        d_base, rep_base = rpmlist2rpmdict(b_x + b_a)
        d_target, rep_target = rpmlist2rpmdict(t_x + t_a)
        bin_rows = compare_rpm_dict(d_base, d_target)
        files.append(
            (
                f"{label}-vs-{label}-binary.xls",
                _build_binary_ws(product_base, product_target, bin_rows, "二进制对比"),
            )
        )
        # repeat：与交付一致，仅 everything 出 same-binary 文件
        if repo == "everything":
            files.append(
                (
                    f"{label}-vs-{label}-same-binary.xls",
                    _build_repeat_ws(product_base, product_target, rep_base, rep_target),
                )
            )
        # source：缺失时出表头空表，保持交付恒为 7 文件
        if t_src and b_src:
            ds_base, _ = rpmlist2rpmdict(b_src)
            ds_target, _ = rpmlist2rpmdict(t_src)
            src_rows = compare_rpm_dict(ds_base, ds_target)
        else:
            src_rows = []
        files.append(
            (
                f"{label}-vs-{label}-source.xls",
                _build_binary_ws(
                    product_base, product_target, src_rows, "源码对比",
                ),
            )
        )
        # 同名异构（当前轮）
        files.append(
            (
                f"{label}-vs-{label}-同名异构.xls",
                _build_isomer_ws(
                    compare_rpm_dict2(
                        rpmlist2rpmdict_by_name(t_x), rpmlist2rpmdict_by_name(t_a)
                    )
                ),
            )
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in files:
            zf.writestr(f"{zip_label}/{filename}", data)
    payload = buf.getvalue()

    # 留档：交付 zip 同步落 rc_export_dir，便于追溯
    export_dir = Path(get_settings().rc_export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / f"{zip_label}.zip").write_bytes(payload)
    return payload, f"{zip_label}.zip"

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""比对编排：抓清单→比较→落库→汇总。

对外口径与交付工具 pkg_compare 一致（see ADR 0041）：
- binary/source 用 compare_rpm_dict，只存非 SAME 变更行；
- 重复包（repeat）在 binary 字典上收集多版本并存；
- isomer 在当前轮内 x86_64 vs aarch64 同名包（SAME 不入库，DIFFERENT/LACK 入库）。
fetch 可注入（默认 pkglist_for），便于测试离线数据。
"""

from __future__ import annotations

from dataclasses import dataclass

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeAlias

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.rc_management.models import (
    CompareStatus,
    MilestoneCompare,
    PackageCompareResult,
    ReleaseMilestone,
)
from app.modules.rc_management.pkglist_fetcher import pkglist_for
from app.modules.rc_management.rpm_util import (
    RpmName,
    compare_rpm_dict,
    compare_rpm_dict2,
    rpmlist2rpmdict,
    rpmlist2rpmdict_by_name,
)

REPOS = ["everything", "EPOL_main"]

FetchFn: TypeAlias = Callable[..., list[str] | None]


def utc_now() -> datetime:
    return datetime.now(UTC)


class CompareExecutionError(RuntimeError):
    """比对执行失败（抓取异常、必要清单缺失等）。"""


def load_repo_lists(
    build_url: str,
    repo_path: str,
    fetch: FetchFn,
    cache_dir: Path,
) -> tuple[list[str] | None, list[str] | None, list[str] | None]:
    x86 = fetch(cache_dir, build_url, repo_path, source=False, arch="x86_64")
    arm = fetch(cache_dir, build_url, repo_path, source=False, arch="aarch64")
    src = fetch(cache_dir, build_url, repo_path, source=True)
    return x86, arm, src


@dataclass(frozen=True)
class CompareRowDraft:
    """一行比对结果草稿。"""

    kind: str
    repo: str
    pkg: str
    arch: str | None
    status: str
    rpm_base: str | None
    rpm_target: str | None


@dataclass(frozen=True)
class CompareResultQuery:
    """比对结果查询条件与分页。"""

    kind: str | None = None
    repo_path: str | None = None
    arch: str | None = None
    statuses: list[str] | None = None
    page: int = 1
    page_size: int = 50


def _bare_name(rpm_file: str) -> str:
    info = RpmName.parse(rpm_file)
    return info.name if info else rpm_file.split("-")[0]


def compute_compare(
    db: Session,
    compare: MilestoneCompare,
    *,
    fetch: FetchFn | None = None,
    cache_dir: Path | None = None,
) -> tuple[int, dict[str, object]]:
    """执行一次比对并落库，返回 (变更行数, 汇总)。调用方负责状态流转与提交。"""
    cache_dir = cache_dir or Path(get_settings().rc_pkglist_cache_dir)
    fetch = fetch or pkglist_for
    target = db.get(ReleaseMilestone, compare.milestone_id)
    base = db.get(ReleaseMilestone, compare.base_milestone_id)
    if target is None or base is None:
        raise CompareExecutionError("target/base 里程碑不存在")

    rows: list[PackageCompareResult] = []

    def add_row(row: CompareRowDraft) -> None:
        rows.append(
            PackageCompareResult(
                compare_id=compare.id,
                kind=row.kind,
                repo_path=row.repo,
                pkg_name=row.pkg,
                arch=row.arch,
                status=row.status,
                rpm_base=row.rpm_base,
                rpm_target=row.rpm_target,
            )
        )

    for repo in REPOS:
        t_x, t_a, t_src = load_repo_lists(target.build_url, repo, fetch, cache_dir)
        b_x, b_a, b_src = load_repo_lists(base.build_url, repo, fetch, cache_dir)
        target_lists_missing = t_x is None or t_a is None
        base_lists_missing = b_x is None or b_a is None
        if target_lists_missing or base_lists_missing:
            raise CompareExecutionError(f"{repo} 二进制清单缺失（各架构 Packages/ 必须存在）")

        # binary：合并双架构，name.arch 键，base vs target
        d_base, rep_base = rpmlist2rpmdict(b_x + b_a)
        d_target, rep_target = rpmlist2rpmdict(t_x + t_a)
        for r in compare_rpm_dict(d_base, d_target):
            if r["compare_result"] == "SAME":
                continue
            bare = _bare_name(r["rpm_list_1"] or r["rpm_list_2"])
            add_row(
                CompareRowDraft(
                    kind="binary",
                    repo=repo,
                    pkg=bare,
                    arch=r["arch"],
                    status=r["compare_result"],
                    rpm_base=r["rpm_list_1"] or None,
                    rpm_target=r["rpm_list_2"] or None,
                )
            )

        # repeat：同名同架构多版本并存（并集）
        for key in sorted(set(rep_base) | set(rep_target)):
            b_files = sorted(x.file for x in rep_base.get(key, []))
            t_files = sorted(x.file for x in rep_target.get(key, []))
            arch = key.rsplit(".", 1)[1]
            add_row(
                CompareRowDraft(
                    kind="repeat",
                    repo=repo,
                    pkg=key,
                    arch=arch,
                    status="REPEAT",
                    rpm_base="\n".join(b_files) or None,
                    rpm_target="\n".join(t_files) or None,
                )
            )

        # source：source 缺失 404 时整块跳过（不报错）
        if t_src and b_src:
            ds_base, _ = rpmlist2rpmdict(b_src)
            ds_target, _ = rpmlist2rpmdict(t_src)
            for r in compare_rpm_dict(ds_base, ds_target):
                if r["compare_result"] == "SAME":
                    continue
                bare = _bare_name(r["rpm_list_1"] or r["rpm_list_2"])
                add_row(
                    CompareRowDraft(
                        kind="source",
                        repo=repo,
                        pkg=bare,
                        arch="src",
                        status=r["compare_result"],
                        rpm_base=r["rpm_list_1"] or None,
                        rpm_target=r["rpm_list_2"] or None,
                    )
                )

        # isomer：当前轮 x86 vs arm 同名包
        d_x = rpmlist2rpmdict_by_name(t_x)
        d_a = rpmlist2rpmdict_by_name(t_a)
        for r in compare_rpm_dict2(d_x, d_a):
            if r["compare_result"] == "SAME":
                continue
            add_row(
                CompareRowDraft(
                    kind="isomer",
                    repo=repo,
                    pkg=r["rpm_name"],
                    arch=None,
                    status=r["compare_result"],
                    rpm_base=r["rpm_x86"] or None,
                    rpm_target=r["rpm_arm"] or None,
                )
            )

    db.add_all(rows)
    summary: dict[str, object] = {}
    for r in rows:
        by_kind = summary.setdefault(r.kind, {})
        by_kind[r.status] = by_kind.get(r.status, 0) + 1
    compare.total_changed = len(rows)
    compare.summary = summary
    compare.status = CompareStatus.SUCCEEDED.value
    compare.completed_at = utc_now()
    db.commit()
    return len(rows), summary


def query_results(
    db: Session,
    compare_id: str,
    *,
    query: CompareResultQuery,
) -> tuple[list[PackageCompareResult], int]:
    kind = query.kind
    repo_path = query.repo_path
    arch = query.arch
    statuses = query.statuses
    page = query.page
    page_size = query.page_size
    """比对结果查询（只读）：按 kind/repo/arch/status 组合筛选，按 id 倒序分页。"""
    from sqlalchemy import func, select

    filters = [PackageCompareResult.compare_id == compare_id]
    if kind:
        filters.append(PackageCompareResult.kind == kind)
    if repo_path:
        filters.append(PackageCompareResult.repo_path == repo_path)
    if arch:
        filters.append(PackageCompareResult.arch == arch)
    if statuses:
        filters.append(PackageCompareResult.status.in_(statuses))

    total = db.scalar(select(func.count(PackageCompareResult.id)).where(*filters)) or 0
    items = (
        db.execute(
            select(PackageCompareResult)
            .where(*filters)
            .order_by(PackageCompareResult.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(items), total

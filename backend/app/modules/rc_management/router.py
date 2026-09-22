# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated

from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.api_runtime import APIError
from app.core.pagination import PAGE_SIZE, PageParams, PageResponse, get_page_params
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.rc_management.errors import (
    CompareInProgressError,
    CompareNotFoundError,
    CompareVersionMismatchError,
    InvalidBuildUrlError,
    MilestoneBuildUrlMissingError,
    MilestoneDuplicateError,
    MilestoneHasComparesError,
    MilestoneNotFoundError,
    RcManagementError,
    VersionDuplicateError,
    VersionHasMilestonesError,
    VersionNotFoundError,
)
from app.modules.rc_management.schemas import (
    CompareRead,
    CompareTrigger,
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    PackageCompareResultRead,
    VersionCreate,
    VersionRead,
    VersionUpdate,
)
from app.modules.rc_management.service import (
    create_compare,
    create_milestone,
    create_version,
    delete_milestone,
    delete_version,
    get_compare,
    get_version,
    list_milestones,
    list_versions,
    update_milestone,
    update_version,
    version_read,
)
from app.modules.users.models import User, UserRole

# 版本管理域路由：薄层，只做请求解析、权限与异常映射；业务规则在 service。
# /versions、/milestones、/compares 三个前缀独立挂载至 /api/v1。

versions_router = APIRouter(prefix="/versions", tags=["版本管理 / 版本"])
milestones_router = APIRouter(prefix="/milestones", tags=["版本管理 / 里程碑"])
compares_router = APIRouter(prefix="/compares", tags=["版本管理 / 比对"])


def _require_write(user: User) -> None:
    """版本/里程碑写操作仅 TSE/ADMIN（后端最终边界）。"""
    if user.role not in (UserRole.ADMIN.value, UserRole.TSE.value):
        raise APIError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden",
            message="仅 TSE/ADMIN 可执行版本/里程碑写操作",
        )


def _map_error(exc: Exception) -> APIError:
    if isinstance(exc, VersionNotFoundError):
        return APIError(status_code=404, code="not_found", message=f"版本不存在：{exc}")
    if isinstance(exc, MilestoneNotFoundError):
        return APIError(status_code=404, code="not_found", message=f"里程碑不存在：{exc}")
    if isinstance(exc, (VersionDuplicateError, MilestoneDuplicateError)):
        return APIError(status_code=409, code="duplicate", message=str(exc))
    if isinstance(exc, (VersionHasMilestonesError, MilestoneHasComparesError)):
        return APIError(status_code=409, code="conflict", message=str(exc))
    if isinstance(exc, (InvalidBuildUrlError, MilestoneBuildUrlMissingError)):
        return APIError(status_code=400, code="bad_request", message=str(exc))
    if isinstance(exc, (CompareVersionMismatchError, CompareInProgressError)):
        return APIError(status_code=409, code="conflict", message=str(exc))
    if isinstance(exc, CompareNotFoundError):
        return APIError(status_code=404, code="not_found", message=str(exc))
    return APIError(status_code=500, code="internal_error", message=str(exc))


def _run(operation: object) -> object:
    try:
        return operation()
    except RcManagementError as exc:
        raise _map_error(exc) from exc


CurrentUser = Annotated[User, Depends(get_current_user)]
Db = Annotated[Session, Depends(get_db)]
PageParamsDep = Annotated[PageParams, Depends(get_page_params)]


@versions_router.get("", response_model=PageResponse[VersionRead])
def read_versions(
    current_user: CurrentUser,
    db: Db,
    pagination: PageParamsDep,
    search: str | None = None,
):
    _ = current_user
    items, total = list_versions(db, search=search, page=pagination.page, page_size=PAGE_SIZE)
    return PageResponse(items=items, total=total, page=pagination.page)


@versions_router.post("", response_model=VersionRead, status_code=status.HTTP_201_CREATED)
def post_version(
    current_user: CurrentUser,
    db: Db,
    payload: VersionCreate,
):
    _require_write(current_user)
    return _run(lambda: create_version(db, payload, created_by=current_user.id))


@versions_router.get("/{version_id}", response_model=VersionRead)
def read_version(
    current_user: CurrentUser,
    db: Db,
    version_id: str,
):
    _ = current_user
    return _run(lambda: version_read(db, get_version(db, version_id)))


@versions_router.put("/{version_id}", response_model=VersionRead)
def put_version(
    current_user: CurrentUser,
    db: Db,
    version_id: str,
    payload: VersionUpdate,
):
    _require_write(current_user)
    return _run(lambda: update_version(db, version_id, payload))


@versions_router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def del_version(
    current_user: CurrentUser,
    db: Db,
    version_id: str,
):
    _require_write(current_user)
    _run(lambda: delete_version(db, version_id))
    return None


@versions_router.get("/{version_id}/milestones", response_model=list[MilestoneRead])
def read_version_milestones(
    current_user: CurrentUser,
    db: Db,
    version_id: str,
):
    _ = current_user
    return _run(lambda: list_milestones(db, version_id))


@milestones_router.post("", response_model=MilestoneRead, status_code=status.HTTP_201_CREATED)
def post_milestone(
    current_user: CurrentUser,
    db: Db,
    payload: MilestoneCreate,
):
    _require_write(current_user)
    return _run(lambda: create_milestone(db, payload, created_by=current_user.id))


@milestones_router.put("/{milestone_id}", response_model=MilestoneRead)
def put_milestone(
    current_user: CurrentUser,
    db: Db,
    milestone_id: str,
    payload: MilestoneUpdate,
):
    _require_write(current_user)
    return _run(lambda: update_milestone(db, milestone_id, payload))


@milestones_router.delete("/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def del_milestone(
    current_user: CurrentUser,
    db: Db,
    milestone_id: str,
):
    _require_write(current_user)
    _run(lambda: delete_milestone(db, milestone_id))
    return None
# ---------- 比对 ----------


@milestones_router.post("/{milestone_id}/compares", response_model=CompareRead, status_code=202)
def trigger_compare(
    current_user: CurrentUser,
    db: Db,
    milestone_id: str,
    payload: CompareTrigger,
):
    _ = current_user  # 登录即可触发
    try:
        compare = create_compare(
            db, milestone_id, payload.base_milestone_id, triggered_by=current_user.id
        )
    except RcManagementError as exc:
        raise _map_error(exc) from exc
    from app.modules.rc_management.tasks import run_rc_compare_task

    run_rc_compare_task.delay(compare.id)
    return CompareRead.model_validate(compare)


@compares_router.get("/{compare_id}", response_model=CompareRead)
def read_compare(
    current_user: CurrentUser,
    db: Db,
    compare_id: str,
):
    _ = current_user
    try:
        compare = get_compare(db, compare_id)
    except RcManagementError as exc:
        raise _map_error(exc) from exc
    return CompareRead.model_validate(compare)


class CompareResultFilters(BaseModel):
    """比对结果筛选条件（查询参数）。"""

    kind: str | None = None
    repo_path: str | None = None
    arch: str | None = None
    status: list[str] | None = None


@compares_router.get("/{compare_id}/results", response_model=PageResponse[PackageCompareResultRead])
def read_compare_results(
    current_user: CurrentUser,
    db: Db,
    compare_id: str,
    pagination: PageParamsDep,
    filters: Annotated[CompareResultFilters, Depends()],
):
    _ = current_user
    try:
        get_compare(db, compare_id)
    except RcManagementError as exc:
        raise _map_error(exc) from exc
    from app.modules.rc_management.compare_service import CompareResultQuery, query_results

    items, total = query_results(
        db,
        compare_id,
        query=CompareResultQuery(
            kind=filters.kind,
            repo_path=filters.repo_path,
            arch=filters.arch,
            statuses=filters.status,
            page=pagination.page,
            page_size=PAGE_SIZE,
        ),
    )
    return PageResponse(
        items=[PackageCompareResultRead.model_validate(r) for r in items],
        total=total,
        page=pagination.page,
    )


@compares_router.get("/{compare_id}/export")
def export_compare(
    current_user: CurrentUser,
    db: Db,
    compare_id: str,
):
    _ = current_user
    try:
        compare = get_compare(db, compare_id)
        if compare.status != "succeeded":
            raise APIError(
                status_code=409, code="conflict", message="比对未完成，暂不可导出"
            )
    except RcManagementError as exc:
        raise _map_error(exc) from exc
    from app.modules.rc_management.export_service import build_export_zip

    data, filename = build_export_zip(db, compare)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

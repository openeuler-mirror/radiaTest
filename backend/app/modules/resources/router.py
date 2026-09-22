# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, PageResponse, get_page_params
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.audit.service import record_audit_log
from app.modules.idempotency.http import begin_http_idempotent_request
from app.modules.idempotency.service import (
    abandon_idempotency_on_error,
    record_idempotency_response,
)
from app.modules.leases.service import release_expired_leases
from app.modules.resources.export_service import export_resources_csv
from app.modules.resources.import_service import ResourceImportFormatError, import_resources
from app.modules.resources.models import ResourceType
from app.modules.resources.schemas import (
    ResourceCreate,
    ResourceImportRequest,
    ResourceImportResult,
    ResourceListParams,
    ResourceRead,
    ResourceUpdate,
)
from app.modules.resources.service import (
    ResourceAlreadyExistsError,
    ResourceBusyError,
    ResourceInvariantError,
    ResourcePolicyError,
    create_managed_resource,
    ensure_resource_not_testing,
    get_resource,
    list_resources,
    paginate_resources,
    serialize_resource,
    serialize_resources,
    update_managed_resource,
)
from app.modules.tasks.recovery import (
    RecoveryTaskType,
    RecoveryTrigger,
    recover_interrupted_tasks,
)
from app.modules.users.models import User, UserRole

# 资源路由：仅做请求解析、鉴权入口、审计落库与响应转换，业务规则在 service。
# 读端点统一先触发 release_expired_leases 懒释放(在 list/get/patch 前顺手收敛
# 过期租约状态)。幂等端点(imports)用 Idempotency-Key + record/replay 闭环。
router = APIRouter(prefix="/resources", tags=["resources"])


def require_admin(user: User) -> None:
    """仅 ADMIN 可继续的入口鉴权，否则 403。"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )



@router.get("", response_model=PageResponse[ResourceRead])
def read_resources(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    params: Annotated[ResourceListParams, Depends()],
) -> PageResponse[ResourceRead]:
    """分页查询资源列表，支持多列过滤与 AND/OR 匹配。

    读端点会先懒释放过期租约再分页查询。

    Args:
        pagination: 分页参数（page/size）.
        params: 聚合查询过滤参数，match 控制多列 AND/OR 匹配.

    Returns:
        PageResponse[ResourceRead]: 分页资源列表.
    """
    if release_expired_leases(db):
        db.commit()
    resources, total = paginate_resources(db, params=params, pagination=pagination)
    return PageResponse(
        items=serialize_resources(db, resources),
        total=total,
        page=pagination.page,
    )


@router.post("", response_model=ResourceRead, status_code=status.HTTP_201_CREATED)
def create_resource_endpoint(
    payload: ResourceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    """创建受管资源，按业务策略校验落库后记录审计日志。

    Args:
        payload: 资源创建字段.

    Returns:
        ResourceRead: 新建资源（HTTP 201）.

    Raises:
        HTTPException: 403 违反资源策略 / 409 资源编码已存在.
    """
    try:
        resource = create_managed_resource(db, actor=current_user, payload=payload)
    except ResourcePolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ResourceAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resource code already exists",
        ) from exc

    record_audit_log(
        db,
        actor_user_id=current_user.id,
        action="resource.create",
        target_type="resource",
        target_id=resource.id,
        detail={
            "resource_code": resource.resource_code,
            "resource_type": resource.resource_type,
        },
    )
    db.commit()
    db.refresh(resource)
    return serialize_resource(db, resource)


@router.post("/imports", response_model=ResourceImportResult)
def import_resources_endpoint(
    payload: ResourceImportRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ResourceImportResult | JSONResponse:
    """批量导入资源，支持 dry_run 预校验与 Idempotency-Key 重放。

    仅 ADMIN。非 dry_run 走幂等记录/重放闭环。

    Args:
        payload: 导入请求，含文件名、格式与行数据.
        idempotency_key: 幂等键，非 dry_run 时用于重放.

    Returns:
        ResourceImportResult | JSONResponse: dry_run 直返结果；
        非 dry_run 经幂等记录后返回 200.

    Raises:
        HTTPException: 403 非 ADMIN / 400 导入格式错误.
    """
    require_admin(current_user)

    if payload.dry_run:
        try:
            return import_resources(db, payload)
        except ResourceImportFormatError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    decision = begin_http_idempotent_request(
        db,
        actor=current_user,
        request=request,
        key=idempotency_key,
        payload=payload.model_dump(mode="json"),
    )
    if decision.replay is not None:
        return decision.replay
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    with abandon_idempotency_on_error(db, decision.record):
        try:
            result = import_resources(db, payload)
        except ResourceImportFormatError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        response = result.model_dump(mode="json")
        created_codes = [
            row.resource_code
            for row in result.rows
            if row.status == "created" and row.resource_code
        ]
        record_audit_log(
            db,
            actor_user_id=current_user.id,
            action="resource.import",
            target_type="resource_import",
            target_id=None,
            detail={
                "filename": payload.filename,
                "total_rows": result.total_rows,
                "success_count": result.success_count,
                "error_count": result.error_count,
                "resource_codes": created_codes,
            },
        )
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_200_OK,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)


@router.get("/exports")
def export_resources_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    params: Annotated[ResourceListParams, Depends()],
) -> Response:
    """按当前过滤条件导出资源 CSV，仅 ADMIN。

    会先懒释放过期租约，再导出并记录审计日志。

    Args:
        params: 聚合查询过滤参数.

    Returns:
        Response: text/csv 附件，文件名 radiaTest-resources.csv.

    Raises:
        HTTPException: 403 非 ADMIN.
    """
    require_admin(current_user)
    if release_expired_leases(db):
        db.commit()
    resources = list_resources(db, params=params, offset=0, limit=None)
    content = export_resources_csv(db, resources)
    record_audit_log(
        db,
        actor_user_id=current_user.id,
        action="resource.export",
        target_type="resource_export",
        target_id=None,
        detail={
            "row_count": len(resources),
            "match": params.match,
            "filters": params.model_dump(exclude_none=True),
        },
    )
    db.commit()
    headers = {"Content-Disposition": 'attachment; filename="radiaTest-resources.csv"'}
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=headers)


# --- Physical machine PXE install ---


class PhysicalInstallImageCreate(BaseModel):
    os_version: str
    arch: str
    efi_url: str | None = None
    repo_url: str | None = None
    round: str | None = None
    iso_url: str | None = None
    kernel_variant: str | None = None


@router.get("/install-images")
def list_install_images(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """列出全部物理机 PXE 安装镜像，仅 ADMIN。列表即时返回，同步在后台刷新。

    Returns:
        list[dict]: 镜像列表（id/os_version/arch/efi_url/repo_url/swap_kernel_variant）.

    Raises:
        HTTPException: 403 非 ADMIN.
    """
    require_admin(current_user)
    from sqlalchemy import select as sa_select

    from app.modules.resources.install_sources import schedule_catalog_refresh
    from app.modules.resources.physical_install_models import PhysicalInstallImage

    schedule_catalog_refresh()

    images = db.execute(sa_select(PhysicalInstallImage)).scalars().all()
    return [
        {
            "id": img.id,
            "os_version": img.os_version,
            "arch": img.arch,
            "efi_url": img.efi_url,
            "repo_url": img.repo_url,
            "round": img.round,
            "iso_url": img.iso_url,
            "kernel_variant": img.kernel_variant,
            "swap_kernel_variant": img.swap_kernel_variant,
        }
        for img in images
    ]


@router.post("/install-images")
def create_install_image(
    payload: PhysicalInstallImageCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    """新建物理机 PXE 安装镜像，仅 ADMIN。

    Args:
        payload: 镜像字段（os_version/arch/efi_url/repo_url）.

    Returns:
        dict: 新建镜像.

    Raises:
        HTTPException: 403 非 ADMIN.
    """
    require_admin(current_user)
    from app.modules.resources.physical_install_models import PhysicalInstallImage

    img = PhysicalInstallImage(
        os_version=payload.os_version,
        arch=payload.arch,
        efi_url=payload.efi_url,
        repo_url=payload.repo_url,
        round=payload.round,
        iso_url=payload.iso_url,
        kernel_variant=payload.kernel_variant,
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return {
        "id": img.id,
        "os_version": img.os_version,
        "arch": img.arch,
        "efi_url": img.efi_url,
        "repo_url": img.repo_url,
        "round": img.round,
        "iso_url": img.iso_url,
        "kernel_variant": img.kernel_variant,
    }


@router.post("/{resource_id}/probe", status_code=200)
def probe_resource_hardware(
    resource_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """对物理机执行硬件探测并回填字段，仅 ADMIN。

    通过 SSH 采集硬件信息并应用到资源。

    Args:
        resource_id: 目标资源 ID.

    Returns:
        dict: status 与已更新字段列表.

    Raises:
        HTTPException: 403 非 ADMIN / 404 资源不存在 /
            400 非物理机或缺少 primary_ip / 502 探测失败.
    """
    require_admin(current_user)
    from app.core.credentials import decrypt_secret
    from app.modules.resources.hardware_probe import probe_physical_hardware
    from app.modules.resources.models import Resource
    from app.modules.resources.service import apply_hardware_probe

    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "resource not found")
    if resource.resource_type != ResourceType.PHYSICAL.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a physical resource")
    if not resource.primary_ip:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "resource has no primary_ip")
    try:
        probe = probe_physical_hardware(
            host=resource.primary_ip,
            username=resource.ssh_username,
            password=decrypt_secret(resource.ssh_password_ciphertext),
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"hardware probe failed: {exc}",
        ) from exc
    apply_hardware_probe(db, resource, probe)
    return {
        "status": "ok",
        "fields_updated": sorted(k for k, v in probe.items() if v is not None),
    }


@router.delete("/install-images/{image_id}")
def delete_install_image(
    image_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """删除指定 PXE 安装镜像，仅 ADMIN。

    Args:
        image_id: 目标镜像 ID.

    Returns:
        dict: {"status": "deleted"}.

    Raises:
        HTTPException: 403 非 ADMIN / 404 镜像不存在.
    """
    require_admin(current_user)
    from app.modules.resources.physical_install_models import PhysicalInstallImage

    img = db.get(PhysicalInstallImage, image_id)
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Install image not found",
        )
    db.delete(img)
    db.commit()
    return {"status": "deleted"}


class InstallBaseVariantIn(BaseModel):
    os_version: str
    base_kernel_variant: str


@router.get("/install-image-base-variants")
def list_install_base_variants(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """列出各发行版安装基础内核变体，仅 ADMIN。"""
    require_admin(current_user)
    from sqlalchemy import select as sa_select

    from app.modules.resources.install_sources import ensure_default_install_base_variants
    from app.modules.resources.physical_install_models import InstallImageBaseVariant

    ensure_default_install_base_variants(db)
    rows = db.execute(
        sa_select(InstallImageBaseVariant).order_by(InstallImageBaseVariant.os_version)
    ).scalars().all()
    return [
        {"os_version": r.os_version, "base_kernel_variant": r.base_kernel_variant}
        for r in rows
    ]


@router.put("/install-image-base-variants")
def update_install_base_variant(
    payload: InstallBaseVariantIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """设置发行版安装基础内核变体，仅 ADMIN。"""
    require_admin(current_user)
    from app.modules.resources.install_sources import set_install_image_base_variant

    set_install_image_base_variant(db, payload.os_version, payload.base_kernel_variant)
    return {"os_version": payload.os_version, "base_kernel_variant": payload.base_kernel_variant}


class InstallRequest(BaseModel):
    image_id: str


@router.post("/{resource_id}/install")
def install_resource(
    resource_id: str,
    payload: InstallRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    """在物理机上触发 PXE 安装。仅 ADMIN。"""
    require_admin(current_user)

    from app.modules.resources.physical_install_models import PhysicalInstallImage
    from app.modules.vms.pxe_install import run_pxe_install_task

    resource = get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    if resource.resource_type != ResourceType.PHYSICAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PHYSICAL resources can be PXE installed",
        )
    try:
        ensure_resource_not_testing(db, resource, action="手动重装")
    except ResourceBusyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    physical_spec = resource.physical_spec
    if physical_spec is None or not physical_spec.bmc_ip:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="物理机缺少 BMC 配置，无法触发 PXE 重装",
        )
    if not resource.mac_address or not resource.primary_ip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource must have bmc_ip, mac_address, and primary_ip",
        )

    image = db.get(PhysicalInstallImage, payload.image_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Install image not found",
        )
    # 安装镜像架构必须与资源架构一致（前端过滤只是体验，后端校验才是边界）。
    if image.arch and image.arch != resource.arch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Install image arch {image.arch} does not match resource arch {resource.arch}",
        )
    # 安装源必须已登记（local OS 树）；未登记的行不可触发（杜绝 ISO 下载兜底路径）。
    if not image.repo_url or not image.efi_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Install image has no local install source (not registered)",
        )

    task = run_pxe_install_task.delay(resource_id, payload.image_id, current_user.id)

    record_audit_log(
        db,
        actor_user_id=current_user.id,
        action="resource.install",
        target_type="resource",
        target_id=resource.id,
        detail={
            "resource_code": resource.resource_code,
            "image_id": payload.image_id,
            "os_version": image.os_version,
            "task_id": task.id,
        },
    )
    db.commit()
    return {"status": "scheduled", "task_id": task.id}


@router.get("/{resource_id}", response_model=ResourceRead)
def read_resource(
    resource_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    """
    读取单个资源详情。虚拟资源读取时顺手触发被中断 VM 销毁任务的懒恢复，
    再跑懒释放过期租约；若期间租约状态变化会重新取一遍资源避免脏读。
    """
    resource = get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    if resource.resource_type == ResourceType.VIRTUAL.value:
        recover_interrupted_tasks(
            db,
            trigger=RecoveryTrigger.LAZY_READ,
            task_types=(RecoveryTaskType.VM_DESTROY,),
        )
    if release_expired_leases(db):
        db.commit()
        resource = get_resource(db, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return serialize_resource(db, resource)


@router.patch("/{resource_id}", response_model=ResourceRead)
def update_resource_endpoint(
    resource_id: str,
    payload: ResourceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    """更新受管资源字段，按策略与不变量校验后记录审计日志。

    会先懒释放过期租约再更新。

    Args:
        resource_id: 目标资源 ID.
        payload: 资源更新字段.

    Returns:
        ResourceRead: 更新后的资源.

    Raises:
        HTTPException: 404 资源不存在 / 403 违反策略 /
            400 违反不变量.
    """
    if release_expired_leases(db):
        db.commit()
    resource = get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    try:
        update_managed_resource(db, actor=current_user, resource=resource, payload=payload)
    except ResourceBusyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ResourcePolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ResourceInvariantError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    record_audit_log(
        db,
        actor_user_id=current_user.id,
        action="resource.update",
        target_type="resource",
        target_id=resource.id,
        detail={
            "resource_code": resource.resource_code,
            "fields": sorted(payload.model_fields_set),
        },
    )
    db.commit()
    db.refresh(resource)
    return serialize_resource(db, resource)

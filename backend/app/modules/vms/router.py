# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated, NoReturn

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
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
from app.modules.resources.models import ResourceType
from app.modules.resources.schemas import ResourceRead
from app.modules.resources.service import get_resource, get_resource_including_deleted
from app.modules.tasks.recovery import (
    RecoveryTaskType,
    RecoveryTrigger,
    recover_interrupted_tasks,
)
from app.modules.tasks.schemas import TaskEventRead
from app.modules.users.models import User
from app.modules.vms.image_discovery import (
    ImageDiscoveryError,
    PrecheckCustomKernelError,
    discover_images,
    list_kernel_variants,
)
from app.modules.vms.iso_storage import (
    ISOInsufficientStorageError,
    ISOStorage,
    ISOStorageUnavailableError,
    ISOTooLargeError,
    ISOValidationError,
    get_iso_storage,
)
from app.modules.vms.schemas import (
    KernelVariantRead,
    VMBatchCreate,
    VMConsoleRead,
    VMImageRead,
    VMISORead,
    VMPowerRead,
    VMPowerRequest,
    VMReleaseBatchRequest,
    VMReleaseRead,
    VMReleaseRequest,
    VMRequestCreate,
    VMRequestRead,
)
from app.modules.vms.service import (
    UnsupportedKernel64kVersionError,
    VMConflictError,
    VMDhcpLeaseFetchError,
    VMDhcpLeaseNotFoundError,
    VMImageNotFoundError,
    VMPolicyError,
    VMQueueUnavailableError,
    batch_release_vms,
    cancel_vm_request,
    get_vm_console_config,
    get_vm_power_state,
    get_vm_request,
    list_vm_request_events,
    list_vm_resource_events,
    operate_vm_power,
    paginate_vm_requests,
    paginate_vms,
    refresh_vm_primary_ip,
    request_vm_release,
    serialize_vm_request,
    submit_vm_request,
)

images_router = APIRouter(prefix="/vm-images", tags=["vms"])
isos_router = APIRouter(prefix="/vm-isos", tags=["vms"])
requests_router = APIRouter(prefix="/vm-requests", tags=["vms"])
vms_router = APIRouter(prefix="/vms", tags=["vms"])

# VM 路由：请求解析 + 鉴权入口 + 状态码映射，业务规则在 service。
# 跨端点约定：
# - 可写端点统一走幂等(begin_http_idempotent_request → service → 记响应 → 提交)。
# - 读端点顺手触发 recover_interrupted_tasks(LAZY_READ) 和 release_expired_leases，
#   在用户读取时收敛中断任务和过期租约(懒恢复/懒释放)，不另起后台轮询。


def raise_policy_error(exc: Exception) -> NoReturn:
    """VM 权限/策略错误 → 403。"""
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def raise_conflict_error(exc: Exception) -> None:
    """VM 状态冲突 → 409。"""
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def raise_service_unavailable(exc: Exception) -> NoReturn:
    """依赖不可用(镜像仓库/Celery broker/存储) → 503。"""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    ) from exc


@dataclass(frozen=True)
class IdempotentRequestEnvelope:
    """请求对象与幂等键的打包依赖。"""

    request: Request
    idempotency_key: str | None


def idempotent_envelope(
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> IdempotentRequestEnvelope:
    return IdempotentRequestEnvelope(request=envelope.request, idempotency_key=idempotency_key)


@images_router.get("", response_model=list[VMImageRead])
def read_vm_images(
    current_user: Annotated[User, Depends(get_current_user)],
    dist: str | None = None,
) -> list[VMImageRead]:
    try:
        return [
            VMImageRead(
                dist=image.dist,
                os_version=image.os_version,
                image_round=image.image_round,
                arch=image.arch,
                url=image.url,
            )
            for image in discover_images(dist=dist)
        ]
    except ImageDiscoveryError as exc:
        raise_service_unavailable(exc)
        raise



@images_router.get("/kernel-variants", response_model=list[KernelVariantRead])
def read_kernel_variants(
    current_user: Annotated[User, Depends(get_current_user)],
    os_version: str,
    image_round: str,
    arch: str,
) -> list[KernelVariantRead]:
    """枚举某轮次下可选内核变体（dailybuild ``*-with-kernel-*`` 子目录）。

    供前端在选定 OS 版本 + 轮次 + 架构后加载变体下拉。dailybuild 不可达
    或该轮次无内核变体时返回空列表（前端走手填 RPM URL 兜底）。
    """
    variants = list_kernel_variants(
        os_version=os_version, image_round=image_round, arch=arch
    )
    return [
        KernelVariantRead(variant=v.variant, kernel_version_prefix=v.kernel_version_prefix)
        for v in variants
    ]


@isos_router.post("", response_model=VMISORead, status_code=status.HTTP_201_CREATED)
async def upload_vm_iso(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[ISOStorage, Depends(get_iso_storage)],
    filename: Annotated[str, Query(min_length=1, max_length=255)],
) -> VMISORead:
    """
    流式上传手动安装 ISO。强制要求 Content-Length(411)，按 ISO 存储异常
    精确映射 413/507/400/503，写审计日志后返回 SHA-256 命名的下载路径。
    """
    content_length_header = request.headers.get("content-length")
    if content_length_header is None:
        raise HTTPException(
            status_code=status.HTTP_411_LENGTH_REQUIRED,
            detail="Content-Length header is required",
        )
    try:
        content_length = int(content_length_header)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content-Length header must be an integer",
        ) from exc

    try:
        stored = await storage.store(
            filename=filename,
            content_length=content_length,
            chunks=request.stream(),
        )
    except ISOTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except ISOInsufficientStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=str(exc),
        ) from exc
    except ISOValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ISOStorageUnavailableError as exc:
        raise_service_unavailable(exc)

    record_audit_log(
        db,
        actor_user_id=current_user.id,
        action="vm.iso.upload",
        target_type="vm_iso",
        target_id=None,
        detail={
            "filename": filename,
            "sha256": stored.sha256,
            "size_bytes": stored.size_bytes,
            "url": stored.download_path,
        },
    )
    db.commit()
    return VMISORead(
        url=stored.download_path,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
    )


@requests_router.post(
    "",
    response_model=VMRequestRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_vm_request_endpoint(
    payload: VMRequestCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> VMRequestRead | JSONResponse:
    decision = begin_http_idempotent_request(
        db,
        actor=current_user,
        request=envelope.request,
        key=envelope.idempotency_key,
        payload=payload.model_dump(mode="json"),
    )
    if decision.replay is not None:
        return decision.replay
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    with abandon_idempotency_on_error(db, decision.record):
        try:
            vm_request = submit_vm_request(db, actor=current_user, payload=payload)
        except VMPolicyError as exc:
            raise_policy_error(exc)
            raise
        except PrecheckCustomKernelError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except VMImageNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except UnsupportedKernel64kVersionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except ImageDiscoveryError as exc:
            raise_service_unavailable(exc)
        except VMQueueUnavailableError as exc:
            raise_service_unavailable(exc)

        response = serialize_vm_request(db, vm_request).model_dump(mode="json")
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_202_ACCEPTED,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


@requests_router.post(
    "/batch",
    response_model=list[VMRequestRead],
    status_code=status.HTTP_202_ACCEPTED,
)
def create_vm_batch_endpoint(
    payload: VMBatchCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> list[VMRequestRead] | JSONResponse:
    """单次请求创建 N 台相同 VM。"""
    decision = begin_http_idempotent_request(
        db,
        actor=current_user,
        request=envelope.request,
        key=envelope.idempotency_key,
        payload=payload.model_dump(mode="json"),
    )
    if decision.replay is not None:
        return decision.replay
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    single_fields = {
        "install_type": payload.install_type,
        "dist": payload.dist,
        "os_version": payload.os_version,
        "image_round": payload.image_round,
        "image_url": payload.image_url,
        "kernel_version": payload.kernel_version,
        "vcpu_count": payload.vcpu_count,
        "memory_mb": payload.memory_mb,
        "data_disk_count": payload.data_disk_count,
        "extra_nic_num": payload.extra_nic_num,
        "purpose": payload.purpose,
        "expected_ends_at": payload.expected_ends_at,
    }
    results: list = []
    with abandon_idempotency_on_error(db, decision.record):
        try:
            for spec in payload.specs:
                for _ in range(spec.count):
                    single_spec = VMRequestCreate(arch=spec.arch, **single_fields)
                    vm_request = submit_vm_request(db, actor=current_user, payload=single_spec)
                    results.append(vm_request)
        except VMPolicyError as exc:
            raise_policy_error(exc)
            raise
        except VMImageNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except UnsupportedKernel64kVersionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except ImageDiscoveryError as exc:
            raise_service_unavailable(exc)
        except VMQueueUnavailableError as exc:
            raise_service_unavailable(exc)

        response = [serialize_vm_request(db, r).model_dump(mode="json") for r in results]
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_202_ACCEPTED,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


@requests_router.get("", response_model=PageResponse[VMRequestRead])
def read_vm_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    show_all: Annotated[bool, Query(alias="all")] = False,
) -> PageResponse[VMRequestRead]:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_CREATE,),
    )
    requests, total = paginate_vm_requests(
        db,
        actor=current_user,
        show_all=show_all,
        pagination=pagination,
    )
    items = [serialize_vm_request(db, request) for request in requests]
    return PageResponse(items=items, total=total, page=pagination.page)


@requests_router.post("/{request_id}/cancel", response_model=VMRequestRead)
def cancel_vm_request_endpoint(
    request_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> VMRequestRead:
    vm_request = get_vm_request(db, request_id)
    if vm_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM request not found")
    try:
        cancelled = cancel_vm_request(db, request=vm_request, actor=current_user)
    except VMPolicyError as exc:
        raise_policy_error(exc)
        raise
    except VMConflictError as exc:
        raise_conflict_error(exc)
        raise
    db.commit()
    return serialize_vm_request(db, cancelled)


@requests_router.get("/{request_id}/events", response_model=list[TaskEventRead])
def read_vm_request_events(
    request_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskEventRead]:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_CREATE,),
    )
    vm_request = get_vm_request(db, request_id)
    if vm_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM request not found")
    return list_vm_request_events(db, vm_request)


@vms_router.get("", response_model=PageResponse[ResourceRead])
def read_vms(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    show_all: Annotated[bool, Query(alias="all")] = False,
    search: Annotated[str | None, Query()] = None,
) -> PageResponse[ResourceRead]:
    if release_expired_leases(db):
        db.commit()
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_DESTROY,),
    )
    items, total = paginate_vms(
        db,
        actor=current_user,
        show_all=show_all,
        pagination=pagination,
        search=search,
    )
    return PageResponse(items=items, total=total, page=pagination.page)


@vms_router.get("/{resource_id}/console", response_model=VMConsoleRead)
def read_vm_console(
    resource_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> VMConsoleRead:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_DESTROY,),
    )
    resource = get_resource(db, resource_id)
    if resource is None or resource.resource_type != ResourceType.VIRTUAL.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    try:
        return get_vm_console_config(db, resource=resource, actor=current_user)
    except VMPolicyError as exc:
        raise_policy_error(exc)
        raise
    except VMConflictError as exc:
        raise_conflict_error(exc)
        raise


@vms_router.get("/{resource_id}/power", response_model=VMPowerRead)
def read_vm_power(
    resource_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> VMPowerRead:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_DESTROY,),
    )
    resource = get_resource_including_deleted(db, resource_id)
    if resource is None or resource.resource_type != ResourceType.VIRTUAL.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    if resource.deleted_at is not None:
        vm_name = resource.virtual_spec.vm_name if resource.virtual_spec else resource.name
        return VMPowerRead(
            resource_id=resource.id,
            vm_name=vm_name,
            power_state="destroyed",
        )
    try:
        return get_vm_power_state(db, resource=resource, actor=current_user)
    except VMPolicyError as exc:
        raise_policy_error(exc)
        raise
    except VMConflictError as exc:
        raise_conflict_error(exc)
        raise


@vms_router.post("/{resource_id}/power", response_model=VMPowerRead)
def operate_vm_power_endpoint(
    resource_id: str,
    payload: VMPowerRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    envelope: Annotated[IdempotentRequestEnvelope, Depends(idempotent_envelope)],
) -> VMPowerRead | JSONResponse:
    decision = begin_http_idempotent_request(
        db,
        actor=current_user,
        request=envelope.request,
        key=envelope.idempotency_key,
        payload=payload.model_dump(mode="json"),
    )
    if decision.replay is not None:
        return decision.replay
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    with abandon_idempotency_on_error(db, decision.record):
        resource = get_resource(db, resource_id)
        if resource is None or resource.resource_type != ResourceType.VIRTUAL.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
        try:
            result = operate_vm_power(
                db,
                resource=resource,
                actor=current_user,
                action=payload.action,
            )
        except VMPolicyError as exc:
            raise_policy_error(exc)
            raise
        except VMConflictError as exc:
            raise_conflict_error(exc)
            raise

        response = result.model_dump(mode="json")
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_200_OK,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)


@vms_router.get("/{resource_id}/events", response_model=list[TaskEventRead])
def read_vm_events(
    resource_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskEventRead]:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_DESTROY,),
    )
    resource = get_resource_including_deleted(db, resource_id)
    if resource is None or resource.resource_type != ResourceType.VIRTUAL.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    return list_vm_resource_events(db, resource)


@vms_router.post("/{resource_id}/refresh-ip", response_model=ResourceRead)
def refresh_vm_ip_endpoint(
    resource_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceRead:
    resource = get_resource(db, resource_id)
    if resource is None or resource.resource_type != ResourceType.VIRTUAL.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    try:
        refreshed = refresh_vm_primary_ip(db, resource=resource, actor=current_user)
    except VMPolicyError as exc:
        raise_policy_error(exc)
        raise
    except VMConflictError as exc:
        raise_conflict_error(exc)
        raise
    except VMDhcpLeaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VMDhcpLeaseFetchError as exc:
        raise_service_unavailable(exc)
    db.commit()
    return refreshed


@vms_router.post("/{resource_id}/release", response_model=VMReleaseRead)
def release_vm_endpoint(
    resource_id: str,
    payload: VMReleaseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    envelope: Annotated[IdempotentRequestEnvelope, Depends(idempotent_envelope)],
) -> VMReleaseRead | JSONResponse:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.VM_DESTROY,),
    )
    decision = begin_http_idempotent_request(
        db,
        actor=current_user,
        request=envelope.request,
        key=envelope.idempotency_key,
        payload=payload.model_dump(mode="json"),
    )
    if decision.replay is not None:
        return decision.replay
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    with abandon_idempotency_on_error(db, decision.record):
        resource = get_resource(db, resource_id)
        if resource is None or resource.resource_type != ResourceType.VIRTUAL.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")

        try:
            request_vm_release(db, resource=resource, actor=current_user, reason=payload.reason)
        except VMPolicyError as exc:
            raise_policy_error(exc)
            raise
        except VMQueueUnavailableError as exc:
            raise_service_unavailable(exc)
        except VMConflictError as exc:
            raise_conflict_error(exc)
            raise

        response = VMReleaseRead(resource_id=resource.id, status="queued").model_dump(mode="json")
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_200_OK,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)


@vms_router.post("/batch-release", response_model=None)
def release_vm_batch_endpoint(
    payload: VMReleaseBatchRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, list[str]] | JSONResponse:
    decision = begin_http_idempotent_request(
        db,
        actor=current_user,
        request=envelope.request,
        key=envelope.idempotency_key,
        payload=payload.model_dump(mode="json"),
    )
    if decision.replay is not None:
        return decision.replay
    if decision.record is None:
        raise RuntimeError("幂等请求必须已领取记录")

    with abandon_idempotency_on_error(db, decision.record):
        result = batch_release_vms(
            db,
            resource_ids=payload.resource_ids,
            actor=current_user,
            reason=payload.reason,
        )
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=result,
            status_code=status.HTTP_200_OK,
        )
        db.commit()
    return JSONResponse(content=result, status_code=status.HTTP_200_OK)

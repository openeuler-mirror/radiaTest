# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
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
from app.modules.leases.import_service import LeaseImportFormatError, import_leases
from app.modules.leases.schemas import (
    LeaseCreateForRole,
    LeaseEventListParams,
    LeaseEventRead,
    LeaseExtend,
    LeaseImportRequest,
    LeaseImportResult,
    LeaseRead,
    LeaseReleaseNormalized,
    ResourceCredentialRead,
)
from app.modules.leases.service import (
    CredentialPolicyError,
    CredentialReadError,
    LeaseConflictError,
    LeasePolicyError,
    create_lease,
    extend_lease,
    get_active_lease,
    list_lease_events,
    read_resource_credentials,
    release_expired_leases,
    release_lease,
    serialize_lease,
)
from app.modules.resources.service import get_resource
from app.modules.users.models import User, UserRole

# 租约路由：仅做请求解析、鉴权入口与响应转换，业务规则放在 service。
#
# 可写端点统一遵循同一形态：幂等判定 → 触发 release_expired_leases 懒释放过期
# 租约(在占用/释放/续期/查凭据前顺手收敛状态) → 调 service → 记录幂等响应 →
# 提交。懒释放不抛错，只返回清理数量；VM 租约的真正销毁由 VM 模块异步完成。
resources_router = APIRouter(prefix="/resources", tags=["leases"])
leases_router = APIRouter(prefix="/leases", tags=["leases"])
lease_events_router = APIRouter(prefix="/lease-events", tags=["leases"])


def require_admin(user: User) -> None:
    """仅 ADMIN 可继续的入口鉴权，否则 403。"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


def raise_policy_error(exc: Exception) -> NoReturn:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def raise_conflict_error(exc: Exception) -> None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


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


@lease_events_router.get("", response_model=PageResponse[LeaseEventRead])
def read_lease_events(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    params: Annotated[LeaseEventListParams, Depends()],
) -> PageResponse[LeaseEventRead]:
    items, total = list_lease_events(
        db,
        actor=current_user,
        params=params,
        pagination=pagination,
    )
    return PageResponse(items=items, total=total, page=pagination.page)


@resources_router.post(
    "/{resource_id}/leases",
    response_model=LeaseRead,
    status_code=status.HTTP_201_CREATED,
)
def occupy_resource(
    resource_id: str,
    payload: LeaseCreateForRole,
    envelope: Annotated[IdempotentRequestEnvelope, Depends(idempotent_envelope)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeaseRead | JSONResponse:
    lease_id = command.lease_id
    payload = command.payload
    current_user = command.current_user
    force = command.force
    envelope = command.envelope
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
        if release_expired_leases(db):
            db.commit()
        resource = get_resource(db, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        try:
            lease = create_lease(db, resource=resource, actor=current_user, payload=payload)
        except LeasePolicyError as exc:
            raise_policy_error(exc)
            raise
        except LeaseConflictError as exc:
            raise_conflict_error(exc)
            raise
        except IntegrityError:
            db.rollback()
            raise_conflict_error(LeaseConflictError("Resource is already occupied"))

        response = serialize_lease(db, lease).model_dump(mode="json")
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_201_CREATED,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_201_CREATED)


@leases_router.post("/{lease_id}/release", response_model=LeaseRead)
def release_own_lease(
    lease_id: str,
    payload: LeaseReleaseNormalized,
    envelope: Annotated[IdempotentRequestEnvelope, Depends(idempotent_envelope)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeaseRead | JSONResponse:
    return release_lease_endpoint(
        lease_id=lease_id,
        payload=payload,
        request=envelope.request,
        current_user=current_user,
        db=db,
        idempotency_key=envelope.idempotency_key,
        force=False,
    )


@leases_router.post("/{lease_id}/force-release", response_model=LeaseRead)
def force_release_lease(
    lease_id: str,
    payload: LeaseReleaseNormalized,
    envelope: Annotated[IdempotentRequestEnvelope, Depends(idempotent_envelope)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeaseRead | JSONResponse:
    return release_lease_endpoint(
        lease_id=lease_id,
        payload=payload,
        request=envelope.request,
        current_user=current_user,
        db=db,
        idempotency_key=envelope.idempotency_key,
        force=True,
    )


@dataclass(frozen=True)
class LeaseReleaseCommand:
    """释放端点共用实现的命令参数。"""

    lease_id: str
    payload: LeaseReleaseNormalized
    current_user: User
    envelope: IdempotentRequestEnvelope
    force: bool


def release_lease_endpoint(
    db: Session,
    *,
    command: LeaseReleaseCommand,
) -> LeaseRead | JSONResponse:
    """本人释放(force=False)与强制释放(force=True)端点的共用实现。

    鉴权矩阵由 service.release_lease 按 force 标志判定，路由只负责幂等与
    懒释放的编排和状态码映射。
    """
    lease_id = command.lease_id
    payload = command.payload
    current_user = command.current_user
    force = command.force
    envelope = command.envelope
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
        if release_expired_leases(db):
            db.commit()
        lease = get_active_lease(db, lease_id, for_update=True)
        if lease is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found")

        try:
            released = release_lease(
                db,
                command=LeaseReleaseCommand(
                    lease=lease,
                    actor=current_user,
                    payload=payload,
                    force=force,
                ),
            )
        except LeasePolicyError as exc:
            raise_policy_error(exc)
            raise
        except LeaseConflictError as exc:
            raise_conflict_error(exc)
            raise

        response = serialize_lease(db, released).model_dump(mode="json")
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_200_OK,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)


@leases_router.post("/{lease_id}/extend", response_model=LeaseRead)
def extend_own_lease(
    lease_id: str,
    payload: LeaseExtend,
    envelope: Annotated[IdempotentRequestEnvelope, Depends(idempotent_envelope)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeaseRead | JSONResponse:
    lease_id = command.lease_id
    payload = command.payload
    current_user = command.current_user
    force = command.force
    envelope = command.envelope
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
        if release_expired_leases(db):
            db.commit()
        lease = get_active_lease(db, lease_id, for_update=True)
        if lease is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found")

        try:
            extended = extend_lease(db, lease=lease, actor=current_user, payload=payload)
        except LeasePolicyError as exc:
            raise_policy_error(exc)
            raise
        except LeaseConflictError as exc:
            raise_conflict_error(exc)
            raise

        response = serialize_lease(db, extended).model_dump(mode="json")
        record_idempotency_response(
            db,
            record=decision.record,
            response_body=response,
            status_code=status.HTTP_200_OK,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)


@leases_router.post("/imports", response_model=LeaseImportResult)
def import_leases_endpoint(
    payload: LeaseImportRequest,
    envelope: Annotated[IdempotentRequestEnvelope, Depends(idempotent_envelope)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeaseImportResult | JSONResponse:
    require_admin(current_user)

    if payload.dry_run:
        try:
            return import_leases(db, payload)
        except LeaseImportFormatError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    lease_id = command.lease_id
    payload = command.payload
    current_user = command.current_user
    force = command.force
    envelope = command.envelope
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
            result = import_leases(db, payload)
        except LeaseImportFormatError as exc:
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
            action="lease.import",
            target_type="lease_import",
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


@resources_router.get("/{resource_id}/credentials", response_model=ResourceCredentialRead)
def get_resource_credentials(
    resource_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ResourceCredentialRead:
    if release_expired_leases(db):
        db.commit()
    resource = get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    try:
        return read_resource_credentials(db, resource=resource, actor=current_user)
    except CredentialPolicyError as exc:
        raise_policy_error(exc)
        raise
    except CredentialReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Resource credentials cannot be decrypted; "
                "check RESOURCE_SECRET_KEY or re-enter credentials"
            ),
        ) from exc

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, PageResponse, get_page_params
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.idempotency.http import begin_http_idempotent_request
from app.modules.idempotency.service import (
    abandon_idempotency_on_error,
    record_idempotency_response,
)
from app.modules.tasks.recovery import (
    RecoveryTaskType,
    RecoveryTrigger,
    recover_interrupted_tasks,
)
from app.modules.tasks.schemas import TaskEventRead
from app.modules.test_management.errors import TestJobDeleteError
from app.modules.test_management.models import TestEnvType
from app.modules.test_management.schemas import (
    MugenCaseRead,
    MugenCaseSyncTaskRead,
    TestJobBatchDeleteRequest,
    TestJobBatchDeleteResponse,
    TestJobCreate,
    TestJobDetailRead,
    TestJobRead,
    TestJobTemplateCreate,
    TestJobTemplateRead,
    TestJobTemplateUpdate,
)
from app.modules.test_management.service import (
    MugenSyncConflictError,
    MugenSyncQueueUnavailableError,
    TestCaseSelectionError,
    TestJobImageIndexUnavailableError,
    TestJobImageSelectionError,
    TestJobQueueUnavailableError,
    TestManagementPolicyError,
    attach_pipeline_origins,
    batch_delete_test_jobs,
    create_test_job,
    delete_test_job,
    enqueue_mugen_case_sync,
    get_test_job,
    list_mugen_sync_events,
    list_test_job_events,
    paginate_mugen_cases,
    paginate_test_jobs,
    queue_test_job,
    require_mugen_sync_admin,
    serialize_test_job,
    serialize_test_job_detail,
)
from app.modules.test_management.templates import (
    TestJobTemplateConflictError,
    TestJobTemplateNotFoundError,
    build_availability_context,
    create_test_job_template,
    delete_test_job_template,
    get_test_job_template,
    paginate_test_job_templates,
    serialize_test_job_template,
    serialize_test_job_templates,
    update_test_job_template,
)
from app.modules.users.models import User, UserRole

# 测试管理路由：用例/任务/模板的请求解析、鉴权入口与状态码映射，业务规则在
# service/templates。读端点统一先 recover_interrupted_tasks(LAZY_READ)：在读取
# 前顺手恢复中断的 mugen 同步或测试任务状态，避免页面长期显示卡住的任务。
cases_router = APIRouter(prefix="/test-cases", tags=["test-management"])
jobs_router = APIRouter(prefix="/test-jobs", tags=["test-management"])
templates_router = APIRouter(prefix="/test-job-templates", tags=["test-management"])


class TestCaseListParams(BaseModel):
    """Mugen 用例列表查询参数。"""

    suite: str | None = None
    case: str | None = None
    env_type: TestEnvType | None = None


@cases_router.get("", response_model=PageResponse[MugenCaseRead])
def read_test_cases(
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    params: Annotated[TestCaseListParams, Depends()],
) -> PageResponse[MugenCaseRead]:
    items, total = paginate_mugen_cases(
        db,
        suite=params.suite,
        case=params.case,
        env_type=params.env_type.value if params.env_type else None,
        pagination=pagination,
    )
    return PageResponse(items=items, total=total, page=pagination.page)


@cases_router.post("/sync", response_model=MugenCaseSyncTaskRead)
def sync_test_cases(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MugenCaseSyncTaskRead:
    try:
        require_mugen_sync_admin(current_user)
    except TestManagementPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.MUGEN_SYNC,),
    )
    try:
        task_id = enqueue_mugen_case_sync(db, actor=current_user)
    except TestManagementPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MugenSyncConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MugenSyncQueueUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    db.commit()
    return MugenCaseSyncTaskRead(task_id=task_id, status="queued")


@cases_router.get("/sync/events", response_model=list[TaskEventRead])
def read_mugen_sync_events(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskEventRead]:
    try:
        require_mugen_sync_admin(current_user)
    except TestManagementPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.MUGEN_SYNC,),
    )
    try:
        return list_mugen_sync_events(db, actor=current_user)
    except TestManagementPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@jobs_router.post(
    "",
    response_model=TestJobDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_job_endpoint(
    payload: TestJobCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TestJobDetailRead | JSONResponse:
    record = begin_http_idempotent_request(
        db,
        actor=current_user,
        request=request,
        key=idempotency_key,
        payload=payload.model_dump(mode="json"),
    )

    with abandon_idempotency_on_error(db, record):
        try:
            job = create_test_job(db, actor=current_user, payload=payload)
        except TestJobImageIndexUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except (
            TestCaseSelectionError,
            TestJobImageSelectionError,
            TestManagementPolicyError,
        ) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        db.commit()
        db.refresh(job)
        try:
            queue_test_job(db, job)
        except TestJobQueueUnavailableError as exc:
            job.status = "error"
            job.error_code = "queue_unavailable"
            job.error_message = str(exc)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        response = serialize_test_job_detail(db, job).model_dump(mode="json")
        record_idempotency_response(
            db,
            record=record,
            response_body=response,
            status_code=status.HTTP_201_CREATED,
        )
        db.commit()
    return JSONResponse(content=response, status_code=status.HTTP_201_CREATED)


class TestJobListParams(BaseModel):
    """测试任务列表查询参数。"""

    show_all: Annotated[bool, Field(alias="all")] = False
    name: Annotated[str | None, Field(max_length=128)] = None
    status_filter: Annotated[str | None, Field(alias="status")] = None
    creator: Annotated[str | None, Field(max_length=64)] = None


@jobs_router.get("", response_model=PageResponse[TestJobRead])
def read_test_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
    params: Annotated[TestJobListParams, Depends()],
) -> PageResponse[TestJobRead]:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.TEST_JOB,),
    )
    jobs, total = paginate_test_jobs(
        db,
        actor=current_user,
        show_all=params.show_all,
        pagination=pagination,
        name=params.name,
        status=params.status_filter,
        creator=params.creator,
    )
    origins = attach_pipeline_origins(db, jobs)
    items = [
        serialize_test_job(
            db,
            job,
            pipeline_origin=origins[job.id][0],
            pipeline_origin_deleted=origins[job.id][1],
        )
        for job in jobs
    ]
    return PageResponse(items=items, total=total, page=pagination.page)


def require_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """删除操作的管理员门禁：后端鉴权是最终边界，前端隐藏按钮仅用于体验。"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除测试任务",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin_user)]


@jobs_router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_job_endpoint(
    job_id: int,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    job = get_test_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test job not found")
    try:
        delete_test_job(db, actor=current_user, job=job)
    except TestJobDeleteError as exc:
        if exc.reason == "forbidden":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@jobs_router.post("/batch-delete", response_model=TestJobBatchDeleteResponse)
def batch_delete_test_jobs_endpoint(
    payload: TestJobBatchDeleteRequest,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> TestJobBatchDeleteResponse:
    results = batch_delete_test_jobs(db, actor=current_user, job_ids=payload.ids)
    db.commit()
    return TestJobBatchDeleteResponse(results=results)


@jobs_router.get("/{job_id}", response_model=TestJobDetailRead)
def read_test_job(
    job_id: int,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TestJobDetailRead:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.TEST_JOB,),
    )
    job = get_test_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test job not found")
    return serialize_test_job_detail(db, job)


@jobs_router.get("/{job_id}/events", response_model=list[TaskEventRead])
def read_test_job_events(
    job_id: int,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskEventRead]:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(RecoveryTaskType.TEST_JOB,),
    )
    job = get_test_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test job not found")
    return list_test_job_events(db, job)


def raise_template_write_error(exc: Exception) -> None:
    if isinstance(exc, TestJobTemplateConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, TestJobImageIndexUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@templates_router.get("", response_model=PageResponse[TestJobTemplateRead])
def read_test_job_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PageParams, Depends(get_page_params)],
) -> PageResponse[TestJobTemplateRead]:
    templates, total = paginate_test_job_templates(db, pagination=pagination)
    items = serialize_test_job_templates(
        db,
        templates=templates,
        actor=current_user,
    )
    return PageResponse(items=items, total=total, page=pagination.page)


@templates_router.post(
    "",
    response_model=TestJobTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_job_template_endpoint(
    payload: TestJobTemplateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TestJobTemplateRead:
    try:
        template = create_test_job_template(db, actor=current_user, payload=payload)
    except (
        TestCaseSelectionError,
        TestJobTemplateConflictError,
        TestJobImageIndexUnavailableError,
        TestJobImageSelectionError,
        TestManagementPolicyError,
    ) as exc:
        raise_template_write_error(exc)
    db.commit()
    db.refresh(template)
    context = build_availability_context(db, [template])
    return serialize_test_job_template(
        db,
        template=template,
        actor=current_user,
        context=context,
    )


@templates_router.get("/{template_id}", response_model=TestJobTemplateRead)
def read_test_job_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TestJobTemplateRead:
    try:
        template = get_test_job_template(db, template_id)
    except TestJobTemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    context = build_availability_context(db, [template])
    return serialize_test_job_template(
        db,
        template=template,
        actor=current_user,
        context=context,
    )


@templates_router.patch("/{template_id}", response_model=TestJobTemplateRead)
def update_test_job_template_endpoint(
    template_id: int,
    payload: TestJobTemplateUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TestJobTemplateRead:
    try:
        template = get_test_job_template(db, template_id)
        template = update_test_job_template(
            db,
            actor=current_user,
            template=template,
            payload=payload,
        )
    except TestJobTemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestManagementPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (
        TestCaseSelectionError,
        TestJobTemplateConflictError,
        TestJobImageIndexUnavailableError,
        TestJobImageSelectionError,
    ) as exc:
        raise_template_write_error(exc)
    db.commit()
    db.refresh(template)
    context = build_availability_context(db, [template])
    return serialize_test_job_template(
        db,
        template=template,
        actor=current_user,
        context=context,
    )


@templates_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_job_template_endpoint(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        template = get_test_job_template(db, template_id)
        delete_test_job_template(db, actor=current_user, template=template)
    except TestJobTemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TestManagementPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

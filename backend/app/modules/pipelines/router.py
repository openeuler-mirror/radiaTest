# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.pipelines.schemas import (
    FrameworkRead,
    LatestExecutionRead,
    PipelineConfigCreate,
    PipelineConfigRead,
    PipelineConfigUpdate,
    PipelineExecutionRead,
    PipelineRunJobRead,
    PipelineRunJobRerunRequest,
    PipelineRunNodeInfoRead,
    PipelineRunRead,
    PipelineTriggerRequest,
    PipelineTypeCreate,
    PipelineTypeRead,
    TestModuleTemplateCreate,
    TestModuleTemplateRead,
    TestModuleTemplateUpdate,
)
from app.modules.pipelines.service import (
    _TERMINAL_STATUSES,
    PhysicalResourceUnavailableError,
    PipelineConfigReferencedError,
    PipelineConfigValidationError,
    PipelineEnvironmentBusyError,
    PipelineRunJobRerunConflict,
    PipelineRunJobRerunError,
    PipelineTypeConflictError,
    PipelineTypeReferencedError,
    PipelineTypeSystemDeleteError,
    PipelineTypeValidationError,
    compute_execution_status,
    compute_run_status,
    create_module_template,
    create_pipeline_config,
    create_pipeline_type,
    create_run_job_rerun,
    delete_pipeline_config,
    delete_pipeline_execution,
    delete_pipeline_executions_by_config,
    delete_pipeline_type,
    enqueue_run_jobs,
    ensure_execution_envs_destroyable,
    execution_config_name,
    get_case_mugen_log,
    get_execution_summary,
    get_module_template,
    get_pipeline_config,
    get_pipeline_execution,
    get_pipeline_run,
    get_run_job_detail,
    latest_execution_for_config,
    list_dir_artifact_files,
    list_execution_runs,
    list_frameworks,
    list_module_templates,
    list_mugen_suites,
    list_pipeline_configs,
    list_pipeline_executions,
    list_pipeline_run_jobs,
    list_pipeline_runs,
    list_pipeline_types,
    list_run_job_node_infos,
    list_run_logs,
    read_dir_artifact_file,
    read_run_log_content,
    trigger_pipeline,
    update_module_template,
    update_pipeline_config,
)
from app.modules.tasks.recovery import (
    RecoveryTaskType,
    RecoveryTrigger,
    recover_interrupted_tasks,
)
from app.modules.users.models import User, UserRole
from app.modules.vms.service import UnsupportedKernel64kVersionError

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _recover_pipeline_tasks(db: Session) -> None:
    recover_interrupted_tasks(
        db,
        trigger=RecoveryTrigger.LAZY_READ,
        task_types=(
            RecoveryTaskType.PIPELINE_RUN_JOB,
            RecoveryTaskType.TEST_JOB,
            RecoveryTaskType.VM_CREATE,
        ),
    )


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/module-templates", response_model=list[TestModuleTemplateRead])
def get_module_templates(
    db: DBSession,
    _user: CurrentUser,
    pipeline_type: str | None = None,
) -> list[TestModuleTemplateRead]:
    """列出测试模块模板，可按流水线类型过滤。

    Args:
        pipeline_type: 可选，按流水线类型过滤模板.

    Returns:
        TestModuleTemplateRead 列表.
    """
    templates = list_module_templates(db, pipeline_type=pipeline_type)
    return [TestModuleTemplateRead.model_validate(t, from_attributes=True) for t in templates]


@router.get("/mugen-suites")
def get_mugen_suites(
    db: DBSession,
    _user: CurrentUser,
) -> list[str]:
    """列出可选的 mugen 套件名称。

    Returns:
        套件名称字符串列表.
    """
    return list_mugen_suites(db)


# ---------- pipeline types ----------


@router.get("/types", response_model=list[PipelineTypeRead])
def get_pipeline_types(
    db: DBSession,
    _user: CurrentUser,
) -> list[PipelineTypeRead]:
    """列出所有流水线类型。

    Returns:
        PipelineTypeRead 列表.
    """
    types = list_pipeline_types(db)
    return [PipelineTypeRead.model_validate(t, from_attributes=True) for t in types]


@router.post(
    "/types",
    response_model=PipelineTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def post_pipeline_type(
    payload: PipelineTypeCreate,
    db: DBSession,
    _user: AdminUser,
) -> PipelineTypeRead:
    """新建流水线类型（仅 admin）。

    Args:
        payload: 流水线类型创建参数.

    Returns:
        创建后的 PipelineTypeRead（201）.

    Raises:
        HTTPException: 409 类型冲突 / 422 校验失败.
    """
    try:
        pt = create_pipeline_type(db, payload)
    except PipelineTypeConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PipelineTypeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    db.commit()
    db.refresh(pt)
    return PipelineTypeRead.model_validate(pt, from_attributes=True)


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline_type_endpoint(
    type_id: str,
    db: DBSession,
    _user: AdminUser,
) -> None:
    """删除流水线类型（仅 admin）。

    Args:
        type_id: 要删除的流水线类型 ID.

    Returns:
        204 No Content.

    Raises:
        HTTPException: 403 系统类型不可删 / 409 仍被引用 / 404 不存在.
    """
    try:
        pt = delete_pipeline_type(db, type_id)
    except PipelineTypeSystemDeleteError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PipelineTypeReferencedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if pt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline type not found",
        )
    db.commit()


# ---------- frameworks ----------


@router.get("/frameworks", response_model=list[FrameworkRead])
def get_frameworks(_user: CurrentUser) -> list[FrameworkRead]:
    """列出支持的测试框架。

    Returns:
        FrameworkRead 列表.
    """
    return [FrameworkRead(**f) for f in list_frameworks()]


@router.post(
    "/module-templates",
    response_model=TestModuleTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def post_module_template(
    payload: TestModuleTemplateCreate,
    db: DBSession,
    _user: AdminUser,
) -> TestModuleTemplateRead:
    """新建测试模块模板（仅 admin）。

    Args:
        payload: 测试模块模板创建参数.

    Returns:
        创建后的 TestModuleTemplateRead（201）.
    """
    template = create_module_template(db, payload)
    db.commit()
    db.refresh(template)
    return TestModuleTemplateRead.model_validate(template, from_attributes=True)


@router.put(
    "/module-templates/{template_id}",
    response_model=TestModuleTemplateRead,
)
def patch_module_template(
    template_id: str,
    payload: TestModuleTemplateUpdate,
    db: DBSession,
    _user: AdminUser,
) -> TestModuleTemplateRead:
    """更新测试模块模板（仅 admin）。

    Args:
        template_id: 要更新的模板 ID.
        payload: 模板更新字段.

    Returns:
        更新后的 TestModuleTemplateRead.

    Raises:
        HTTPException: 404 模板不存在.
    """
    template = get_module_template(db, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module template not found",
        )
    update_module_template(db, template, payload)
    db.commit()
    return TestModuleTemplateRead.model_validate(template, from_attributes=True)


@router.post(
    "/configs",
    response_model=PipelineConfigRead,
    status_code=status.HTTP_201_CREATED,
)
def post_pipeline_config(
    payload: PipelineConfigCreate,
    db: DBSession,
    _user: AdminUser,
) -> PipelineConfigRead:
    """新建流水线配置（仅 admin）。

    Args:
        payload: 流水线配置创建参数.

    Returns:
        创建后的 PipelineConfigRead（201）.

    Raises:
        HTTPException: 422 release 配置校验失败（多版本/内核参数冲突/未知 suite）.
    """
    try:
        config = create_pipeline_config(db, payload)
    except PipelineConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    db.commit()
    db.refresh(config)
    return PipelineConfigRead.model_validate(config, from_attributes=True)


@router.get(
    "/configs",
    response_model=list[PipelineConfigRead],
)
def get_pipeline_configs(
    db: DBSession,
    _user: CurrentUser,
) -> list[PipelineConfigRead]:
    """列出所有流水线配置，附带最近一次执行状态。

    Returns:
        PipelineConfigRead 列表，每项含 latest_execution.
    """
    configs = list_pipeline_configs(db)
    result: list[PipelineConfigRead] = []
    for c in configs:
        read = PipelineConfigRead.model_validate(c, from_attributes=True)
        latest = latest_execution_for_config(db, c.id)
        if latest is not None:
            # status 用 compute_execution_status（stored 恒 pending 不准），同 executions 端点。
            read.latest_execution = LatestExecutionRead(
                id=latest.id,
                status=compute_execution_status(db, latest),
                triggered_at=latest.triggered_at,
            )
        result.append(read)
    return result


@router.put(
    "/configs/{config_id}",
    response_model=PipelineConfigRead,
)
def patch_pipeline_config(
    config_id: str,
    payload: PipelineConfigUpdate,
    db: DBSession,
    _user: AdminUser,
) -> PipelineConfigRead:
    """更新流水线配置（仅 admin）。

    Args:
        config_id: 要更新的配置 ID.
        payload: 配置更新字段.

    Returns:
        更新后的 PipelineConfigRead.

    Raises:
        HTTPException: 404 配置不存在; 422 release 配置校验失败.
    """
    config = get_pipeline_config(db, config_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline config not found",
        )
    try:
        update_pipeline_config(db, config, payload)
    except PipelineConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    db.commit()
    return PipelineConfigRead.model_validate(config, from_attributes=True)


@router.post(
    "/trigger",
    response_model=PipelineExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_trigger(
    payload: PipelineTriggerRequest,
    db: DBSession,
    user: AdminUser,
) -> PipelineExecutionRead:
    """触发流水线执行（仅 admin）。

    Args:
        payload: 触发请求，含 config_id 及版本/架构/镜像轮次.

    Returns:
        创建后的 PipelineExecutionRead（201）.

    Raises:
        HTTPException: 404 配置不存在.
    """
    config = get_pipeline_config(db, payload.config_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline config not found",
        )
    try:
        execution, run_jobs = trigger_pipeline(
            db,
            config,
            versions=payload.versions,
            archs=payload.archs,
            image_round=payload.image_round,
            triggered_by=user.id,
        )
    except PhysicalResourceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UnsupportedKernel64kVersionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    db.commit()
    enqueue_run_jobs(db, run_jobs, user.id)
    db.refresh(execution)
    return PipelineExecutionRead.model_validate(execution, from_attributes=True)


def _execution_to_read(db: Session, execution: object) -> PipelineExecutionRead:
    """构造 PipelineExecutionRead，含 read-time 计算的状态、用户名和 completed_at。"""
    execution_status = compute_execution_status(db, execution)
    # execution 进入终态时写入 completed_at。
    if execution_status in _TERMINAL_STATUSES and execution.completed_at is None:
        from datetime import UTC, datetime

        execution.completed_at = datetime.now(UTC)
        db.commit()
    # Resolve triggered_by UUID to username.
    triggered_by = execution.triggered_by
    if triggered_by:
        user = db.get(User, triggered_by)
        if user:
            triggered_by = user.username
    return PipelineExecutionRead.model_validate(
        {
            **execution.__dict__,
            "config_name": execution_config_name(db, execution),
            "status": execution_status,
            "triggered_by": triggered_by,
        },
        from_attributes=True,
    )


@router.get("/executions", response_model=list[PipelineExecutionRead])
def get_executions(
    db: DBSession,
    _user: CurrentUser,
    config_id: str | None = None,
    limit: int | None = None,
) -> list[PipelineExecutionRead]:
    """列出流水线执行记录，可按配置过滤并限制数量。

    Args:
        config_id: 可选，按配置过滤.
        limit: 可选，限制返回数量.

    Returns:
        PipelineExecutionRead 列表（含实时计算状态）.
    """
    items = list_pipeline_executions(db, config_id=config_id, limit=limit)
    return [_execution_to_read(db, e) for e in items]


@router.get("/executions/{execution_id}", response_model=PipelineExecutionRead)
def get_execution_detail(
    execution_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> PipelineExecutionRead:
    """获取单条流水线执行详情。

    Args:
        execution_id: 执行 ID.

    Returns:
        PipelineExecutionRead（含实时计算状态）.

    Raises:
        HTTPException: 404 执行不存在.
    """
    execution = get_pipeline_execution(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline execution not found",
        )
    return _execution_to_read(db, execution)


@router.get(
    "/executions/{execution_id}/runs",
    response_model=list[PipelineRunRead],
)
def get_execution_runs(
    execution_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> list[PipelineRunRead]:
    """列出某次执行下的所有 Run。

    Args:
        execution_id: 执行 ID.

    Returns:
        PipelineRunRead 列表（含实时计算状态）.
    """
    runs = list_execution_runs(db, execution_id)
    return [
        PipelineRunRead.model_validate(
            {**r.__dict__, "status": compute_run_status(db, r)},
            from_attributes=True,
        )
        for r in runs
    ]


@router.get("/runs", response_model=list[PipelineRunRead])
def get_pipeline_runs(
    db: DBSession,
    _user: CurrentUser,
) -> list[PipelineRunRead]:
    """列出所有 Run。

    Returns:
        PipelineRunRead 列表（含实时计算状态）.
    """
    runs = list_pipeline_runs(db)
    return [
        PipelineRunRead.model_validate(
            {**r.__dict__, "status": compute_run_status(db, r)},
            from_attributes=True,
        )
        for r in runs
    ]

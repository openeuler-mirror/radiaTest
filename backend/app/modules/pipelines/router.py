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


@router.get("/runs/{run_id}", response_model=PipelineRunRead)
def get_pipeline_run_detail(
    run_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> PipelineRunRead:
    """获取单个 Run 详情。

    Args:
        run_id: Run ID.

    Returns:
        PipelineRunRead（含实时计算状态）.

    Raises:
        HTTPException: 404 Run 不存在.
    """
    run = get_pipeline_run(db, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found",
        )
    return PipelineRunRead.model_validate(
        {**run.__dict__, "status": compute_run_status(db, run)},
        from_attributes=True,
    )


@router.get(
    "/runs/{run_id}/jobs",
    response_model=list[PipelineRunJobRead],
)
def get_pipeline_run_jobs(
    run_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> list[PipelineRunJobRead]:
    """列出某 Run 下的所有 RunJob。

    Args:
        run_id: Run ID.

    Returns:
        PipelineRunJobRead 列表.
    """
    _recover_pipeline_tasks(db)
    jobs = list_pipeline_run_jobs(db, run_id)
    return [PipelineRunJobRead.model_validate(j, from_attributes=True) for j in jobs]


@router.get(
    "/runs/{run_id}/jobs/{job_id}/nodes",
    response_model=list[PipelineRunNodeInfoRead],
)
def get_run_job_nodes(
    run_id: str,
    job_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> list[PipelineRunNodeInfoRead]:
    """列出某 RunJob 的节点信息。

    Args:
        run_id: Run ID.
        job_id: RunJob ID.

    Returns:
        PipelineRunNodeInfoRead 列表.
    """
    nodes = list_run_job_node_infos(db, job_id)
    return [PipelineRunNodeInfoRead.model_validate(n, from_attributes=True) for n in nodes]


@router.get("/executions/{execution_id}/summary")
def get_execution_summary_endpoint(
    execution_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> dict:
    """获取某次执行的汇总统计。

    Args:
        execution_id: 执行 ID.

    Returns:
        执行汇总字典.

    Raises:
        HTTPException: 404 执行不存在.
    """
    _recover_pipeline_tasks(db)
    summary = get_execution_summary(db, execution_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline execution not found",
        )
    return summary


@router.post("/executions/{execution_id}/destroy-envs")
def destroy_execution_envs_endpoint(
    execution_id: str,
    db: DBSession,
    user: AdminUser,
) -> dict:
    """异步销毁某次执行占用的测试环境（仅 admin）。

    Args:
        execution_id: 执行 ID.

    Returns:
        提交状态字典，任务在后台执行.

    Raises:
        HTTPException: 404 执行不存在.
    """
    execution = get_pipeline_execution(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline execution not found",
        )
    try:
        ensure_execution_envs_destroyable(db, execution_id)
    except PipelineEnvironmentBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    from app.modules.pipelines.tasks import destroy_execution_envs_task

    destroy_execution_envs_task.delay(execution_id, user.id)
    return {"status": "destroying", "message": "销毁任务已提交，正在后台执行"}


@router.get("/runs/{run_id}/logs")
def list_run_logs_endpoint(
    run_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> list[dict]:
    """列出某 Run 的日志产物条目。

    Args:
        run_id: Run ID.

    Returns:
        日志产物元信息字典列表.
    """
    artifacts = list_run_logs(db, run_id)
    return [
        {
            "id": a.id,
            "pipeline_run_id": a.pipeline_run_id,
            "job_id": a.job_id,
            "module": a.module,
            "arch": a.arch,
            "artifact_type": a.artifact_type,
            "artifact_name": a.artifact_name,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ]


@router.get("/runs/{run_id}/logs/{artifact_id}")
def read_run_log_endpoint(
    run_id: str,
    artifact_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> dict:
    """读取某 Run 日志产物的文本内容（展示用，截断至 1MB）。

    Args:
        run_id: Run ID.
        artifact_id: 日志产物 ID.

    Returns:
        含 content 字段的字典.

    Raises:
        HTTPException: 404 日志产物不存在.
    """
    content = read_run_log_content(db, run_id, artifact_id)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log artifact not found",
        )
    return {"content": content}


@router.get("/runs/{run_id}/logs/{artifact_id}/download")
def download_run_log_endpoint(
    run_id: str,
    artifact_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> FileResponse:
    """Download the full log file (no truncation). Unlike the content endpoint
    which truncates to 1MB for display, this streams the full file.
    """
    from app.modules.test_management.models import TestLogArtifact

    artifact = db.get(TestLogArtifact, artifact_id)
    if artifact is None or artifact.pipeline_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log artifact not found",
        )
    if not artifact.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log artifact has no file",
        )
    from pathlib import Path

    path = Path(artifact.storage_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log file not found on disk",
        )
    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=artifact.artifact_name,
    )


@router.get("/runs/{run_id}/logs/{artifact_id}/files/download")
def download_dir_artifact_file_endpoint(
    run_id: str,
    artifact_id: str,
    db: DBSession,
    _user: CurrentUser,
    path: str = "",
) -> FileResponse:
    """Stream a single file from a folder artifact at full size (no truncation).

    The content/listing endpoints truncate to 1 MB for display and append
    "...[truncated, download for full]"; this streams the whole file so that
    promise holds for files inside ``pkg_folder`` artifacts (e.g. the mugen
    case log at ``logs/<suite>/<case>/<ts>.log``).
    """
    from app.modules.test_management.models import TestLogArtifact

    artifact = db.get(TestLogArtifact, artifact_id)
    if artifact is None or artifact.pipeline_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log artifact not found",
        )
    if artifact.artifact_type != "pkg_folder" or not artifact.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a folder artifact",
        )
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="path is required",
        )
    from pathlib import Path

    base = Path(artifact.storage_path).resolve()
    target = (base / path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in folder artifact",
        ) from None
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in folder artifact",
        )
    return FileResponse(
        path=str(target),
        media_type="application/octet-stream",
        filename=target.name,
    )


@router.get("/runs/{run_id}/logs/{artifact_id}/files")
def list_dir_artifact_files_endpoint(
    run_id: str,
    artifact_id: str,
    db: DBSession,
    _user: CurrentUser,
    path: str | None = None,
) -> dict:
    if path is not None:
        content = read_dir_artifact_file(db, run_id, artifact_id, path)
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in folder artifact",
            )
        return {"content": content}
    files = list_dir_artifact_files(db, run_id, artifact_id)
    if files is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder artifact not found",
        )
    return {"files": files}


@router.get("/run-jobs/{run_job_id}")
def get_run_job_detail_endpoint(
    run_job_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> dict:
    """获取某 RunJob 的详情。

    Args:
        run_job_id: RunJob ID.

    Returns:
        RunJob 详情字典.

    Raises:
        HTTPException: 404 RunJob 不存在.
    """
    _recover_pipeline_tasks(db)
    detail = get_run_job_detail(db, run_job_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run job not found",
        )
    return detail


@router.post("/run-jobs/{run_job_id}/cancel", status_code=202)
def cancel_run_job_endpoint(
    run_job_id: str,
    db: DBSession,
    _user: AdminUser,
) -> dict:
    """ADMIN 取消运行中的 RunJob（仅非终止状态可取消）。

    设 cancel_requested=True + status=cancelling。worker 在下一个检查点
    检测到后清理环境并标 cancelled。

    Raises:
        HTTPException: 404 RunJob 不存在 / 409 已终止.
    """
    from app.modules.pipelines.models import PipelineRunJob

    run_job = db.get(PipelineRunJob, run_job_id)
    if run_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run job not found",
        )
    if run_job.status not in ("running", "preparing", "pending"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel RunJob in terminal status: {run_job.status}",
        )
    run_job.cancel_requested = True
    run_job.status = "cancelled" if run_job.status == "pending" else "cancelling"
    # Propagate to TestJob so test_management can check without importing pipelines.
    if run_job.test_job_id:
        from app.modules.test_management.models import TestJob

        test_job = db.get(TestJob, run_job.test_job_id)
        if test_job is not None:
            test_job.cancel_requested = True
    db.commit()
    return {"status": run_job.status}


@router.get("/run-jobs/{run_job_id}/case-runs/{case_run_id}/mugen-log")
def get_case_mugen_log_endpoint(
    run_job_id: str,
    case_run_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> dict:
    """获取某条用例运行的 mugen 日志。

    Args:
        run_job_id: RunJob ID.
        case_run_id: 用例运行 ID.

    Returns:
        mugen 日志字典.

    Raises:
        HTTPException: 404 日志不存在.
    """
    result = get_case_mugen_log(db, run_job_id, case_run_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mugen log not found for this case run",
        )
    return result


@router.post(
    "/run-jobs/{run_job_id}/rerun",
    response_model=PipelineRunJobRead,
    status_code=status.HTTP_201_CREATED,
)
def rerun_cases_endpoint(
    run_job_id: str,
    payload: PipelineRunJobRerunRequest,
    db: DBSession,
    user: CurrentUser,
) -> PipelineRunJobRead:
    """对指定 RunJob 的所选终态用例创建重跑任务。

    Args:
        run_job_id: 源 RunJob ID.
        payload: 含 case_run_ids 的重跑请求.

    Returns:
        重跑生成的 PipelineRunJobRead（201）.

    Raises:
        HTTPException: 400 重跑不可行；409 来源环境状态冲突.
    """
    try:
        rerun = create_run_job_rerun(
            db,
            source_run_job_id=run_job_id,
            case_run_ids=payload.case_run_ids,
        )
    except PipelineRunJobRerunConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PipelineRunJobRerunError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    enqueue_run_jobs(db, [rerun], user.id)
    return PipelineRunJobRead.model_validate(rerun, from_attributes=True)


@router.post("/run-jobs/{run_job_id}/collect-logs")
def collect_run_job_logs_endpoint(
    run_job_id: str,
    db: DBSession,
    _user: AdminUser,
) -> dict:
    """手动触发某 RunJob 的日志汇集(仅 admin)。

    用于 worker 被重启、finally 块未执行的补救。调度 collect_pipeline_logs
    celery task。
    """
    from app.modules.pipelines.models import PipelineRunJob
    from app.modules.pipelines.tasks import collect_pipeline_logs_task

    run_job = db.get(PipelineRunJob, run_job_id)
    if run_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run job not found",
        )
    collect_pipeline_logs_task.delay(run_job_id)
    return {"status": "scheduled", "run_job_id": run_job_id}


# ---------- pipeline config / execution delete ----------


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline_config_endpoint(
    config_id: str,
    db: DBSession,
    _user: AdminUser,
) -> None:
    """删除流水线配置（仅 admin）。

    Args:
        config_id: 要删除的配置 ID.

    Returns:
        204 No Content.

    Raises:
        HTTPException: 409 仍被引用 / 404 不存在.
    """
    try:
        config = delete_pipeline_config(db, config_id)
    except PipelineConfigReferencedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline config not found",
        )
    db.commit()


@router.delete("/executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline_execution_endpoint(
    execution_id: str,
    db: DBSession,
    user: AdminUser,
) -> None:
    """删除单条流水线执行记录（仅 admin）。

    Args:
        execution_id: 执行 ID.

    Returns:
        204 No Content.

    Raises:
        HTTPException: 404 执行不存在.
    """
    execution = delete_pipeline_execution(db, execution_id, actor=user)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline execution not found",
        )
    db.commit()


@router.delete("/configs/{config_id}/executions", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline_executions_by_config_endpoint(
    config_id: str,
    db: DBSession,
    user: AdminUser,
) -> None:
    """按配置批量删除其下所有执行记录（仅 admin）。

    Args:
        config_id: 配置 ID.

    Returns:
        204 No Content.

    Raises:
        HTTPException: 404 配置不存在.
    """
    config = get_pipeline_config(db, config_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline config not found",
        )
    delete_pipeline_executions_by_config(db, config_id, actor=user)
    db.commit()

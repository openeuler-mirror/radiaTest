# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.modules.assistant.service import AssistantContext
from app.modules.assistant.tool_registry import AssistantTool, AssistantToolError
from app.modules.pipelines.service import (
    compute_execution_status,
    execution_config_name,
    get_case_mugen_log,
    get_execution_summary,
    get_run_job_detail,
    latest_execution_for_config,
    list_pipeline_configs,
    list_pipeline_executions,
)

# 助手只读工具：把平台数据裁剪成对 LLM 友好的有界结构(条数/字符上限)，
# 避免把整份日志塞进上下文。所有工具均为查询，不写数据。


class ListPipelineConfigsArguments(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    pipeline_type: str | None = Field(default=None, max_length=64)
    limit: int = Field(default=10, ge=1, le=20)


class ListPipelineExecutionsArguments(BaseModel):
    config_id: str | None = Field(default=None, max_length=36)
    status: Literal["pending", "running", "succeeded", "failed", "error"] | None = None
    version: str | None = Field(default=None, max_length=64)
    arch: str | None = Field(default=None, max_length=32)
    limit: int = Field(default=10, ge=1, le=20)


class GetPipelineExecutionArguments(BaseModel):
    execution_id: str = Field(min_length=1, max_length=36)


class GetRunJobResultArguments(BaseModel):
    run_job_id: str = Field(min_length=1, max_length=36)


class GetFailedCasesArguments(BaseModel):
    run_job_id: str = Field(min_length=1, max_length=36)
    limit: int = Field(default=20, ge=1, le=50)


class GetCaseLogExcerptArguments(BaseModel):
    run_job_id: str = Field(min_length=1, max_length=36)
    case_run_id: str = Field(min_length=1, max_length=36)
    max_chars: int = Field(default=8000, ge=200, le=20000)


def _validate(model: type[BaseModel], raw: dict[str, Any], tool_name: str) -> BaseModel:
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise AssistantToolError(f"Invalid {tool_name} arguments: {exc}") from exc


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _clip(value: Any, limit: int = 2000) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def list_assistant_pipeline_configs(
    db: Session, _context: AssistantContext, raw: dict[str, Any]
) -> dict[str, Any]:
    arguments = _validate(
        ListPipelineConfigsArguments, raw, "list_pipeline_configs"
    )
    matches: list[dict[str, Any]] = []
    for config in list_pipeline_configs(db):
        if arguments.name and arguments.name.casefold() not in config.name.casefold():
            continue
        if arguments.pipeline_type and (
            arguments.pipeline_type.casefold() != config.pipeline_type.casefold()
        ):
            continue
        latest = latest_execution_for_config(db, config.id)
        matches.append(
            {
                "id": config.id,
                "name": config.name,
                "pipeline_type": config.pipeline_type,
                "versions": config.versions,
                "archs": config.archs,
                "dist": config.dist,
                "test_framework": config.test_framework,
                "latest_execution": (
                    {
                        "id": latest.id,
                        "status": compute_execution_status(db, latest),
                        "triggered_at": _timestamp(latest.triggered_at),
                    }
                    if latest
                    else None
                ),
            }
        )
        if len(matches) >= arguments.limit:
            break
    return {"count": len(matches), "configs": matches}


def list_assistant_pipeline_executions(
    db: Session, _context: AssistantContext, raw: dict[str, Any]
) -> dict[str, Any]:
    arguments = _validate(
        ListPipelineExecutionsArguments, raw, "list_pipeline_executions"
    )
    matches: list[dict[str, Any]] = []
    for execution in list_pipeline_executions(db, config_id=arguments.config_id):
        status = compute_execution_status(db, execution)
        if arguments.status and status != arguments.status:
            continue
        if arguments.version and arguments.version not in execution.versions:
            continue
        if arguments.arch and arguments.arch not in execution.archs:
            continue
        matches.append(
            {
                "id": execution.id,
                "config_id": execution.config_id,
                "config_name": execution_config_name(db, execution),
                "status": status,
                "versions": execution.versions,
                "archs": execution.archs,
                "image_round": execution.image_round,
                "triggered_at": _timestamp(execution.triggered_at),
                "completed_at": _timestamp(execution.completed_at),
            }
        )
        if len(matches) >= arguments.limit:
            break
    return {"count": len(matches), "executions": matches}


def get_assistant_pipeline_execution(
    db: Session, _context: AssistantContext, raw: dict[str, Any]
) -> dict[str, Any]:
    arguments = _validate(
        GetPipelineExecutionArguments, raw, "get_pipeline_execution"
    )
    summary = get_execution_summary(db, arguments.execution_id)
    if summary is None:
        raise AssistantToolError("Pipeline execution not found")
    for run in summary.get("runs", []):
        for job in run.get("jobs", []):
            job["nodes"] = [
                {
                    "resource_code": node.get("resource_code"),
                    "role": node.get("role"),
                    "env_set_index": node.get("env_set_index"),
                    "node_index": node.get("node_index"),
                }
                for node in job.get("nodes", [])
            ]
    return {"execution": summary}


def _safe_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case.get("id"),
        "suite_name": case.get("suite_name"),
        "case_name": case.get("case_name"),
        "status": case.get("status"),
        "exit_code": case.get("exit_code"),
        "stdout_summary": _clip(case.get("stdout_summary")),
        "stderr_summary": _clip(case.get("stderr_summary")),
        "sub_cases": case.get("sub_cases") or [],
    }


def get_run_job_result(
    db: Session, _context: AssistantContext, raw: dict[str, Any]
) -> dict[str, Any]:
    arguments = _validate(GetRunJobResultArguments, raw, "get_run_job_result")
    detail = get_run_job_detail(db, arguments.run_job_id)
    if detail is None:
        raise AssistantToolError("Run job not found")
    cases = [_safe_case(case) for case in detail.get("case_runs", [])]
    counts: dict[str, int] = {}
    for case in cases:
        status = str(case.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "run_job": {
            "id": detail.get("id"),
            "pipeline_run_id": detail.get("pipeline_run_id"),
            "module_template_id": detail.get("module_template_id"),
            "arch": detail.get("arch"),
            "env_type": detail.get("env_type"),
            "status": detail.get("status"),
            "error_code": detail.get("error_code"),
            "error_message": _clip(detail.get("error_message")),
            "result_parser": detail.get("result_parser"),
            "counts": counts,
            "case_runs": cases[:50],
            "task_events": [
                {
                    "phase": event.get("phase"),
                    "level": event.get("level"),
                    "message": _clip(event.get("message"), 1000),
                    "created_at": event.get("created_at"),
                }
                for event in detail.get("task_events", [])[-20:]
            ],
            "nodes": [
                {
                    "resource_code": node.get("resource_code"),
                    "role": node.get("role"),
                    "env_type": node.get("env_type"),
                }
                for node in detail.get("nodes", [])
            ],
            "logs": [
                {
                    "id": log.get("id"),
                    "artifact_type": log.get("artifact_type"),
                    "artifact_name": log.get("artifact_name"),
                    "module": log.get("module"),
                    "arch": log.get("arch"),
                }
                for log in detail.get("logs", [])
            ],
        }
    }


def get_failed_cases(
    db: Session, _context: AssistantContext, raw: dict[str, Any]
) -> dict[str, Any]:
    arguments = _validate(GetFailedCasesArguments, raw, "get_failed_cases")
    detail = get_run_job_detail(db, arguments.run_job_id)
    if detail is None:
        raise AssistantToolError("Run job not found")
    cases = [
        _safe_case(case)
        for case in detail.get("case_runs", [])
        if case.get("status") in {"failed", "error", "timeout"}
    ][: arguments.limit]
    return {"run_job_id": arguments.run_job_id, "count": len(cases), "cases": cases}


_ERROR_PATTERN = re.compile(
    r"error|fail|fatal|warn|traceback|exception|timeout|segmentation|panic",
    re.IGNORECASE,
)


def _error_excerpt(content: str, max_chars: int) -> tuple[str, bool]:
    """从日志内容中抽取错误相关片段：匹配 error/fail/traceback 等关键词的行
    并各带前后 2 行上下文；无匹配则取末尾 40 行。超出 max_chars 截断，
    返回 (片段, 是否被截断)。
    """
    lines = content.splitlines()
    selected: set[int] = set()
    for index, line in enumerate(lines):
        if _ERROR_PATTERN.search(line):
            selected.update(range(max(0, index - 2), min(len(lines), index + 3)))
    indexes = (
        sorted(selected)
        if selected
        else range(max(0, len(lines) - 40), len(lines))
    )
    excerpt = "\n".join(lines[index] for index in indexes)
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars]
    return excerpt, len(excerpt) < len(content)


def get_case_log_excerpt(
    db: Session, _context: AssistantContext, raw: dict[str, Any]
) -> dict[str, Any]:
    arguments = _validate(GetCaseLogExcerptArguments, raw, "get_case_log_excerpt")
    log = get_case_mugen_log(db, arguments.run_job_id, arguments.case_run_id)
    if log is None:
        raise AssistantToolError("Case log not found")
    content = str(log.get("content") or "")
    excerpt, truncated = _error_excerpt(content, arguments.max_chars)
    return {
        "run_job_id": arguments.run_job_id,
        "case_run_id": arguments.case_run_id,
        "file_path": log.get("file_path"),
        "excerpt": excerpt,
        "truncated": truncated,
    }


LIST_PIPELINE_CONFIGS_TOOL = AssistantTool.from_function(
    name="list_pipeline_configs",
    description="List pipeline configurations and the computed status of their latest execution.",
    parameters=ListPipelineConfigsArguments.model_json_schema(),
    execute=list_assistant_pipeline_configs,
)

LIST_PIPELINE_EXECUTIONS_TOOL = AssistantTool.from_function(
    name="list_pipeline_executions",
    description="List and filter recent pipeline executions using computed runtime status.",
    parameters=ListPipelineExecutionsArguments.model_json_schema(),
    execute=list_assistant_pipeline_executions,
)

GET_PIPELINE_EXECUTION_TOOL = AssistantTool.from_function(
    name="get_pipeline_execution",
    description="Get a pipeline execution summary, runs, jobs, result counts, and resource codes.",
    parameters=GetPipelineExecutionArguments.model_json_schema(),
    execute=get_assistant_pipeline_execution,
)

GET_RUN_JOB_RESULT_TOOL = AssistantTool.from_function(
    name="get_run_job_result",
    description="Get a bounded RunJob result summary including cases, events, and log metadata.",
    parameters=GetRunJobResultArguments.model_json_schema(),
    execute=get_run_job_result,
)

GET_FAILED_CASES_TOOL = AssistantTool.from_function(
    name="get_failed_cases",
    description="List failed, errored, or timed-out test cases for a RunJob.",
    parameters=GetFailedCasesArguments.model_json_schema(),
    execute=get_failed_cases,
)

GET_CASE_LOG_EXCERPT_TOOL = AssistantTool.from_function(
    name="get_case_log_excerpt",
    description="Read a bounded error-focused excerpt from one test case mugen log.",
    parameters=GetCaseLogExcerptArguments.model_json_schema(),
    execute=get_case_log_excerpt,
)

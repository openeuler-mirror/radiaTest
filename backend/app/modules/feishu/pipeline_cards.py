# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

# 飞书流水线卡片：配置列表、执行记录、触发表单与确认卡。纯展示层，
# 触发动作的幂等由 card_actions 闭环。

from typing import Any
from uuid import uuid4

from app.modules.feishu.cards import (
    action_block,
    button,
    card,
    input_control,
    option,
    primary_button,
    select_static,
    text_block,
)
from app.modules.pipelines.models import PipelineConfig, PipelineExecution

STATUS_LABELS = {
    "pending": "等待中",
    "running": "执行中",
    "succeeded": "成功",
    "failed": "失败",
    "error": "异常",
    "timeout": "超时",
}


def status_label(status: object) -> str:
    value = str(status or "unknown")
    return STATUS_LABELS.get(value, value)


def time_label(value: object) -> str:
    if value is None:
        return "-"
    isoformat = getattr(value, "isoformat", None)
    return str(isoformat())[:19].replace("T", " ") if callable(isoformat) else str(value)


def build_pipeline_menu_card() -> dict[str, Any]:
    return card(
        "流水线",
        [
            text_block("查看流水线配置、正在执行的测试和近期结果。"),
            action_block(
                [
                    primary_button("执行中", "pipeline_executions_running"),
                    button("近期执行", "pipeline_executions_recent"),
                    button("流水线配置", "pipeline_configs"),
                    button("返回首页", "home"),
                ]
            ),
        ],
    )


def build_pipeline_configs_card(
    items: list[dict[str, Any]], *, is_admin: bool
) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    if not items:
        elements.append(text_block("当前没有流水线配置。"))
    for item in items[:5]:
        latest = item.get("latest") or {}
        elements.append(
            text_block(
                f"**{item.get('name') or '-'}**\n"
                f"类型：{item.get('pipeline_type') or '-'}　"
                f"最近状态：{status_label(latest.get('status')) if latest else '暂无执行'}\n"
                f"版本：{', '.join(item.get('versions') or []) or '-'}\n"
                f"架构：{', '.join(item.get('archs') or []) or '-'}"
            )
        )
        actions = []
        if latest.get("id"):
            actions.append(
                button(
                    "最近执行",
                    "pipeline_execution_detail",
                    value={"execution_id": latest["id"]},
                )
            )
        if is_admin:
            actions.append(
                primary_button(
                    "选择并执行",
                    "pipeline_trigger_form",
                    value={"config_id": item["id"]},
                )
            )
        if actions:
            elements.append(action_block(actions))
    elements.append(action_block([button("返回流水线", "pipeline_menu")]))
    return card("流水线配置", elements)


def build_pipeline_executions_card(
    items: list[dict[str, Any]], *, running_only: bool
) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    if not items:
        elements.append(
            text_block("当前没有正在执行的流水线。" if running_only else "暂无执行记录。")
        )
    for item in items[:10]:
        elements.append(
            text_block(
                f"**{item.get('config_name') or '-'}**　"
                f"{status_label(item.get('status'))}\n"
                f"版本：{', '.join(item.get('versions') or []) or '-'}　"
                f"架构：{', '.join(item.get('archs') or []) or '-'}\n"
                f"触发者：{item.get('triggered_by') or '-'}　"
                f"时间：{time_label(item.get('triggered_at'))}\n"
                f"执行 ID：{item.get('id')}"
            )
        )
        elements.append(
            action_block(
                [
                    primary_button(
                        "查看详情",
                        "pipeline_execution_detail",
                        value={"execution_id": item["id"]},
                    )
                ]
            )
        )
    refresh_action = (
        "pipeline_executions_running" if running_only else "pipeline_executions_recent"
    )
    elements.append(
        action_block(
            [
                primary_button("刷新", refresh_action),
                button("返回流水线", "pipeline_menu"),
            ]
        )
    )
    return card("执行中的流水线" if running_only else "近期执行", elements)


def build_pipeline_execution_detail_card(summary: dict[str, Any]) -> dict[str, Any]:
    elements: list[dict[str, Any]] = [
        text_block(
            f"**{summary.get('config_name') or '-'}**\n"
            f"状态：**{status_label(summary.get('status'))}**\n"
            f"版本：{', '.join(summary.get('versions') or []) or '-'}\n"
            f"架构：{', '.join(summary.get('archs') or []) or '-'}\n"
            f"触发者：{summary.get('triggered_by') or '-'}　"
            f"时间：{time_label(summary.get('triggered_at'))}\n"
            f"执行 ID：{summary.get('id')}"
        )
    ]
    jobs = [job for run in summary.get("runs", []) for job in run.get("jobs", [])]
    for job in jobs[:8]:
        counts = job.get("counts") or {}
        elements.append(
            text_block(
                f"**{job.get('arch') or '-'} / {job.get('env_type') or '默认环境'}**　"
                f"{status_label(job.get('status'))}\n"
                f"等待 {counts.get('pending', 0)}　执行中 {counts.get('running', 0)}\n"
                f"通过 {counts.get('passed', 0)}　失败 {counts.get('failed', 0)}　"
                f"异常 {counts.get('error', 0)}　超时 {counts.get('timeout', 0)}"
            )
        )
        elements.append(
            action_block(
                [
                    button(
                        "RunJob 详情",
                        "pipeline_run_job_detail",
                        value={
                            "run_job_id": job.get("id"),
                            "execution_id": summary.get("id"),
                        },
                    )
                ]
            )
        )
    elements.append(
        action_block(
            [
                primary_button(
                    "刷新状态",
                    "pipeline_execution_detail",
                    value={"execution_id": summary.get("id")},
                ),
                button("返回执行中", "pipeline_executions_running"),
            ]
        )
    )
    return card("流水线执行状态", elements)


def build_pipeline_run_job_card(
    detail: dict[str, Any], *, execution_id: str | None
) -> dict[str, Any]:
    cases = detail.get("case_runs") or []
    resource_codes = ", ".join(
        node.get("resource_code") or "-" for node in detail.get("nodes", [])
    )
    counts: dict[str, int] = {}
    for case in cases:
        status = str(case.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    elements = [
        text_block(
            f"模块：**{detail.get('module_name') or detail.get('module_template_id') or '-'}**\n"
            f"状态：**{status_label(detail.get('status'))}**\n"
            f"架构：{detail.get('arch') or '-'}　环境：{detail.get('env_type') or '-'}\n"
            f"资源：{resource_codes or '-'}\n"
            f"总计 {len(cases)}　等待 {counts.get('pending', 0)}　"
            f"执行中 {counts.get('running', 0)}\n"
            f"通过 {counts.get('passed', 0)}　"
            f"失败 {counts.get('failed', 0)}　异常 {counts.get('error', 0)}　"
            f"超时 {counts.get('timeout', 0)}"
        )
    ]
    if detail.get("error_message"):
        elements.append(text_block(f"**错误信息**：{str(detail['error_message'])[:500]}"))
    failed = [
        case
        for case in cases
        if case.get("status") in {"failed", "error", "timeout"}
    ]
    for case in failed[:5]:
        elements.append(
            text_block(
                f"**{case.get('suite_name') or '-'} / {case.get('case_name') or '-'}**\n"
                f"{status_label(case.get('status'))}　退出码："
                f"{case.get('exit_code') if case.get('exit_code') is not None else '-'}\n"
                f"{str(case.get('stderr_summary') or case.get('stdout_summary') or '-')[:500]}"
            )
        )
    actions = [
        primary_button(
            "刷新",
            "pipeline_run_job_detail",
            value={
                "run_job_id": detail.get("id"),
                "execution_id": execution_id,
            },
        )
    ]
    if execution_id:
        actions.append(
            button(
                "返回执行",
                "pipeline_execution_detail",
                value={"execution_id": execution_id},
            )
        )
    elements.append(action_block(actions))
    return card("RunJob 测试结果", elements)


def build_pipeline_permission_card() -> dict[str, Any]:
    return card(
        "无法启动流水线",
        [
            text_block("启动流水线仅限管理员。你仍可以查询执行状态和分析测试日志。"),
            action_block([button("返回首页", "home")]),
        ],
        template="yellow",
    )


def build_pipeline_trigger_form_card(
    config: PipelineConfig,
    *,
    state: dict[str, str],
    error: str | None = None,
) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    if error:
        elements.append(text_block(f"**参数错误**：{error}"))
    elements.extend(
        [
            text_block(f"**{config.name}**\n选择本次执行的版本、架构和镜像轮次。"),
            action_block(
                [
                    select_static(
                        name=f"pipeline_version|{config.id}",
                        placeholder="版本",
                        options=[option(value, value) for value in config.versions],
                        initial_option=state.get("version"),
                    )
                ]
            ),
            action_block(
                [
                    select_static(
                        name=f"pipeline_arch|{config.id}",
                        placeholder="架构",
                        options=[option(value, value) for value in config.archs],
                        initial_option=state.get("arch"),
                    )
                ]
            ),
            text_block("镜像轮次（可留空，使用流水线默认值）"),
            action_block(
                [
                    input_control(
                        name=f"pipeline_image_round|{config.id}",
                        placeholder=config.image_round or "默认值",
                        default_value=state.get("image_round", ""),
                        max_length=64,
                    )
                ]
            ),
            action_block(
                [
                    primary_button(
                        "下一步",
                        "pipeline_trigger_confirm",
                        value={"config_id": config.id},
                    ),
                    button("取消", "home"),
                ]
            ),
        ]
    )
    return card("执行流水线", elements)


def build_pipeline_trigger_confirm_card(
    config: PipelineConfig,
    *,
    version: str,
    arch: str,
    image_round: str | None,
) -> dict[str, Any]:
    confirmation_id = str(uuid4())
    return card(
        "确认执行流水线",
        [
            text_block(
                f"**{config.name}**\n"
                f"版本：{version}\n架构：{arch}\n"
                f"镜像轮次：{image_round or config.image_round or '-'}\n\n"
                "确认后将立即创建执行记录并投递测试任务。"
            ),
            action_block(
                [
                    primary_button(
                        "确认执行",
                        "pipeline_trigger_submit",
                        value={
                            "confirmation_id": confirmation_id,
                            "config_id": config.id,
                            "version": version,
                            "arch": arch,
                            "image_round": image_round or "",
                        },
                    ),
                    button(
                        "返回修改",
                        "pipeline_trigger_form",
                        value={"config_id": config.id},
                    ),
                ]
            ),
        ],
        template="orange",
    )


def build_pipeline_started_card(
    config: PipelineConfig, execution: PipelineExecution
) -> dict[str, Any]:
    return card(
        "流水线已启动",
        [
            text_block(
                f"**{config.name}** 已开始执行。\n"
                f"状态：pending\n版本：{', '.join(execution.versions)}\n"
                f"架构：{', '.join(execution.archs)}\n执行 ID：{execution.id}"
            ),
            action_block(
                [
                    primary_button(
                        "查看执行状态",
                        "pipeline_execution_detail",
                        value={"execution_id": execution.id},
                    ),
                    button("返回流水线", "pipeline_menu"),
                ]
            ),
        ],
        template="green",
    )


def build_pipeline_trigger_error_card(
    message: str, *, config_id: str | None = None
) -> dict[str, Any]:
    actions = []
    if config_id:
        actions.append(
            button("重新选择", "pipeline_trigger_form", value={"config_id": config_id})
        )
    actions.append(button("返回首页", "home"))
    return card(
        "流水线启动失败",
        [text_block(message), action_block(actions)],
        template="red",
    )

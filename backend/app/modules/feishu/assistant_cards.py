# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

# 飞书智能助手卡片：把助手结果/错误/帮助渲染成卡片。

from typing import Any

from app.modules.assistant.service import AssistantResult
from app.modules.feishu.cards import action_block, button, card, text_block


def build_assistant_result_card(result: AssistantResult) -> dict[str, Any]:
    resources: list[dict[str, Any]] = []
    configs: list[dict[str, Any]] = []
    executions: list[dict[str, Any]] = []
    failed_cases: list[dict[str, Any]] = []
    for tool_result in result.tool_results:
        for key, target in (
            ("resources", resources),
            ("configs", configs),
            ("executions", executions),
            ("cases", failed_cases),
        ):
            value = tool_result.data.get(key)
            if isinstance(value, list):
                target.extend(item for item in value if isinstance(item, dict))

    elements = [text_block(result.text)]
    for resource in resources[:5]:
        resource_id = resource.get("id")
        code = resource.get("resource_code") or "-"
        name = resource.get("name") or "-"
        details = (
            f"**{code} · {name}**\n"
            f"架构：{resource.get('arch') or '-'}　CPU：{resource.get('cpu_cores') or '-'} 核\n"
            f"内存：{resource.get('memory_gb') or '-'} GB　状态："
            f"{resource.get('occupancy_status') or '-'}"
        )
        elements.append(text_block(details))
        if isinstance(resource_id, str):
            kind = "physical" if resource.get("resource_type") == "PHYSICAL" else "vm"
            elements.append(
                action_block(
                    [
                        button(
                            "查看详情",
                            "resource_detail",
                            value={
                                "resource_id": resource_id,
                                "kind": kind,
                                "return_action": "home",
                                "page": 0,
                            },
                        )
                    ]
                )
            )
    for config in configs[:5]:
        latest = config.get("latest_execution") or {}
        elements.append(
            text_block(
                f"**流水线：{config.get('name') or '-'}**\n"
                f"类型：{config.get('pipeline_type') or '-'}　框架："
                f"{config.get('test_framework') or '-'}\n"
                f"版本：{', '.join(config.get('versions') or []) or '-'}\n"
                f"架构：{', '.join(config.get('archs') or []) or '-'}　"
                f"最近状态：{latest.get('status') or '暂无执行'}"
            )
        )
        config_id = config.get("id")
        if isinstance(config_id, str):
            elements.append(
                action_block(
                    [
                        button(
                            "选择并执行",
                            "pipeline_trigger_form",
                            value={"config_id": config_id},
                        )
                    ]
                )
            )
    for execution in executions[:5]:
        elements.append(
            text_block(
                f"**执行：{execution.get('config_name') or '-'}**\n"
                f"状态：{execution.get('status') or '-'}　"
                f"架构：{', '.join(execution.get('archs') or []) or '-'}\n"
                f"版本：{', '.join(execution.get('versions') or []) or '-'}\n"
                f"执行 ID：{execution.get('id') or '-'}"
            )
        )
    for case in failed_cases[:5]:
        error = case.get("stderr_summary") or case.get("stdout_summary") or "-"
        elements.append(
            text_block(
                f"**失败用例：{case.get('suite_name') or '-'} / "
                f"{case.get('case_name') or '-'}**\n"
                f"状态：{case.get('status') or '-'}　退出码："
                f"{case.get('exit_code') if case.get('exit_code') is not None else '-'}\n"
                f"摘要：{str(error)[:500]}"
            )
        )
    elements.append(action_block([button("返回首页", "home")]))
    return card("radiaTest 智能助手", elements, template="blue")


def build_assistant_error_card(message: str) -> dict[str, Any]:
    return card(
        "智能助手暂时不可用",
        [text_block(message), action_block([button("返回首页", "home")])],
        template="red",
    )


def build_assistant_help_card() -> dict[str, Any]:
    return card(
        "radiaTest 智能助手",
        [
            text_block(
                "可以直接发送自然语言查询资源，例如：\n"
                "- 找一台空闲的 aarch64 物理机\n"
                "- 查看我正在使用的资源\n"
                "- 找至少 16 核、32 GB 内存的机器\n"
                "- 查看最近失败的流水线执行\n"
                "- 分析某个 RunJob 的失败用例和关键日志"
            ),
            action_block([button("返回首页", "home")]),
        ],
    )

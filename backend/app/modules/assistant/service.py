# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.modules.assistant.tool_registry import AssistantToolError, ToolRegistry

logger = logging.getLogger(__name__)

# 助手系统提示词：约束为只读——只能用提供的工具查事实，不得编造资源/状态/
# 权限/凭据/操作结果，不得声称触发、重跑、修改或删除数据。
SYSTEM_PROMPT = """You are the radiaTest test resource platform assistant.
Use only the supplied tools for platform facts. Never invent resources, status,
permissions, credentials, or operation results. You can inspect resources,
pipeline executions, test results, failed cases, and bounded log excerpts.
This version is read-only: never claim to trigger, rerun, modify, or delete data.
Reply in the user's language and keep the answer concise."""


class AssistantError(Exception):
    """助手执行错误(空响应、工具参数非法、预算耗尽后仍请求工具等)。"""


class LLMClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        """调用 LLM 返回 assistant message，可能含 tool_calls。"""
        raise NotImplementedError(self)


@dataclass(frozen=True)
class AssistantContext:
    """助手调用上下文：当前用户(用于工具内鉴权)与渠道来源。"""

    user: Any
    channel: str
    conversation_id: str | None = None


@dataclass(frozen=True)
class ToolResult:
    name: str
    data: dict[str, Any]


@dataclass(frozen=True)
class AssistantResult:
    text: str
    tool_results: tuple[ToolResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AssistantRunRequest:
    """助手运行入参：会话、上下文、用户文本、LLM 客户端与工具注册表。"""

    db: Session
    context: AssistantContext
    text: str
    client: LLMClient
    registry: ToolRegistry
    max_rounds: int = 6


def run_assistant(
    *,
    request: AssistantRunRequest,
) -> AssistantResult:
    db = request.db
    context = request.context
    text = request.text
    client = request.client
    registry = request.registry
    max_rounds = request.max_rounds
    """运行一轮工具调用循环：LLM 返回 tool_calls 则执行工具并回填结果，再让
    LLM 继续，直到 LLM 不再请求工具给出最终文本答案。

    非直观约束：
    - 工具调用轮次有上限(max_rounds，默认 6)，耗尽后强制注入"用已有证据作答"
      的系统消息再要一次无工具的回答，防止无限工具循环。
    - 耗尽预算后若 LLM 仍请求工具，视为错误抛 AssistantError。
    - 工具参数解析或执行失败立即抛错，不静默吞掉。
    """
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"Current radiaTest user: {context.user.username}; "
                f"role: {context.user.role}."
            ),
        },
        {"role": "user", "content": text},
    ]
    results: list[ToolResult] = []
    for round_index in range(max_rounds):
        message = client.complete(messages, registry.schemas())
        messages.append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return AssistantResult(text=content.strip(), tool_results=tuple(results))
            raise AssistantError("LLM returned an empty assistant response")
        tool_names: list[str] = []
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            function_spec = call.get("function") or {}
            if not isinstance(function_spec, dict):
                continue
            tool_names.append(str(function_spec.get("name", "unknown")))
        logger.info(
            "Assistant tool round=%s tools=%s",
            round_index + 1,
            ",".join(tool_names),
        )
        for call in tool_calls:
            try:
                function = call["function"]
                arguments = json.loads(function.get("arguments") or "{}")
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be an object")
                data = registry.execute(
                    db=db,
                    context=context,
                    name=str(function["name"]),
                    arguments=arguments,
                )
                call_id = str(call["id"])
            except (
                KeyError,
                TypeError,
                ValueError,
                AssistantToolError,
            ) as exc:
                raise AssistantError(str(exc)) from exc
            results.append(ToolResult(name=str(function["name"]), data=data))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(data, ensure_ascii=False),
                }
            )
    messages.append(
        {
            "role": "system",
            "content": (
                "The tool-call budget is exhausted. Do not request more tools. "
                "Answer now using the evidence already returned by the tools, "
                "and clearly state any information that is still unavailable."
            ),
        }
    )
    logger.info("Assistant tool budget exhausted; requesting final answer")
    message = client.complete(messages, [])
    if message.get("tool_calls"):
        raise AssistantError("LLM requested tools after tool-call budget was exhausted")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return AssistantResult(text=content.strip(), tool_results=tuple(results))
    raise AssistantError("LLM returned an empty final response after tool-call limit")

# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from app.core.config import Settings


class LLMClientError(Exception):
    """LLM 请求或响应解析失败(HTTP 错误、超时、格式非法)。"""


class AssistantNotConfiguredError(LLMClientError):
    """助手未配置(BASE_URL/API_KEY/MODEL 任一缺失或未启用)。"""


def chat_completions_url(base_url: str) -> str:
    """把 BASE_URL 规范成 /chat/completions 端点；已带后缀则原样返回。"""
    normalized = base_url.rstrip("/")
    suffix = "/chat/completions"
    return normalized if normalized.endswith(suffix) else f"{normalized}{suffix}"


@dataclass(frozen=True)
class OpenAICompatibleClient:
    """兼容 OpenAI Chat Completions 协议的最小 LLM 客户端。

    temperature 固定为 0，保证助手回答可复现、不发散。
    """

    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 30
    opener: Callable[..., Any] = urlopen

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        """发起一次补全请求，返回 choices[0].message。

        HTTP 错误、超时或响应结构非法统一抛 LLMClientError，由上层决定重试/失败。
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        request = Request(
            chat_completions_url(self.base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except HTTPError as exc:
            raise LLMClientError(f"LLM request failed with HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise LLMClientError("LLM request failed or timed out") from exc
        try:
            parsed = json.loads(body.decode("utf-8"))
            message = parsed["choices"][0]["message"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LLMClientError("LLM response has an invalid format") from exc
        if not isinstance(message, dict):
            raise LLMClientError("LLM response has an invalid assistant message")
        return message


def create_llm_client(settings: "Settings") -> OpenAICompatibleClient:
    """按配置创建 LLM 客户端；任一必填项缺失则抛 AssistantNotConfiguredError。"""
    missing_feature = not settings.llm_assistant_enabled
    missing_endpoint = not settings.llm_base_url or not settings.llm_api_key
    missing_model = not settings.llm_model
    if missing_feature or missing_endpoint or missing_model:
        raise AssistantNotConfiguredError("LLM assistant is not configured")
    return OpenAICompatibleClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )

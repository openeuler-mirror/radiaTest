# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
from types import SimpleNamespace

from app.modules.assistant.llm_client import OpenAICompatibleClient
from app.modules.assistant.service import AssistantContext, AssistantRunRequest, run_assistant
from app.modules.assistant.tool_registry import AssistantTool, ToolRegistry


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict], list[dict]]] = []

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        self.calls.append((list(messages), tools))
        if len(self.calls) == 1:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "search_resources",
                            "arguments": json.dumps({"arch": "aarch64"}),
                        },
                    }
                ],
            }
        return {"role": "assistant", "content": "找到 1 台 aarch64 机器。"}


def test_assistant_executes_validated_tool_call_and_returns_answer() -> None:
    tool = AssistantTool.from_function(
        name="search_resources",
        description="Search resources",
        parameters={
            "type": "object",
            "properties": {"arch": {"type": "string"}},
            "additionalProperties": False,
        },
        execute=lambda _db, _context, arguments: {
            "count": 1,
            "resources": [{"id": "resource-1", "arch": arguments["arch"]}],
        },
    )
    client = FakeLLMClient()

    result = run_assistant(
        request=AssistantRunRequest(
            db=SimpleNamespace(),
            context=AssistantContext(
                user=SimpleNamespace(id="user-1", username="te1", role="TE"),
                channel="feishu",
                conversation_id="oc-chat",
            ),
            text="找一台 aarch64 机器",
            client=client,
            registry=ToolRegistry([tool]),
        ),
    )

    assert result.text == "找到 1 台 aarch64 机器。"
    assert result.tool_results[0].name == "search_resources"
    assert result.tool_results[0].data["resources"][0]["id"] == "resource-1"
    assert json.loads(client.calls[1][0][-1]["content"])["count"] == 1


def test_assistant_forces_final_answer_after_tool_round_limit() -> None:
    class ToolChainClient:
        def __init__(self) -> None:
            self.calls: list[list[dict]] = []

        def complete(self, _messages: list[dict], tools: list[dict]) -> dict:
            self.calls.append(tools)
            if tools:
                index = len(self.calls)
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call-{index}",
                            "type": "function",
                            "function": {
                                "name": "inspect",
                                "arguments": "{}",
                            },
                        }
                    ],
                }
            return {"role": "assistant", "content": "根据已获取结果，测试失败。"}

    tool = AssistantTool.from_function(
        name="inspect",
        description="Inspect one test result layer",
        parameters={"type": "object", "properties": {}},
        execute=lambda _db, _context, _arguments: {"status": "failed"},
    )
    client = ToolChainClient()

    result = run_assistant(
        request=AssistantRunRequest(
            db=SimpleNamespace(),
            context=AssistantContext(
                user=SimpleNamespace(id="user-1", username="te1", role="TE"),
                channel="feishu",
            ),
            text="分析最近一次失败",
            client=client,
            registry=ToolRegistry([tool]),
            max_rounds=3,
        ),
    )

    assert result.text == "根据已获取结果，测试失败。"
    assert len(result.tool_results) == 3
    assert client.calls[-1] == []


def test_openai_compatible_client_appends_chat_completions_once() -> None:
    requests = []

    class Response:
        def __enter__(self):
            return self

        @staticmethod
        def __exit__(*_args: object) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return json.dumps(
                {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
            ).encode()

    def opener(request, timeout: int):
        requests.append((request, timeout))
        return Response()

    client = OpenAICompatibleClient(
        api_key="secret",
        base_url="https://llm.example/v1/chat/completions/",
        model="test-model",
        timeout_seconds=12,
        opener=opener,
    )

    result = client.complete([{"role": "user", "content": "hello"}], [])

    assert result["content"] == "ok"
    assert requests[0][0].full_url == "https://llm.example/v1/chat/completions"
    assert requests[0][1] == 12
    assert requests[0][0].headers["Authorization"] == "Bearer secret"

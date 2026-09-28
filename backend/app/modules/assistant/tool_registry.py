# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session


class AssistantToolError(Exception):
    """工具执行或参数校验失败，含工具不支持、参数非法等。"""


ToolExecutor = Callable[[Session, Any, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class AssistantTool:
    """助手可调用工具的描述与执行器，schema() 生成 OpenAI function 工具定义。"""

    name: str
    description: str
    parameters: dict[str, Any]
    execute: ToolExecutor

    @classmethod
    def from_function(
        cls,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any],
        execute: ToolExecutor,
    ) -> "AssistantTool":
        return cls(name=name, description=description, parameters=parameters, execute=execute)

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """已注册工具的查表与执行入口，按名分发；未知名抛 AssistantToolError。"""

    def __init__(self, tools: list[AssistantTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(
        self,
        *,
        db: Session,
        context: Any,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise AssistantToolError(f"Unsupported assistant tool: {name}")
        return tool.execute(db, context, arguments)

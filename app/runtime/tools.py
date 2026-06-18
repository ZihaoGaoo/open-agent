"""工具执行器。

运行时只认 ToolExecutor 接口；具体工具来源（MCP / Skill / Webhook）在 M2 由
各能力子系统注册到 ToolRegistry。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from app.providers.base import ToolCall, ToolDef

# 工具处理函数：接收解析后的参数，返回字符串结果
ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


@runtime_checkable
class ToolExecutor(Protocol):
    def specs(self) -> list[ToolDef]: ...

    async def execute(self, call: ToolCall) -> str: ...


class ToolRegistry:
    """按名称聚合工具定义与处理函数的默认 ToolExecutor 实现。"""

    def __init__(self) -> None:
        self._defs: dict[str, ToolDef] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, spec: ToolDef, handler: ToolHandler) -> None:
        self._defs[spec.name] = spec
        self._handlers[spec.name] = handler

    def specs(self) -> list[ToolDef]:
        return list(self._defs.values())

    async def execute(self, call: ToolCall) -> str:
        handler = self._handlers.get(call.name)
        if handler is None:
            return f"[error] 未知工具: {call.name}"
        return await handler(call.arguments)

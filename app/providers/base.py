"""Provider 中立数据结构与接口。

各 Provider 负责把这套中立结构与自家 API（消息、工具调用、流式事件）互转，
使运行时无需感知具体厂商。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    """模型请求调用某个工具。"""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """中立消息。tool_calls 仅 assistant 轮使用；tool_call_id 仅 tool 轮使用。"""

    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass
class ToolDef:
    """暴露给模型的工具定义（来源可为 MCP / Skill / Webhook）。"""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class GenRequest:
    model: str
    messages: list[Message]
    system: str | None = None
    tools: list[ToolDef] = field(default_factory=list)
    max_tokens: int = 16000
    # 厂商无关的额外参数：effort、thinking、temperature 等，由各 Provider 解释。
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenResult:
    """一次非流式生成的结果。"""

    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None


@dataclass
class StreamEvent:
    """流式事件（归一化）。"""

    type: Literal["text", "tool_call", "thinking", "done", "error"]
    text: str | None = None
    tool_call: ToolCall | None = None
    result: GenResult | None = None  # type == "done" 时携带最终结果


@runtime_checkable
class LLMProvider(Protocol):
    """统一 Provider 接口。"""

    name: str

    async def generate(self, req: GenRequest) -> GenResult: ...

    def stream(self, req: GenRequest) -> AsyncIterator[StreamEvent]: ...

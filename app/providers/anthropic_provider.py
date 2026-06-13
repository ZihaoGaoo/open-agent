"""Claude Provider（默认 / 参考实现）。

默认模型 claude-opus-4-8：adaptive thinking + effort，流式用 messages.stream()。
把中立结构 <-> Anthropic Messages API 互转。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.config import get_settings
from app.providers.base import (
    GenRequest,
    GenResult,
    Message,
    StreamEvent,
    ToolCall,
    ToolDef,
)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        import anthropic  # 懒加载：未使用该 Provider 时不强制安装/导入

        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)

    # ---- 转换：中立 → Anthropic ----
    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "tool":
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id,
                                "content": m.content or "",
                            }
                        ],
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                blocks: list[dict[str, Any]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )
                out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": m.role, "content": m.content or ""})
        return out

    @staticmethod
    def _to_anthropic_tools(tools: list[ToolDef]) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in tools
        ]

    def _build_kwargs(self, req: GenRequest) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": self._to_anthropic_messages(req.messages),
            # 默认开启 adaptive thinking（claude-opus-4-8）
            "thinking": req.params.get("thinking", {"type": "adaptive"}),
        }
        if req.system:
            kwargs["system"] = req.system
        if req.tools:
            kwargs["tools"] = self._to_anthropic_tools(req.tools)
        effort = req.params.get("effort")
        if effort:
            kwargs["output_config"] = {"effort": effort}
        return kwargs

    # ---- 转换：Anthropic → 中立 ----
    @staticmethod
    def _parse_message(msg: Any) -> GenResult:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in msg.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )
        usage = {}
        if getattr(msg, "usage", None) is not None:
            usage = {
                "input_tokens": getattr(msg.usage, "input_tokens", 0),
                "output_tokens": getattr(msg.usage, "output_tokens", 0),
            }
        return GenResult(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=msg.stop_reason or "end_turn",
            usage=usage,
            raw=msg,
        )

    # ---- 接口实现 ----
    async def generate(self, req: GenRequest) -> GenResult:
        msg = await self._client.messages.create(**self._build_kwargs(req))
        return self._parse_message(msg)

    async def stream(self, req: GenRequest) -> AsyncIterator[StreamEvent]:
        kwargs = self._build_kwargs(req)
        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield StreamEvent(type="text", text=delta.text)
                    elif delta.type == "thinking_delta":
                        yield StreamEvent(type="thinking", text=delta.thinking)
            final = await stream.get_final_message()
            yield StreamEvent(type="done", result=self._parse_message(final))

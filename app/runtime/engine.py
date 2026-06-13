"""编排引擎：执行 agentic loop。

loop：组装请求 → 调 Provider → 若 tool_use 则执行工具并回灌 tool_result →
直到 end_turn 或达到 max_iterations。

M1 提供可运行的循环结构；上下文压缩 / 流式事件持久化 / 多 agent 委派在后续里程碑接入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.providers.base import GenRequest, GenResult, LLMProvider, Message
from app.runtime.tools import ToolExecutor


@dataclass
class RunConfig:
    model: str
    system: str | None = None
    max_tokens: int = 16000
    max_iterations: int = 16
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunOutput:
    text: str
    messages: list[Message]
    iterations: int
    usage: dict[str, int]
    stop_reason: str


class AgentRuntime:
    def __init__(self, provider: LLMProvider, tools: ToolExecutor | None = None) -> None:
        self._provider = provider
        self._tools = tools

    async def run(self, config: RunConfig, messages: list[Message]) -> RunOutput:
        history = list(messages)
        tool_specs = self._tools.specs() if self._tools else []
        total_usage: dict[str, int] = {}
        last: GenResult | None = None

        for i in range(config.max_iterations):
            req = GenRequest(
                model=config.model,
                messages=history,
                system=config.system,
                tools=tool_specs,
                max_tokens=config.max_tokens,
                params=config.params,
            )
            last = await self._provider.generate(req)
            _accumulate(total_usage, last.usage)

            # 记录 assistant 轮
            history.append(
                Message(role="assistant", content=last.text, tool_calls=last.tool_calls)
            )

            if not last.tool_calls:
                break

            # 执行工具并回灌结果
            for call in last.tool_calls:
                result = (
                    await self._tools.execute(call)
                    if self._tools
                    else f"[error] 无可用工具执行器: {call.name}"
                )
                history.append(
                    Message(role="tool", content=result, tool_call_id=call.id)
                )

        return RunOutput(
            text=last.text if last else "",
            messages=history,
            iterations=i + 1,
            usage=total_usage,
            stop_reason=last.stop_reason if last else "error",
        )


def _accumulate(acc: dict[str, int], usage: dict[str, int]) -> None:
    for k, v in usage.items():
        acc[k] = acc.get(k, 0) + v

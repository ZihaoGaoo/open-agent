"""运行时流式 + 工具调用循环（用 stub provider，无 DB / 无网络）。"""

from __future__ import annotations

from app.providers.base import GenRequest, GenResult, StreamEvent, ToolCall, ToolDef
from app.runtime.engine import AgentRuntime, RunConfig
from app.runtime.tools import ToolRegistry


class _ToolThenAnswerProvider:
    """第一轮请求调用工具；第二轮基于工具结果给出最终文本。"""

    name = "stub"

    def __init__(self) -> None:
        self.turns = 0

    async def generate(self, req: GenRequest) -> GenResult:  # pragma: no cover
        raise NotImplementedError

    async def stream(self, req: GenRequest):
        self.turns += 1
        if self.turns == 1:
            yield StreamEvent(type="text", text="let me check ")
            yield StreamEvent(
                type="done",
                result=GenResult(
                    text="let me check ",
                    tool_calls=[ToolCall(id="t1", name="echo", arguments={"msg": "hi"})],
                    stop_reason="tool_use",
                    usage={"output_tokens": 4},
                ),
            )
        else:
            yield StreamEvent(type="text", text="answer: echoed hi")
            yield StreamEvent(
                type="done",
                result=GenResult(
                    text="answer: echoed hi",
                    tool_calls=[],
                    stop_reason="end_turn",
                    usage={"output_tokens": 3},
                ),
            )


async def test_stream_loop_with_tool():
    reg = ToolRegistry()

    async def echo(args):
        return f"echoed {args['msg']}"

    reg.register(
        ToolDef(name="echo", description="echo", parameters={"type": "object", "properties": {}}),
        echo,
    )

    rt = AgentRuntime(_ToolThenAnswerProvider(), reg)
    from app.providers.base import Message

    events = [e async for e in rt.stream(RunConfig(model="m"), [Message(role="user", content="hi")])]
    types = [e.type for e in events]

    assert "tool_use" in types and "tool_result" in types
    tool_result = next(e for e in events if e.type == "tool_result")
    assert tool_result.content == "echoed hi"

    done = events[-1]
    assert done.type == "done"
    assert done.output == "answer: echoed hi"
    assert done.iterations == 2
    assert done.usage == {"output_tokens": 7}

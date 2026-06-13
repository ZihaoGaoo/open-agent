"""运行时流式事件（归一化，可直接序列化为 SSE）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

RunEventType = Literal["text", "thinking", "tool_use", "tool_result", "done", "error"]


@dataclass
class RunStreamEvent:
    type: RunEventType
    text: str | None = None
    # tool_use / tool_result
    tool_call_id: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    content: str | None = None
    # done
    output: str | None = None
    stop_reason: str | None = None
    iterations: int | None = None
    usage: dict[str, int] = field(default_factory=dict)
    # error
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None and v != {}}

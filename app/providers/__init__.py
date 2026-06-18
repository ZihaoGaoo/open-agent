"""模型 Provider 抽象层。

统一的中立接口屏蔽各家 LLM 差异；默认实现为 Claude(AnthropicProvider)。
运行时(app.runtime)只依赖此处的接口与数据结构。
"""

from app.providers.base import (
    GenRequest,
    GenResult,
    LLMProvider,
    Message,
    StreamEvent,
    ToolCall,
    ToolDef,
)
from app.providers.registry import get_provider, register_provider

__all__ = [
    "GenRequest",
    "GenResult",
    "LLMProvider",
    "Message",
    "StreamEvent",
    "ToolCall",
    "ToolDef",
    "get_provider",
    "register_provider",
]

"""IM 渠道归一化接口（M3 落地具体适配器）。

各平台适配器实现 Channel：把入站事件转为 InboundMessage，把 agent 输出经
send 发回平台。身份映射与会话续接由渠道层与 app.sessions 协作完成。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class InboundMessage:
    """归一化的入站消息。"""

    channel: str  # slack | telegram | discord
    external_user_id: str
    external_chat_id: str
    text: str
    raw: Any = None


@runtime_checkable
class Channel(Protocol):
    name: str

    async def parse_inbound(self, request: Any) -> InboundMessage: ...

    async def send(self, chat_id: str, text: str) -> None: ...

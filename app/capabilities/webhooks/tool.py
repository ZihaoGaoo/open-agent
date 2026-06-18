"""Webhook 工具：把外部 HTTP 接口声明为 agent 可调用的工具。

配置(存于 agent version 的 capabilities["webhook_tools"])示例：
    {
      "name": "get_weather",
      "description": "查询城市天气",
      "parameters": {"type": "object",
                     "properties": {"city": {"type": "string"}},
                     "required": ["city"]},
      "method": "GET",
      "url": "https://api.example.com/weather",
      "headers": {"Authorization": "Bearer ..."},
      "timeout": 30
    }

调用语义：
- GET/DELETE  → 工具参数作为 query string
- 其他方法    → 工具参数作为 JSON body
返回响应正文文本（超长截断）。凭据注入(app.secrets)在后续接入；当前支持静态 headers。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.providers.base import ToolCall, ToolDef
from app.runtime.tools import ToolHandler

_MAX_RESULT_CHARS = 8000


@dataclass
class WebhookToolConfig:
    name: str
    description: str
    url: str
    method: str = "POST"
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebhookToolConfig":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            url=data["url"],
            method=data.get("method", "POST").upper(),
            parameters=data.get("parameters", {"type": "object", "properties": {}}),
            headers=data.get("headers", {}),
            timeout=float(data.get("timeout", 30.0)),
        )


def to_tool_def(cfg: WebhookToolConfig) -> ToolDef:
    return ToolDef(name=cfg.name, description=cfg.description, parameters=cfg.parameters)


def build_handler(
    cfg: WebhookToolConfig, client: httpx.AsyncClient | None = None
) -> ToolHandler:
    """返回一个 ToolHandler；client 可注入（测试时用 MockTransport）。"""

    async def handler(arguments: dict[str, Any]) -> str:
        owns_client = client is None
        http = client or httpx.AsyncClient(timeout=cfg.timeout)
        try:
            if cfg.method in ("GET", "DELETE"):
                resp = await http.request(
                    cfg.method, cfg.url, params=arguments, headers=cfg.headers
                )
            else:
                resp = await http.request(
                    cfg.method, cfg.url, json=arguments, headers=cfg.headers
                )
            text = resp.text
            if len(text) > _MAX_RESULT_CHARS:
                text = text[:_MAX_RESULT_CHARS] + "…[截断]"
            if resp.is_error:
                return f"[http {resp.status_code}] {text}"
            return text
        except httpx.HTTPError as exc:
            return f"[error] webhook 调用失败: {exc}"
        finally:
            if owns_client:
                await http.aclose()

    return handler


def register_webhook_tools(registry, configs: list[dict[str, Any]]) -> None:
    """把 webhook 工具配置列表注册到 ToolRegistry。"""
    for raw in configs:
        cfg = WebhookToolConfig.from_dict(raw)
        registry.register(to_tool_def(cfg), build_handler(cfg))


def execute_once(cfg: WebhookToolConfig, call: ToolCall) -> Any:  # pragma: no cover
    """便于交互调试的同步包装（非生产路径）。"""
    raise NotImplementedError

"""Webhook 工具单测：用 httpx MockTransport 验证 HTTP → 工具结果，无需真实网络。"""

from __future__ import annotations

import httpx

from app.capabilities.webhooks.tool import WebhookToolConfig, build_handler, to_tool_def


def _mock_client() -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/weather":
            return httpx.Response(200, json={"city": "SF", "temp": 18})
        if request.url.path == "/fail":
            return httpx.Response(500, text="boom")
        return httpx.Response(404, text="nope")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_tool_def_from_config():
    cfg = WebhookToolConfig(
        name="get_weather",
        description="天气",
        url="https://x/weather",
        parameters={"type": "object", "properties": {"city": {"type": "string"}}},
    )
    spec = to_tool_def(cfg)
    assert spec.name == "get_weather"
    assert spec.parameters["properties"]["city"]["type"] == "string"


async def test_post_webhook_success():
    cfg = WebhookToolConfig(name="w", description="", url="https://x/weather", method="POST")
    async with _mock_client() as client:
        handler = build_handler(cfg, client=client)
        result = await handler({"city": "SF"})
    assert '"temp":18' in result.replace(" ", "")


async def test_get_webhook_uses_query():
    cfg = WebhookToolConfig(name="w", description="", url="https://x/weather", method="GET")
    async with _mock_client() as client:
        handler = build_handler(cfg, client=client)
        result = await handler({"city": "SF"})
    assert '"city":"SF"' in result.replace(" ", "")


async def test_webhook_http_error_surfaced():
    cfg = WebhookToolConfig(name="w", description="", url="https://x/fail", method="POST")
    async with _mock_client() as client:
        handler = build_handler(cfg, client=client)
        result = await handler({})
    assert result.startswith("[http 500]")

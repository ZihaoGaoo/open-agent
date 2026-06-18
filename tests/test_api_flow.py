"""端到端流程测试（需要可用的 PostgreSQL，通过 DATABASE_URL 提供）。

覆盖：API Key 鉴权 → 创建 agent → 同步 invoke（用 stub provider，不打真实 API）。
"""

from __future__ import annotations

import os

import httpx
import pytest

DB = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB, reason="需要 DATABASE_URL 指向可用的 PostgreSQL")

from app.auth.security import generate_api_key  # noqa: E402
from app.db.models import ApiKey, Org  # noqa: E402
from app.db.session import get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.base import GenResult, StreamEvent  # noqa: E402
from app.providers.registry import register_provider  # noqa: E402


class _StubProvider:
    name = "stub"

    async def generate(self, req) -> GenResult:
        return GenResult(
            text=f"echo:{req.messages[-1].content}|sys={req.system}",
            tool_calls=[],
            stop_reason="end_turn",
            usage={"output_tokens": 3},
        )

    async def stream(self, req):
        text = f"echo:{req.messages[-1].content}|sys={req.system}"
        yield StreamEvent(type="text", text=text)
        yield StreamEvent(
            type="done",
            result=GenResult(
                text=text, tool_calls=[], stop_reason="end_turn", usage={"output_tokens": 3}
            ),
        )


register_provider("stub", lambda: _StubProvider())


async def _bootstrap_key() -> str:
    sm = get_sessionmaker()
    async with sm() as session:
        org = Org(name="pytest-org")
        session.add(org)
        await session.flush()
        plaintext, prefix, hashed = generate_api_key()
        session.add(ApiKey(org_id=org.id, name="t", prefix=prefix, hashed_key=hashed))
        await session.commit()
        return plaintext


async def test_auth_crud_invoke_flow():
    key = await _bootstrap_key()
    headers = {"X-API-Key": key}
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # 无凭据 → 401
        assert (await c.get("/v1/agents")).status_code == 401

        # 创建 agent（带变量化 system prompt）
        r = await c.post(
            "/v1/agents",
            headers=headers,
            json={
                "name": "a1",
                "model": "claude-opus-4-8",
                "system_prompt": "You are $role.",
            },
        )
        assert r.status_code == 201, r.text
        agent_id = r.json()["id"]

        # 列表可见
        r = await c.get("/v1/agents", headers=headers)
        assert r.status_code == 200 and any(a["id"] == agent_id for a in r.json())

        # 同步 invoke（stub provider，变量插值生效）
        r = await c.post(
            f"/v1/agents/{agent_id}/invoke",
            headers=headers,
            json={"input": "hi", "provider": "stub", "variables": {"role": "helper"}},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["output"] == "echo:hi|sys=You are helper."
        assert body["stop_reason"] == "end_turn"

        # 流式 invoke（SSE）
        async with c.stream(
            "POST",
            f"/v1/agents/{agent_id}/stream",
            headers=headers,
            json={"input": "hi", "provider": "stub", "variables": {"role": "helper"}},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body_text = ""
            async for line in resp.aiter_lines():
                body_text += line + "\n"
        assert "event: text" in body_text
        assert "event: done" in body_text
        assert "echo:hi|sys=You are helper." in body_text

        # 更新配置 → 产生新版本(v2)
        r = await c.patch(
            f"/v1/agents/{agent_id}",
            headers=headers,
            json={"system_prompt": "v2 prompt", "params": {"max_tokens": 2048}},
        )
        assert r.status_code == 200, r.text
        assert r.json()["current_version"] == 2

        r = await c.get(f"/v1/agents/{agent_id}/version", headers=headers)
        assert r.status_code == 200
        assert r.json()["version"] == 2
        assert r.json()["system_prompt"] == "v2 prompt"

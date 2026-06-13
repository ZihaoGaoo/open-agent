"""Agent 服务：加载配置 → 组装运行时 → 执行同步调用。

M1：system_prompt 直接取自 AgentVersion（+ 变量插值），无外部工具。
M2 起，能力绑定(MCP/Skill/Webhook)在此解析为 ToolExecutor 注入运行时。
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import InvokeRequest, InvokeResponse
from app.capabilities.prompts import render_prompt
from app.config import get_settings
from app.db.models import Agent, AgentVersion
from app.providers import Message, get_provider
from app.runtime import AgentRuntime
from app.runtime.engine import RunConfig


async def _load_agent_with_version(
    session: AsyncSession, org_id: uuid.UUID, agent_id: uuid.UUID
) -> tuple[Agent, AgentVersion]:
    agent = (
        await session.execute(
            select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        )
    ).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent 不存在")

    version = (
        await session.execute(
            select(AgentVersion).where(
                AgentVersion.agent_id == agent.id,
                AgentVersion.version == agent.current_version,
            )
        )
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agent 版本缺失")
    return agent, version


async def invoke_agent(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    req: InvokeRequest,
) -> InvokeResponse:
    settings = get_settings()
    _, version = await _load_agent_with_version(session, org_id, agent_id)

    system = (
        render_prompt(version.system_prompt, req.variables)
        if version.system_prompt
        else None
    )
    provider = get_provider(req.provider)
    runtime = AgentRuntime(provider, tools=None)  # M1：暂无工具

    config = RunConfig(
        model=version.model or settings.default_model,
        system=system,
        max_tokens=req.max_tokens or int(version.params.get("max_tokens", 16000)),
        params={k: v for k, v in version.params.items() if k != "max_tokens"},
    )
    output = await runtime.run(config, [Message(role="user", content=req.input)])
    return InvokeResponse(
        output=output.text,
        iterations=output.iterations,
        stop_reason=output.stop_reason,
        usage=output.usage,
    )

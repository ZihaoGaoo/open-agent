"""Agent 服务：加载配置 → 组装运行时(含工具) → 同步/流式执行。

M1 起支持单 agent 完整 loop：配置/版本、提示词插值、工具调用、流式与非流式调用。
当前工具来源为 Webhook（capabilities["webhook_tools"]）；MCP/Skill 在后续接入同一 ToolRegistry。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import InvokeRequest, InvokeResponse
from app.capabilities.prompts import render_prompt
from app.capabilities.webhooks.tool import register_webhook_tools
from app.config import get_settings
from app.db.models import Agent, AgentVersion
from app.providers import Message, get_provider
from app.runtime import AgentRuntime, ToolRegistry
from app.runtime.engine import RunConfig
from app.runtime.events import RunStreamEvent


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


def _build_tool_executor(version: AgentVersion) -> ToolRegistry | None:
    """从版本能力绑定构建 ToolExecutor（当前支持 webhook 工具）。"""
    webhook_cfgs = (version.capabilities or {}).get("webhook_tools") or []
    if not webhook_cfgs:
        return None
    registry = ToolRegistry()
    register_webhook_tools(registry, webhook_cfgs)
    return registry


def _build_runtime_and_config(
    version: AgentVersion, req: InvokeRequest
) -> tuple[AgentRuntime, RunConfig]:
    settings = get_settings()
    system = (
        render_prompt(version.system_prompt, req.variables)
        if version.system_prompt
        else None
    )
    provider = get_provider(req.provider)
    tools = _build_tool_executor(version)
    runtime = AgentRuntime(provider, tools=tools)
    config = RunConfig(
        model=version.model or settings.default_model,
        system=system,
        max_tokens=req.max_tokens or int((version.params or {}).get("max_tokens", 16000)),
        params={k: v for k, v in (version.params or {}).items() if k != "max_tokens"},
    )
    return runtime, config


async def prepare_run(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    req: InvokeRequest,
) -> tuple[AgentRuntime, RunConfig]:
    """在请求(DB会话)作用域内完成所有 DB 读取与运行时组装。

    流式调用必须在返回 SSE 响应前调用此函数——之后请求作用域的 DB 会话会关闭，
    生成器阶段不能再访问 DB。
    """
    _, version = await _load_agent_with_version(session, org_id, agent_id)
    return _build_runtime_and_config(version, req)


async def invoke_agent(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    req: InvokeRequest,
) -> InvokeResponse:
    runtime, config = await prepare_run(session, org_id, agent_id, req)
    output = await runtime.run(config, [Message(role="user", content=req.input)])
    return InvokeResponse(
        output=output.text,
        iterations=output.iterations,
        stop_reason=output.stop_reason,
        usage=output.usage,
    )


def stream_run(
    runtime: AgentRuntime, config: RunConfig, user_input: str
) -> AsyncIterator[RunStreamEvent]:
    """纯流式生成器：不触碰 DB（runtime/config 须由 prepare_run 预先构建）。"""
    return runtime.stream(config, [Message(role="user", content=user_input)])


# ---- 配置 / 版本 ----
def _next_version_snapshot(prev: AgentVersion, patch: dict[str, Any]) -> dict[str, Any]:
    """以上一版本为基线，应用补丁，产出新版本字段。"""
    return {
        "model": patch.get("model") or prev.model,
        "system_prompt": patch.get("system_prompt", prev.system_prompt),
        "params": patch.get("params") if patch.get("params") is not None else prev.params,
        "capabilities": (
            patch.get("capabilities")
            if patch.get("capabilities") is not None
            else prev.capabilities
        ),
    }


async def update_agent_version(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    patch: dict[str, Any],
) -> Agent:
    """创建新版本并把 current_version 指向它；可同时更新 agent 元信息。"""
    agent, prev = await _load_agent_with_version(session, org_id, agent_id)

    if patch.get("name") is not None:
        agent.name = patch["name"]
    if patch.get("description") is not None:
        agent.description = patch["description"]

    snapshot = _next_version_snapshot(prev, patch)
    new_version = agent.current_version + 1
    session.add(
        AgentVersion(
            agent_id=agent.id,
            version=new_version,
            model=snapshot["model"],
            system_prompt=snapshot["system_prompt"],
            params=snapshot["params"],
            capabilities=snapshot["capabilities"],
        )
    )
    agent.current_version = new_version
    await session.commit()
    await session.refresh(agent)
    return agent

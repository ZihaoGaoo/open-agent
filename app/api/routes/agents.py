"""Agent CRUD + 同步调用。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.service import invoke_agent
from app.api.schemas import (
    AgentCreate,
    AgentOut,
    AgentVersionOut,
    InvokeRequest,
    InvokeResponse,
)
from app.auth.deps import AuthContext, get_auth_context
from app.config import get_settings
from app.db.models import Agent, AgentVersion
from app.db.session import get_db_session

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> Agent:
    settings = get_settings()
    agent = Agent(
        org_id=auth.org_id,
        name=payload.name,
        description=payload.description,
        current_version=1,
    )
    session.add(agent)
    await session.flush()  # 拿到 agent.id

    version = AgentVersion(
        agent_id=agent.id,
        version=1,
        model=payload.model or settings.default_model,
        system_prompt=payload.system_prompt,
        params=payload.params,
        capabilities=payload.capabilities,
    )
    session.add(version)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.get("", response_model=list[AgentOut])
async def list_agents(
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[Agent]:
    result = await session.execute(select(Agent).where(Agent.org_id == auth.org_id))
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> Agent:
    agent = await _get_agent_or_404(session, auth.org_id, agent_id)
    return agent


@router.get("/{agent_id}/version", response_model=AgentVersionOut)
async def get_current_version(
    agent_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> AgentVersion:
    agent = await _get_agent_or_404(session, auth.org_id, agent_id)
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
    return version


@router.post("/{agent_id}/invoke", response_model=InvokeResponse)
async def invoke(
    agent_id: uuid.UUID,
    payload: InvokeRequest,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> InvokeResponse:
    return await invoke_agent(session, auth.org_id, agent_id, payload)


async def _get_agent_or_404(
    session: AsyncSession, org_id: uuid.UUID, agent_id: uuid.UUID
) -> Agent:
    agent = (
        await session.execute(
            select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        )
    ).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent 不存在")
    return agent

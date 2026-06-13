"""提示词模板 CRUD。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PromptCreate, PromptOut
from app.auth.deps import AuthContext, get_auth_context
from app.db.models import Prompt
from app.db.session import get_db_session

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptOut, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreate,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> Prompt:
    prompt = Prompt(
        org_id=auth.org_id,
        name=payload.name,
        template=payload.template,
        variables=payload.variables,
    )
    session.add(prompt)
    await session.commit()
    await session.refresh(prompt)
    return prompt


@router.get("", response_model=list[PromptOut])
async def list_prompts(
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[Prompt]:
    result = await session.execute(select(Prompt).where(Prompt.org_id == auth.org_id))
    return list(result.scalars().all())


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(
    prompt_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> Prompt:
    prompt = (
        await session.execute(
            select(Prompt).where(Prompt.id == prompt_id, Prompt.org_id == auth.org_id)
        )
    ).scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prompt 不存在")
    return prompt

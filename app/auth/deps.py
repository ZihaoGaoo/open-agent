"""FastAPI 鉴权依赖：解析 API Key，返回当前调用上下文（org 维度）。

支持两种头：
- Authorization: Bearer oa_xxx
- X-API-Key: oa_xxx
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_api_key
from app.db.models import ApiKey
from app.db.session import get_db_session


@dataclass
class AuthContext:
    org_id: uuid.UUID
    api_key_id: uuid.UUID


def _extract_key(authorization: str | None, x_api_key: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def get_auth_context(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_db_session),
) -> AuthContext:
    raw = _extract_key(authorization, x_api_key)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 API Key"
        )
    hashed = hash_api_key(raw)
    result = await session.execute(
        select(ApiKey).where(ApiKey.hashed_key == hashed, ApiKey.revoked.is_(False))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 API Key"
        )
    return AuthContext(org_id=api_key.org_id, api_key_id=api_key.id)

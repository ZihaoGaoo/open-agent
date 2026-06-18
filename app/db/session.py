"""异步引擎与会话工厂（懒加载，首次使用时建立连接池）。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：提供一个事务性会话。"""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session

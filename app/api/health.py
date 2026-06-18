"""健康检查与根信息。"""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/")
async def root() -> dict:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": __version__,
        "role": settings.role,
        "environment": settings.environment,
    }

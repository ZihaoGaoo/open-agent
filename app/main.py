"""FastAPI 应用工厂。

单镜像通过 ROLE 环境变量切换进程：
- ROLE=web    → 本模块的 ``app`` 由 gunicorn/uvicorn 启动
- ROLE=worker → 由 ``python -m app.workers`` 启动（不经过本模块）
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.config import get_settings
from app.observability.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    # 资源初始化（DB 引擎按需懒加载，连接池在首次使用时建立）。
    yield
    # 资源清理（关闭引擎等）将在后续里程碑接入。


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_router)
    return app


app = create_app()

"""聚合所有路由。

调用 API 三形态（详见 docs/ARCHITECTURE.md §4.1）：
- 同步:  POST /v1/agents/{id}/invoke
- 异步:  POST /v1/agents/{id}/runs  →  GET /v1/runs/{run_id}
- 流式:  GET  /v1/runs/{run_id}/stream  (SSE)

各业务路由在对应里程碑填充，这里先建立挂载点。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import health
from app.api.routes import agents, prompts

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(agents.router, prefix="/v1")
api_router.include_router(prompts.router, prefix="/v1")

# 后续里程碑挂载点：
# from app.api.routes import runs, im_webhooks
# api_router.include_router(runs.router, prefix="/v1", tags=["runs"])   # M3 异步/流式
# api_router.include_router(im_webhooks.router, prefix="/im", tags=["im"])  # M3 IM

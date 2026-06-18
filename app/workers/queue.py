"""Postgres 原生任务队列接口（M3 实现）。

设计：runs 表即队列；worker 用 ``SELECT ... FOR UPDATE SKIP LOCKED`` 领取待执行
run，执行 agentic loop，更新状态并写 run_events，完成后触发回调 webhook。
多实例水平扩展时可换/叠加 Redis。
"""

from __future__ import annotations


async def claim_next_run() -> None:
    """领取下一个待执行 run（占位，M3 实现）。"""
    raise NotImplementedError("PG 任务队列在 M3 实现")

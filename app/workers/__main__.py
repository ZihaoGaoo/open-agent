"""Worker 进程入口：`python -m app.workers`（ROLE=worker）。

M1 为占位循环：仅初始化日志并保持存活，便于验证容器编排。
M3 接入真正的 PG 队列消费（见 app.workers.queue）。
"""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.observability.logging import configure_logging, get_logger


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("worker")
    log.info("worker.start", role=settings.role, note="占位循环；PG 队列消费在 M3 接入")
    try:
        while True:
            # M3: claim_next_run() → run agentic loop → 写回结果 → 触发回调
            await asyncio.sleep(5)
    except (KeyboardInterrupt, asyncio.CancelledError):  # pragma: no cover
        log.info("worker.stop")


if __name__ == "__main__":
    asyncio.run(main())

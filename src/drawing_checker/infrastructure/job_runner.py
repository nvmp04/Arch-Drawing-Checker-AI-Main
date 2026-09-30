"""Chạy việc phân tích nền, in-process (PoC). Qua lớp trừu tượng để sau đổi sang hàng đợi thật."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class JobRunner:
    """Mỗi job là một asyncio.Task trên event loop của server."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def submit(self, job_id: str, work: Callable[[], Awaitable[None]]) -> None:
        task = asyncio.get_running_loop().create_task(work(), name=f"analysis-{job_id}")
        self._tasks[job_id] = task  # giữ tham chiếu để task không bị GC
        task.add_done_callback(lambda t: self._on_done(job_id, t))

    def cancel(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def _on_done(self, job_id: str, task: asyncio.Task[None]) -> None:
        self._tasks.pop(job_id, None)
        if not task.cancelled() and task.exception() is not None:
            logger.error("Job %s lỗi ngoài dự kiến", job_id, exc_info=task.exception())

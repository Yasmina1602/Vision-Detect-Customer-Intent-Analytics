"""Yengil rejalashtiruvchi (Redis'siz). Production'da alohida jarayon: `python -m app.workers.run`."""
import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.workers import jobs

log = logging.getLogger("app.worker")

SCHEDULE: list[tuple[str, Callable[[], Awaitable], int]] = [
    ("detect_abandoned", jobs.detect_abandoned, 5 * 60),
    ("cluster_demand", jobs.cluster_demand, 15 * 60),
    ("build_profiles", jobs.build_profiles, 15 * 60),
    ("aggregate_daily", jobs.aggregate_daily, 30 * 60),
    ("sync_catalogs", jobs.sync_catalogs, 60 * 60),
    ("retention", jobs.retention, 24 * 3600),
]


async def _loop(name: str, fn: Callable[[], Awaitable], interval: int, initial_delay: int) -> None:
    await asyncio.sleep(initial_delay)
    while True:
        try:
            await fn()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Job %s xato bilan tugadi", name)
        await asyncio.sleep(interval)


def start(loop_delay: int = 10) -> list[asyncio.Task]:
    tasks = []
    for i, (name, fn, interval) in enumerate(SCHEDULE):
        tasks.append(asyncio.create_task(_loop(name, fn, interval, loop_delay + i * 5), name=f"job:{name}"))
    log.info("Worker: %s ta job rejalashtirildi", len(tasks))
    return tasks

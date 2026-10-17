"""Alohida worker jarayoni: python -m app.workers.run"""
import asyncio

from app.core.config import settings
from app.core.logging import setup_logging
from app.workers import scheduler


async def main() -> None:
    setup_logging(settings.is_dev)
    tasks = scheduler.start(loop_delay=1)
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

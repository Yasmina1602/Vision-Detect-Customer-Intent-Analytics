"""Kesh va rate limit. Redis bo'lsa Redis, bo'lmasa jarayon ichidagi xotira.

Graceful degradation (17-bo'lim, #21): Redis yiqilsa, kesh/limit o'tkazib yuboriladi, qidiruv ishlaydi.
"""
import json
import logging
import time
from collections import OrderedDict
from typing import Any

from app.core.config import settings

log = logging.getLogger("app.cache")


class _MemoryStore:
    def __init__(self, max_items: int = 5000):
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max = max_items

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if not item:
            return None
        exp, value = item
        if exp < time.time():
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._data[key] = (time.time() + ttl, value)
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)

    def incr(self, key: str, ttl: int) -> int:
        current = self.get(key) or 0
        current += 1
        exp = self._data[key][0] if key in self._data else time.time() + ttl
        self._data[key] = (exp, current)
        return current


_memory = _MemoryStore()
_redis = None

if settings.REDIS_URL:
    try:
        import redis.asyncio as redis_lib  # type: ignore

        _redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:  # pragma: no cover
        log.warning("Redis ulanmadi — xotiradagi keshga o'tildi")
        _redis = None


async def cache_get(key: str) -> Any | None:
    if _redis is not None:
        try:
            raw = await _redis.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            log.warning("Redis get xatosi, kesh o'tkazib yuborildi")
            return None
    return _memory.get(key)


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    if _redis is not None:
        try:
            await _redis.set(key, json.dumps(value, default=str), ex=ttl)
            return
        except Exception:
            log.warning("Redis set xatosi")
            return
    _memory.set(key, value, ttl)


async def hit_rate_limit(key: str, limit: int, window_s: int = 60) -> bool:
    """True qaytarsa — limit oshib ketgan."""
    bucket = f"rl:{key}:{int(time.time() // window_s)}"
    if _redis is not None:
        try:
            n = await _redis.incr(bucket)
            if n == 1:
                await _redis.expire(bucket, window_s)
            return n > limit
        except Exception:
            return False
    return _memory.incr(bucket, window_s) > limit


def backend_name() -> str:
    return "redis" if _redis is not None else "memory"

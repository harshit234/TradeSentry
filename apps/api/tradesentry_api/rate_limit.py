from __future__ import annotations

from collections import defaultdict
from time import time
from typing import Protocol

from redis.asyncio import Redis


class RateLimiter(Protocol):
    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool: ...


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self.windows: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        window = int(time()) // window_seconds
        stored_window, count = self.windows[key]
        if stored_window != window:
            stored_window, count = window, 0
        count += 1
        self.windows[key] = stored_window, count
        return count <= limit


class RedisRateLimiter:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        window = int(time()) // window_seconds
        redis_key = f"rate:{key}:{window}"
        count = int(await self.client.incr(redis_key))
        if count == 1:
            await self.client.expire(redis_key, window_seconds + 1)
        return count <= limit

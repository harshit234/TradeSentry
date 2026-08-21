from typing import cast

from redis.asyncio import Redis


class RedisCache:
    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(url, decode_responses=True)

    async def check(self) -> bool:
        return bool(await self.client.ping())

    async def set(self, key: str, value: str, expires: int = 300) -> None:
        await self.client.set(key, value, ex=expires)

    async def get(self, key: str) -> str | None:
        return cast(str | None, await self.client.get(key))

    async def close(self) -> None:
        await self.client.aclose()


class InMemoryRedis:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    async def check(self) -> bool:
        return True

    async def set(self, key: str, value: str, expires: int = 300) -> None:
        del expires
        self._values[key] = value

    async def get(self, key: str) -> str | None:
        return self._values.get(key)

    async def close(self) -> None:
        return None

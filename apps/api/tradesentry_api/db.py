from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True)

    async def check(self) -> bool:
        async with self.engine.connect() as connection:
            return bool(await connection.scalar(text("SELECT 1")))

    async def close(self) -> None:
        await self.engine.dispose()


class InMemoryDatabase:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    async def check(self) -> bool:
        return True

    async def write(self, key: str, value: str) -> None:
        self._values[key] = value

    async def read(self, key: str) -> str | None:
        return self._values.get(key)

    async def close(self) -> None:
        return None


async def database_lifespan(database: Database) -> AsyncIterator[Database]:
    try:
        yield database
    finally:
        await database.close()

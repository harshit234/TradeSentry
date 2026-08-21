import pytest
from tradesentry_api.db import InMemoryDatabase
from tradesentry_api.redis_client import InMemoryRedis
from tradesentry_api.s3 import InMemoryStorage


@pytest.mark.asyncio
async def test_database_write_and_read() -> None:
    db = InMemoryDatabase()
    await db.write("case", "created")
    assert await db.read("case") == "created"


@pytest.mark.asyncio
async def test_redis_set_and_get() -> None:
    cache = InMemoryRedis()
    await cache.set("health", "ok")
    assert await cache.get("health") == "ok"


@pytest.mark.asyncio
async def test_storage_upload_download_presign_delete() -> None:
    storage = InMemoryStorage()
    key = await storage.upload(b"synthetic", "cases/test/document.pdf", {"case_id": "test"})
    assert await storage.download(key) == b"synthetic"
    assert await storage.presigned_url(key, expires=3600) == f"memory://{key}?expires=900"
    await storage.delete(key)
    with pytest.raises(KeyError):
        await storage.download(key)

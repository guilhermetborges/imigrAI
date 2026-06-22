import time
from functools import lru_cache

from app.core.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_redis_client() -> "InMemoryRedis":
    return InMemoryRedis()


class InMemoryRedis:
    def __init__(self) -> None:
        self._store: dict[str, tuple[int, float | None]] = {}

    async def ping(self) -> bool:
        return True

    async def incr(self, key: str) -> int:
        self._delete_if_expired(key)
        value, expires_at = self._store.get(key, (0, None))
        value += 1
        self._store[key] = (value, expires_at)
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        self._delete_if_expired(key)
        if key not in self._store:
            return False
        value, _ = self._store[key]
        self._store[key] = (value, time.time() + seconds)
        return True

    def _delete_if_expired(self, key: str) -> None:
        item = self._store.get(key)
        if item is None:
            return
        _, expires_at = item
        if expires_at is not None and time.time() >= expires_at:
            self._store.pop(key, None)


async def ping_redis() -> bool:
    client = get_redis_client()
    try:
        pong = await client.ping()
        return bool(pong)
    except Exception:
        return False

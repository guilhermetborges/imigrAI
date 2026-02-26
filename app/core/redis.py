from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


async def ping_redis() -> bool:
    client = get_redis_client()
    try:
        pong = await client.ping()
        return bool(pong)
    except Exception:
        return False

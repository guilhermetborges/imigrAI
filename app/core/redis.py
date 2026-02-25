import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()


async def ping_redis() -> bool:
    client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        pong = await client.ping()
        return bool(pong)
    finally:
        await client.aclose()

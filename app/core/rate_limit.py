from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.core.security import get_optional_current_user
from apps.accounts.models import User

logger = logging.getLogger(__name__)
settings = get_settings()
_fallback_lock = threading.Lock()
_fallback_store: dict[str, tuple[int, float]] = {}


def rate_limit(
    *,
    scope: str,
    limit: int,
    window_seconds: int,
    identity: str = "user_or_ip",
) -> Callable:
    async def dependency(
        request: Request,
        current_user: User | None = Depends(get_optional_current_user),
    ) -> None:
        if limit <= 0 or window_seconds <= 0:
            return

        identity_key = _identity_key(
            request=request,
            current_user=current_user if identity == "user_or_ip" else None,
        )
        route = _route_key(request)
        redis_key = f"rate_limit:{scope}:{route}:{identity_key}"

        allowed = await _allow_request(
            redis_key=redis_key, limit=limit, window_seconds=window_seconds
        )
        if allowed:
            return

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for scope='{scope}'. Try again later.",
        )

    return dependency


def _route_key(request: Request) -> str:
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return str(route.path)
    return request.url.path


def _identity_key(*, request: Request, current_user: User | None) -> str:
    if current_user is not None:
        return f"user:{current_user.id}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


async def _allow_request(*, redis_key: str, limit: int, window_seconds: int) -> bool:
    try:
        client = get_redis_client()
        counter = int(await client.incr(redis_key))
        if counter == 1:
            await client.expire(redis_key, window_seconds)
        return counter <= limit
    except Exception as exc:
        logger.warning(
            "rate_limiter_backend_error", extra={"error": str(exc), "redis_key": redis_key}
        )
        if settings.rate_limit_fail_open:
            return _allow_fallback(redis_key=redis_key, limit=limit, window_seconds=window_seconds)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter backend unavailable",
        ) from exc


def _allow_fallback(*, redis_key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    with _fallback_lock:
        current_count, expires_at = _fallback_store.get(redis_key, (0, now + window_seconds))
        if now >= expires_at:
            current_count = 0
            expires_at = now + window_seconds

        current_count += 1
        _fallback_store[redis_key] = (current_count, expires_at)
        return current_count <= limit

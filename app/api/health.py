from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import ping_redis
from app.db import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", status_code=status.HTTP_200_OK)
async def health_live() -> dict[str, str]:
    return {
        "status": "live",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
        redis_ok = await ping_redis()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"dependency check failed: {exc}",
        ) from exc

    if not redis_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="redis is unavailable",
        )

    return {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
    }

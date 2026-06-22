from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import refresh_operational_metrics, render_metrics_payload
from app.core.redis import ping_redis
from app.db import AsyncSessionLocal, get_db

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
        memory_store_ok = await ping_redis()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"dependency check failed: {exc}",
        ) from exc

    if not memory_store_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="memory store is unavailable",
        )

    return {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    try:
        await refresh_operational_metrics(AsyncSessionLocal)
    except Exception:
        # Mantem endpoint de metricas disponivel mesmo com dependencia degradada.
        pass
    payload, content_type = render_metrics_payload()
    return Response(content=payload, media_type=content_type)

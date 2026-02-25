from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.permissions import require_feature
from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.roadmaps.schemas import (
    RoadmapCreate,
    RoadmapDetailRead,
    RoadmapQueuedRead,
    RoadmapStatusRead,
)
from apps.roadmaps.services import RoadmapsService

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])
settings = get_settings()


@router.post("", response_model=RoadmapQueuedRead, status_code=status.HTTP_202_ACCEPTED)
async def create_roadmap(
    payload: RoadmapCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: str = Depends(require_feature(settings.pro_roadmap_feature_key)),
    x_trace_id: str | None = Header(default=None),
) -> RoadmapQueuedRead:
    service = RoadmapsService(db)
    trace_id = x_trace_id or getattr(request.state, "trace_id", None)
    return await service.create_roadmap(
        user_id=current_user.id,
        payload=payload,
        trace_id=trace_id,
    )


@router.get("/{roadmap_id}/status", response_model=RoadmapStatusRead)
async def get_roadmap_status(
    roadmap_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RoadmapStatusRead:
    service = RoadmapsService(db)
    return await service.get_roadmap_status(roadmap_id)


@router.get("/{roadmap_id}", response_model=RoadmapDetailRead)
async def get_roadmap_detail(
    roadmap_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RoadmapDetailRead:
    service = RoadmapsService(db)
    return await service.get_roadmap_detail(roadmap_id)

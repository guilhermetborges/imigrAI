from fastapi import APIRouter

from app.api.v1.assessments import router as assessments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.entitlements import router as entitlements_router
from app.api.v1.immigration_rules import router as immigration_rules_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.roadmaps import router as roadmaps_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(billing_router)
router.include_router(entitlements_router)
router.include_router(immigration_rules_router)
router.include_router(assessments_router)
router.include_router(roadmaps_router)
router.include_router(jobs_router)

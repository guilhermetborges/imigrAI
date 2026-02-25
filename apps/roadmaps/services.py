from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from apps.assessments.models import AssessmentStatus
from apps.billing.services import BillingService
from apps.common.models import JobType
from apps.common.repositories import JobsRepository
from apps.roadmaps.llm import build_llm_provider
from apps.roadmaps.models import Roadmap, RoadmapStatus
from apps.roadmaps.repositories import RoadmapsRepository
from apps.roadmaps.schemas import (
    RoadmapContract,
    RoadmapCreate,
    RoadmapDetailRead,
    RoadmapQueuedRead,
    RoadmapRead,
    RoadmapStatusRead,
    RoadmapStepRead,
)


class RoadmapsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RoadmapsRepository(db)
        self.jobs_repo = JobsRepository(db)
        self.billing_service = BillingService(db)
        self.settings = get_settings()

    async def create_roadmap(
        self,
        *,
        user_id: UUID,
        payload: RoadmapCreate,
        trace_id: str | None,
    ) -> RoadmapQueuedRead:
        if payload.idempotency_key:
            existing_job = await self.jobs_repo.get_job_by_key(
                job_type=JobType.roadmap_job,
                idempotency_key=payload.idempotency_key,
            )
            if existing_job and existing_job.roadmap_id:
                existing_roadmap = await self.repo.get_roadmap(existing_job.roadmap_id)
                if existing_roadmap:
                    if existing_roadmap.user_id != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Idempotency key already used by another user",
                        )
                    return RoadmapQueuedRead(
                        roadmap_id=existing_roadmap.id,
                        status=existing_roadmap.status,
                        roadmap_schema_version=existing_roadmap.roadmap_schema_version,
                        job_id=existing_job.id,
                    )

        assessment = await self.repo.get_assessment_for_roadmap(
            assessment_id=payload.assessment_id,
            user_id=user_id,
        )
        if assessment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
            )

        if assessment.status != AssessmentStatus.completed or assessment.result is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Assessment must be completed before roadmap generation "
                    f"(current={assessment.status.value})"
                ),
            )

        await self.billing_service.require_entitlement(
            user_id=user_id,
            feature_key=self.settings.pro_roadmap_feature_key,
        )

        roadmap = await self.repo.create_roadmap(
            user_id=user_id,
            assessment_result_id=assessment.result.id,
            roadmap_schema_version=self.settings.roadmap_schema_version,
            trace_id=trace_id,
        )

        idempotency_key = payload.idempotency_key or f"roadmap:{roadmap.id}"
        job = await self.jobs_repo.get_or_create_job(
            job_type=JobType.roadmap_job,
            idempotency_key=idempotency_key,
            roadmap_id=roadmap.id,
            trace_id=trace_id,
        )

        from apps.roadmaps.tasks import generate_roadmap_task

        generate_roadmap_task.apply_async(
            kwargs={
                "roadmap_id": str(roadmap.id),
                "job_id": str(job.id),
                "trace_id": trace_id,
            },
            queue="roadmap_queue",
            priority=0,
        )

        return RoadmapQueuedRead(
            roadmap_id=roadmap.id,
            status=roadmap.status,
            roadmap_schema_version=roadmap.roadmap_schema_version,
            job_id=job.id,
        )

    async def process_roadmap(self, roadmap_id: UUID) -> None:
        roadmap = await self.repo.get_roadmap_for_generation(roadmap_id)
        if roadmap is None:
            raise ValueError("Roadmap not found")

        if roadmap.status == RoadmapStatus.completed and roadmap.steps:
            return

        await self.repo.mark_running(roadmap)

        provider = build_llm_provider(self.settings)
        payload = self._build_provider_payload(roadmap)
        contract = provider.generate_roadmap(payload)
        self._validate_contract(contract)

        await self.repo.apply_generated_contract(
            roadmap=roadmap,
            contract=contract,
            provider_name=provider.provider_name,
            provider_model=provider.model_name,
        )

    async def mark_roadmap_failed(self, roadmap_id: UUID, error_message: str) -> None:
        roadmap = await self.repo.get_roadmap(roadmap_id)
        if roadmap is None:
            return
        await self.repo.mark_failed(roadmap, error_message=error_message)

    async def get_roadmap_status(self, roadmap_id: UUID) -> RoadmapStatusRead:
        roadmap = await self.repo.get_roadmap(roadmap_id)
        if roadmap is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")

        job = await self.jobs_repo.get_latest_job_for_roadmap(roadmap_id)
        return RoadmapStatusRead(
            roadmap_id=roadmap.id,
            status=roadmap.status,
            completed_at=roadmap.completed_at,
            error=roadmap.generation_error,
            job_id=job.id if job else None,
        )

    async def get_roadmap_detail(self, roadmap_id: UUID) -> RoadmapDetailRead:
        roadmap = await self.repo.get_roadmap_detail(roadmap_id)
        if roadmap is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")
        return RoadmapDetailRead(
            roadmap=RoadmapRead.model_validate(roadmap),
            steps=[RoadmapStepRead.model_validate(step) for step in roadmap.steps],
        )

    def _build_provider_payload(self, roadmap: Roadmap) -> dict:
        result = roadmap.assessment_result
        assessment = result.assessment
        if assessment is None or assessment.profile_snapshot is None:
            raise ValueError("Roadmap is missing assessment snapshot context")

        profile_json = assessment.profile_snapshot.profile_json
        gaps_criticos: list[str] = []
        fatores_positivos: list[str] = []
        breakdown: list[dict] = []
        for item in sorted(result.items, key=lambda entry: (entry.created_at, str(entry.id))):
            payload = item.audit_payload_json or {}
            is_blocking = bool(payload.get("is_blocking", False))
            score_delta = Decimal(str(item.score_delta))

            breakdown.append(
                {
                    "rule_group_id": str(item.rule_group_id) if item.rule_group_id else None,
                    "rule_outcome_id": str(item.rule_outcome_id) if item.rule_outcome_id else None,
                    "applied": item.applied,
                    "score_delta": str(score_delta),
                    "message": item.explanation_message,
                    "is_blocking": is_blocking,
                    "condition_checks": payload.get("condition_checks", []),
                }
            )

            if not item.applied:
                continue
            if is_blocking or score_delta < 0:
                gaps_criticos.append(item.explanation_message)
            if score_delta > 0:
                fatores_positivos.append(item.explanation_message)

        score_final = Decimal(str(result.total_score)).quantize(Decimal("0.01"))
        faixa = "baixo"
        if score_final >= Decimal("70.00"):
            faixa = "alto"
        elif score_final >= Decimal("40.00"):
            faixa = "medio"

        return {
            "roadmap_schema_version": self.settings.roadmap_schema_version,
            "programa_alvo": {
                "program_id": str(assessment.program_id),
                "program_name": assessment.program.name if assessment.program else None,
                "program_version_id": str(result.program_version_id),
                "program_version": (
                    result.program_version.version if result.program_version else None
                ),
            },
            "perfil": profile_json,
            "score": {
                "score_final": str(score_final),
                "faixa": faixa,
                "algorithm_version": result.algorithm_version,
                "rules_version_hash": result.rules_version_hash,
            },
            "fatores_positivos": fatores_positivos,
            "gaps_criticos": gaps_criticos,
            "breakdown": breakdown,
        }

    def _validate_contract(self, contract: RoadmapContract) -> None:
        if contract.roadmap_schema_version != self.settings.roadmap_schema_version:
            raise ValueError(
                "Roadmap schema version mismatch: "
                f"expected={self.settings.roadmap_schema_version} "
                f"got={contract.roadmap_schema_version}"
            )
        seen_orders: set[int] = set()
        for step in contract.passos_priorizados:
            if step.step_order in seen_orders:
                raise ValueError(f"Duplicate roadmap step_order={step.step_order}")
            seen_orders.add(step.step_order)

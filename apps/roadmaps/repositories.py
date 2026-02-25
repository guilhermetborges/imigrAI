from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from apps.assessments.models import Assessment, AssessmentResult
from apps.roadmaps.models import Roadmap, RoadmapStatus, RoadmapStep
from apps.roadmaps.schemas import RoadmapContract


class RoadmapsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_assessment_for_roadmap(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
    ) -> Assessment | None:
        query = (
            select(Assessment)
            .where(Assessment.id == assessment_id, Assessment.user_id == user_id)
            .options(
                joinedload(Assessment.result).selectinload(AssessmentResult.items),
                joinedload(Assessment.result).joinedload(AssessmentResult.program_version),
                joinedload(Assessment.profile_snapshot),
                joinedload(Assessment.program),
            )
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_roadmap(self, roadmap_id: UUID) -> Roadmap | None:
        result = await self.db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
        return result.scalar_one_or_none()

    async def get_roadmap_detail(self, roadmap_id: UUID) -> Roadmap | None:
        query = select(Roadmap).where(Roadmap.id == roadmap_id).options(selectinload(Roadmap.steps))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_roadmap_for_generation(self, roadmap_id: UUID) -> Roadmap | None:
        query = (
            select(Roadmap)
            .where(Roadmap.id == roadmap_id)
            .options(
                selectinload(Roadmap.steps),
                joinedload(Roadmap.assessment_result)
                .joinedload(AssessmentResult.assessment)
                .joinedload(Assessment.profile_snapshot),
                joinedload(Roadmap.assessment_result).selectinload(AssessmentResult.items),
                joinedload(Roadmap.assessment_result).joinedload(AssessmentResult.program_version),
                joinedload(Roadmap.assessment_result)
                .joinedload(AssessmentResult.assessment)
                .joinedload(Assessment.program),
            )
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def create_roadmap(
        self,
        *,
        user_id: UUID,
        assessment_result_id: UUID,
        roadmap_schema_version: str,
        trace_id: str | None,
    ) -> Roadmap:
        roadmap = Roadmap(
            user_id=user_id,
            assessment_result_id=assessment_result_id,
            roadmap_schema_version=roadmap_schema_version,
            status=RoadmapStatus.pending,
            summary="Roadmap generation pending",
            trace_id=trace_id,
        )
        self.db.add(roadmap)
        await self.db.commit()
        await self.db.refresh(roadmap)
        return roadmap

    async def mark_running(self, roadmap: Roadmap) -> None:
        roadmap.status = RoadmapStatus.pending
        roadmap.generation_error = None
        roadmap.completed_at = None
        await self.db.commit()

    async def mark_failed(self, roadmap: Roadmap, *, error_message: str) -> None:
        roadmap.status = RoadmapStatus.failed
        roadmap.generation_error = error_message
        roadmap.completed_at = datetime.now(UTC)
        await self.db.commit()

    async def apply_generated_contract(
        self,
        *,
        roadmap: Roadmap,
        contract: RoadmapContract,
        provider_name: str,
        provider_model: str,
    ) -> None:
        for existing in roadmap.steps:
            await self.db.delete(existing)
        await self.db.flush()

        roadmap.status = RoadmapStatus.completed
        roadmap.summary = contract.objetivo
        roadmap.manual_review_required = contract.manual_review_required
        roadmap.generation_error = None
        roadmap.llm_provider = provider_name
        roadmap.llm_model = provider_model
        roadmap.completed_at = datetime.now(UTC)

        for step in contract.passos_priorizados:
            roadmap_step = RoadmapStep(
                roadmap_id=roadmap.id,
                step_order=step.step_order,
                title=step.titulo,
                description=step.descricao,
                related_gap_json={"gap": step.gap_relacionado} if step.gap_relacionado else {},
                is_required=step.is_required,
                eta_weeks=step.prazo_estimado_semanas,
                dependencies_json=step.dependencias,
                risk_level=step.risco,
                completion_criteria=step.criterio_conclusao,
            )
            self.db.add(roadmap_step)

        await self.db.commit()
        await self.db.refresh(roadmap)

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from apps.assessments.engine import ScoreBreakdownItem
from apps.assessments.models import (
    Assessment,
    AssessmentResult,
    AssessmentResultItem,
    AssessmentStatus,
    UserProfileSnapshot,
)
from apps.immigration_rules.models import ProgramVersion, ProgramVersionStatus, RuleGroup


class AssessmentsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_assessment(self, assessment_id: UUID) -> Assessment | None:
        query = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(
                joinedload(Assessment.profile_snapshot),
                joinedload(Assessment.result).selectinload(AssessmentResult.items),
                joinedload(Assessment.result).joinedload(AssessmentResult.program_version),
            )
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_assessment_status(self, assessment_id: UUID) -> Assessment | None:
        result = await self.db.execute(select(Assessment).where(Assessment.id == assessment_id))
        return result.scalar_one_or_none()

    async def get_assessment_by_user_idempotency(
        self,
        *,
        user_id: UUID,
        idempotency_key: str,
    ) -> Assessment | None:
        query = select(Assessment).where(
            Assessment.user_id == user_id,
            Assessment.idempotency_key == idempotency_key,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_snapshot_version(self, *, user_id: UUID) -> int:
        query = (
            select(UserProfileSnapshot.snapshot_version)
            .where(UserProfileSnapshot.user_id == user_id)
            .order_by(UserProfileSnapshot.snapshot_version.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        latest = result.scalar_one_or_none()
        return int(latest or 0)

    async def create_profile_snapshot(
        self,
        *,
        user_id: UUID,
        snapshot_version: int,
        profile_json: dict,
        profile_hash: str,
    ) -> UserProfileSnapshot:
        snapshot = UserProfileSnapshot(
            user_id=user_id,
            snapshot_version=snapshot_version,
            profile_json=profile_json,
            profile_hash=profile_hash,
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def create_assessment(
        self,
        *,
        user_id: UUID,
        program_id: UUID,
        profile_snapshot_id: UUID,
        idempotency_key: str,
    ) -> Assessment:
        assessment = Assessment(
            user_id=user_id,
            program_id=program_id,
            profile_snapshot_id=profile_snapshot_id,
            idempotency_key=idempotency_key,
            status=AssessmentStatus.pending,
            requested_at=datetime.now(UTC),
        )
        self.db.add(assessment)
        await self.db.flush()
        return assessment

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh_assessment(self, assessment: Assessment) -> Assessment:
        await self.db.refresh(assessment)
        return assessment

    async def set_assessment_status(
        self,
        *,
        assessment: Assessment,
        status_value: AssessmentStatus,
        completed_at: datetime | None = None,
    ) -> None:
        assessment.status = status_value
        assessment.completed_at = completed_at
        await self.db.commit()

    async def get_active_program_version(
        self,
        *,
        program_id: UUID,
        at: datetime,
    ) -> ProgramVersion | None:
        at_utc = at.astimezone(UTC)
        query = (
            select(ProgramVersion)
            .where(
                and_(
                    ProgramVersion.program_id == program_id,
                    ProgramVersion.status == ProgramVersionStatus.active,
                    ProgramVersion.effective_from <= at_utc,
                    or_(
                        ProgramVersion.effective_to.is_(None),
                        ProgramVersion.effective_to > at_utc,
                    ),
                )
            )
            .order_by(ProgramVersion.effective_from.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_rule_groups(self, *, program_version_id: UUID) -> list[RuleGroup]:
        query = (
            select(RuleGroup)
            .where(RuleGroup.program_version_id == program_version_id)
            .options(selectinload(RuleGroup.conditions), selectinload(RuleGroup.outcomes))
            .order_by(RuleGroup.priority.asc(), RuleGroup.code.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def replace_assessment_result(
        self,
        *,
        assessment: Assessment,
        program_version_id: UUID,
        rules_version_hash: str,
        algorithm_version: str,
        total_score: Decimal,
        is_eligible: bool,
        breakdown_items: list[ScoreBreakdownItem],
    ) -> AssessmentResult:
        if assessment.result is not None:
            await self.db.delete(assessment.result)
            await self.db.flush()

        computed_at = datetime.now(UTC)
        result = AssessmentResult(
            assessment_id=assessment.id,
            program_version_id=program_version_id,
            rules_version_hash=rules_version_hash,
            algorithm_version=algorithm_version,
            total_score=float(total_score),
            is_eligible=is_eligible,
            computed_at=computed_at,
        )
        self.db.add(result)
        await self.db.flush()

        for item in breakdown_items:
            result_item = AssessmentResultItem(
                assessment_result_id=result.id,
                rule_group_id=item.rule_group_id,
                rule_condition_id=item.rule_condition_id,
                rule_outcome_id=item.rule_outcome_id,
                applied=item.applied,
                score_delta=float(item.score_delta),
                explanation_message=item.explanation_message,
                audit_payload_json={
                    "condition_checks": list(item.condition_checks),
                    "is_blocking": item.is_blocking,
                    "rule_group_code": item.rule_group_code,
                },
            )
            self.db.add(result_item)

        assessment.status = AssessmentStatus.completed
        assessment.completed_at = computed_at

        await self.db.commit()
        await self.db.refresh(result)
        return result

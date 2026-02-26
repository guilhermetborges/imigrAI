import hashlib
import json
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from apps.assessments.engine import (
    ProgramVersionInput,
    RuleConditionInput,
    RuleGroupInput,
    RuleOutcomeInput,
    ScoreEngine,
)
from apps.assessments.models import Assessment, AssessmentStatus
from apps.assessments.repositories import AssessmentsRepository
from apps.assessments.schemas import (
    AssessmentBreakdownEntryRead,
    AssessmentBreakdownRead,
    AssessmentCreate,
    AssessmentQueuedRead,
    AssessmentStatusRead,
    ProgramVersionUsedRead,
)
from apps.billing.services import BillingService
from apps.common.models import JobType
from apps.common.repositories import JobsRepository


class AssessmentsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AssessmentsRepository(db)
        self.jobs_repo = JobsRepository(db)
        self.billing_service = BillingService(db)
        settings = get_settings()
        self.engine = ScoreEngine(algorithm_version=settings.score_algorithm_version)

    async def create_assessment(
        self,
        *,
        user_id: UUID,
        payload: AssessmentCreate,
        trace_id: str | None,
    ) -> AssessmentQueuedRead:
        existing = await self.repo.get_assessment_by_user_idempotency(
            user_id=user_id,
            idempotency_key=payload.idempotency_key,
        )
        quota_priority = False
        if existing is None:
            quota = await self.billing_service.consume_assessment_quota(user_id=user_id)
            quota_priority = quota.priority
            snapshot_version = await self.repo.get_latest_snapshot_version(user_id=user_id) + 1
            profile_hash = self._hash_profile(payload.profile_json)
            snapshot = await self.repo.create_profile_snapshot(
                user_id=user_id,
                snapshot_version=snapshot_version,
                profile_json=payload.profile_json,
                profile_hash=profile_hash,
            )
            existing = await self.repo.create_assessment(
                user_id=user_id,
                program_id=payload.program_id,
                profile_snapshot_id=snapshot.id,
                idempotency_key=payload.idempotency_key,
            )
            await self.repo.commit()
            await self.repo.refresh_assessment(existing)
        else:
            quota_priority = await self.billing_service.has_priority_processing(user_id=user_id)

        job = await self.jobs_repo.get_or_create_job(
            job_type=JobType.score_job,
            idempotency_key=f"assessment:{existing.id}",
            assessment_id=existing.id,
            trace_id=trace_id,
        )

        if existing.status in {AssessmentStatus.pending, AssessmentStatus.failed}:
            from apps.assessments.tasks import process_assessment_task

            process_assessment_task.apply_async(
                kwargs={
                    "assessment_id": str(existing.id),
                    "job_id": str(job.id),
                    "trace_id": trace_id,
                },
                queue="score_queue",
                priority=0 if quota_priority else 9,
            )

        return AssessmentQueuedRead(
            assessment_id=existing.id,
            status=existing.status,
            job_id=job.id,
        )

    async def get_assessment_status(
        self, *, assessment_id: UUID, user_id: UUID
    ) -> AssessmentStatusRead:
        assessment = await self.repo.get_assessment_status(assessment_id)
        if assessment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
            )
        if assessment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found",
            )

        job = await self.jobs_repo.get_latest_job_for_assessment(assessment.id)
        return AssessmentStatusRead(
            assessment_id=assessment.id,
            status=assessment.status,
            completed_at=assessment.completed_at,
            job_id=job.id if job else None,
        )

    async def process_assessment(self, assessment_id: UUID) -> None:
        assessment = await self.repo.get_assessment(assessment_id)
        if assessment is None:
            raise ValueError("Assessment not found")

        if assessment.result is not None and assessment.status == AssessmentStatus.completed:
            return

        await self.repo.set_assessment_status(
            assessment=assessment,
            status_value=AssessmentStatus.running,
            completed_at=None,
        )

        try:
            await self._compute_and_persist_assessment(assessment)
        except Exception:
            await self.repo.set_assessment_status(
                assessment=assessment,
                status_value=AssessmentStatus.failed,
                completed_at=None,
            )
            raise

    async def get_assessment_breakdown(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
    ) -> AssessmentBreakdownRead:
        assessment = await self.repo.get_assessment(assessment_id)
        if assessment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found",
            )
        if assessment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found",
            )

        if assessment.result is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Assessment is {assessment.status.value}. Result not ready",
            )

        return self._to_breakdown_response(assessment)

    async def _compute_and_persist_assessment(self, assessment: Assessment) -> None:
        if assessment.profile_snapshot is None:
            raise ValueError("Assessment is missing profile snapshot")

        active_version = await self.repo.get_active_program_version(
            program_id=assessment.program_id,
            at=assessment.requested_at,
        )
        if active_version is None:
            raise ValueError("No active program version found for requested timestamp")

        rule_groups = await self.repo.list_rule_groups(program_version_id=active_version.id)
        if not rule_groups:
            raise ValueError("Program version has no rules configured")

        program_version_input = ProgramVersionInput(
            id=active_version.id,
            version=active_version.version,
            effective_from=active_version.effective_from,
            effective_to=active_version.effective_to,
        )

        rule_group_inputs = [
            RuleGroupInput(
                id=group.id,
                code=group.code,
                name=group.name,
                priority=group.priority,
                match_operator=(
                    group.match_operator.value
                    if hasattr(group.match_operator, "value")
                    else str(group.match_operator)
                ),
                conditions=tuple(
                    RuleConditionInput(
                        id=condition.id,
                        field_key=condition.field_key,
                        operator=(
                            condition.operator.value
                            if hasattr(condition.operator, "value")
                            else str(condition.operator)
                        ),
                        value_json=condition.value_json,
                        condition_order=condition.condition_order,
                        is_required=condition.is_required,
                    )
                    for condition in sorted(
                        group.conditions,
                        key=lambda c: (c.condition_order, c.field_key, str(c.id)),
                    )
                ),
                outcomes=tuple(
                    RuleOutcomeInput(
                        id=outcome.id,
                        score_delta=Decimal(str(outcome.score_delta)),
                        is_blocking=outcome.is_blocking,
                        explanation_message=outcome.explanation_message,
                        outcome_code=outcome.outcome_code,
                    )
                    for outcome in group.outcomes
                ),
            )
            for group in rule_groups
        ]

        computation = self.engine.evaluate(
            profile_snapshot=assessment.profile_snapshot.profile_json,
            program_version=program_version_input,
            rule_groups=rule_group_inputs,
        )

        await self.repo.replace_assessment_result(
            assessment=assessment,
            program_version_id=active_version.id,
            rules_version_hash=computation.rules_version_hash,
            algorithm_version=computation.algorithm_version,
            total_score=computation.score_final,
            is_eligible=computation.is_eligible,
            breakdown_items=list(computation.breakdown),
        )

    def _to_breakdown_response(self, assessment: Assessment) -> AssessmentBreakdownRead:
        result = assessment.result
        if result is None or result.program_version is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Assessment result is incomplete",
            )

        breakdown_items: list[AssessmentBreakdownEntryRead] = []
        positive_factors: list[str] = []
        critical_gaps: list[str] = []

        for item in sorted(result.items, key=lambda entry: (entry.created_at, str(entry.id))):
            payload = item.audit_payload_json or {}
            is_blocking = bool(payload.get("is_blocking", False))
            condition_checks = payload.get("condition_checks", [])
            group_code = str(payload.get("rule_group_code", "unknown"))

            breakdown_items.append(
                AssessmentBreakdownEntryRead(
                    rule_group_id=item.rule_group_id,
                    rule_group_code=group_code,
                    rule_condition_id=item.rule_condition_id,
                    rule_outcome_id=item.rule_outcome_id,
                    applied=item.applied,
                    score_delta=Decimal(str(item.score_delta)),
                    is_blocking=is_blocking,
                    explanation_message=item.explanation_message,
                    condition_checks=condition_checks,
                )
            )

            if not item.applied:
                continue

            delta = Decimal(str(item.score_delta))
            if is_blocking or delta < 0:
                critical_gaps.append(item.explanation_message)
            if delta > 0:
                positive_factors.append(item.explanation_message)

        score_final = Decimal(str(result.total_score)).quantize(Decimal("0.01"))
        faixa = self._faixa(score_final)

        return AssessmentBreakdownRead(
            assessment_id=assessment.id,
            score_final=score_final,
            faixa=faixa,
            fatores_positivos=positive_factors,
            gaps_criticos=critical_gaps,
            program_version_used=ProgramVersionUsedRead(
                id=result.program_version.id,
                version=result.program_version.version,
                effective_from=result.program_version.effective_from,
                effective_to=result.program_version.effective_to,
            ),
            algorithm_version=result.algorithm_version,
            rules_version_hash=result.rules_version_hash,
            items=breakdown_items,
        )

    def _faixa(self, score: Decimal) -> str:
        if score < Decimal("40"):
            return "baixo"
        if score < Decimal("70"):
            return "medio"
        return "alto"

    def _hash_profile(self, profile_json: dict) -> str:
        canonical = json.dumps(
            profile_json, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

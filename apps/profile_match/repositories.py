from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.profile_match.models import ProfileMatchSubmission


class ProfileMatchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_submission(
        self,
        *,
        user_id: UUID | None,
        guest_session_id: str,
        algorithm_version: str,
        profile_json: dict,
        result_json: list[dict],
    ) -> ProfileMatchSubmission:
        submission = ProfileMatchSubmission(
            user_id=user_id,
            guest_session_id=guest_session_id,
            algorithm_version=algorithm_version,
            profile_json=profile_json,
            result_json=result_json,
        )
        self.db.add(submission)
        await self.db.flush()
        return submission

    async def get_submission(self, submission_id: UUID) -> ProfileMatchSubmission | None:
        result = await self.db.execute(
            select(ProfileMatchSubmission).where(ProfileMatchSubmission.id == submission_id)
        )
        return result.scalar_one_or_none()

    async def claim_submission(self, submission: ProfileMatchSubmission, user_id: UUID) -> None:
        submission.user_id = user_id
        submission.claimed_at = datetime.now(UTC)
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, submission: ProfileMatchSubmission) -> None:
        await self.db.refresh(submission)

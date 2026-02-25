from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.immigration_rules.models import ProgramVersionStatus
from apps.immigration_rules.repositories import ImmigrationRulesRepository
from apps.immigration_rules.schemas import (
    CountryCreate,
    CountryUpdate,
    ImmigrationProgramCreate,
    ImmigrationProgramUpdate,
    ProgramVersionActivateRequest,
    ProgramVersionCreate,
    ProgramVersionUpdate,
    RuleConditionCreate,
    RuleConditionUpdate,
    RuleGroupCreate,
    RuleGroupUpdate,
    RuleOutcomeCreate,
    RuleOutcomeUpdate,
)


class ImmigrationRulesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ImmigrationRulesRepository(db)

    async def _commit_and_refresh(self, entity) -> None:
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Integrity constraint violation",
            ) from exc
        await self.db.refresh(entity)

    async def create_country(self, payload: CountryCreate):
        existing = await self.repo.get_country_by_code(payload.code)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Country code already exists"
            )

        country = await self.repo.create_country(
            {
                "code": payload.code.upper(),
                "name": payload.name,
            }
        )
        await self._commit_and_refresh(country)
        return country

    async def update_country(self, country_id: UUID, payload: CountryUpdate):
        country = await self.repo.get_country(country_id)
        if country is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(country, field, value)

        await self._commit_and_refresh(country)
        return country

    async def create_program(self, payload: ImmigrationProgramCreate):
        country = await self.repo.get_country(payload.country_id)
        if country is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")

        existing = await self.repo.get_program_by_country_code(payload.country_id, payload.code)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Program code already exists for this country",
            )

        program = await self.repo.create_program(payload.model_dump())
        await self._commit_and_refresh(program)
        return program

    async def update_program(self, program_id: UUID, payload: ImmigrationProgramUpdate):
        program = await self.repo.get_program(program_id)
        if program is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(program, field, value)

        await self._commit_and_refresh(program)
        return program

    async def create_program_version(self, payload: ProgramVersionCreate):
        program = await self.repo.get_program(payload.program_id)
        if program is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

        existing = await self.repo.get_program_version_by_program_and_version(
            payload.program_id,
            payload.version,
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Version already exists for this program",
            )

        program_version = await self.repo.create_program_version(payload.model_dump())

        if program_version.status == ProgramVersionStatus.active:
            overlap = await self.repo.find_active_overlap_for_program_version(program_version)
            if overlap is not None:
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Cannot create active version with overlapping effective period "
                        f"(conflicts with version={overlap.version})"
                    ),
                )

        await self._commit_and_refresh(program_version)
        return program_version

    async def update_program_version(self, program_version_id: UUID, payload: ProgramVersionUpdate):
        program_version = await self.repo.get_program_version(program_version_id)
        if program_version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Program version not found"
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(program_version, field, value)

        if program_version.status == ProgramVersionStatus.active:
            overlap = await self.repo.find_active_overlap_for_program_version(program_version)
            if overlap is not None:
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Cannot keep active version with overlapping effective period "
                        f"(conflicts with version={overlap.version})"
                    ),
                )

        await self._commit_and_refresh(program_version)
        return program_version

    async def activate_program_version(
        self,
        program_version_id: UUID,
        payload: ProgramVersionActivateRequest,
    ):
        target = await self.repo.get_program_version(program_version_id, for_update=True)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Program version not found"
            )

        overlap = await self.repo.find_active_overlap_for_program_version(target)

        if overlap is not None and not payload.force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Activation would overlap with another active version. "
                    "Set force=true to archive conflicting active versions first."
                ),
            )

        if overlap is not None and payload.force:
            active_versions = await self.repo.list_active_versions_by_program(target.program_id)
            for active in active_versions:
                if active.id != target.id:
                    active.status = ProgramVersionStatus.archived

        target.status = ProgramVersionStatus.active
        await self._commit_and_refresh(target)
        return target

    async def create_rule_group(self, payload: RuleGroupCreate):
        program_version = await self.repo.get_program_version(payload.program_version_id)
        if program_version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Program version not found"
            )

        rule_group = await self.repo.create_rule_group(payload.model_dump())
        await self._commit_and_refresh(rule_group)
        return rule_group

    async def update_rule_group(self, rule_group_id: UUID, payload: RuleGroupUpdate):
        rule_group = await self.repo.get_rule_group(rule_group_id)
        if rule_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule group not found"
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule_group, field, value)

        await self._commit_and_refresh(rule_group)
        return rule_group

    async def delete_rule_group(self, rule_group_id: UUID) -> None:
        rule_group = await self.repo.get_rule_group(rule_group_id)
        if rule_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule group not found"
            )

        await self.db.delete(rule_group)
        await self.db.commit()

    async def create_rule_condition(self, payload: RuleConditionCreate):
        rule_group = await self.repo.get_rule_group(payload.rule_group_id)
        if rule_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule group not found"
            )

        condition = await self.repo.create_rule_condition(payload.model_dump())
        await self._commit_and_refresh(condition)
        return condition

    async def update_rule_condition(self, condition_id: UUID, payload: RuleConditionUpdate):
        condition = await self.repo.get_rule_condition(condition_id)
        if condition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule condition not found"
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(condition, field, value)

        await self._commit_and_refresh(condition)
        return condition

    async def delete_rule_condition(self, condition_id: UUID) -> None:
        condition = await self.repo.get_rule_condition(condition_id)
        if condition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule condition not found"
            )

        await self.db.delete(condition)
        await self.db.commit()

    async def create_rule_outcome(self, payload: RuleOutcomeCreate):
        rule_group = await self.repo.get_rule_group(payload.rule_group_id)
        if rule_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule group not found"
            )

        outcome = await self.repo.create_rule_outcome(payload.model_dump())
        await self._commit_and_refresh(outcome)
        return outcome

    async def update_rule_outcome(self, outcome_id: UUID, payload: RuleOutcomeUpdate):
        outcome = await self.repo.get_rule_outcome(outcome_id)
        if outcome is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule outcome not found"
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(outcome, field, value)

        await self._commit_and_refresh(outcome)
        return outcome

    async def delete_rule_outcome(self, outcome_id: UUID) -> None:
        outcome = await self.repo.get_rule_outcome(outcome_id)
        if outcome is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule outcome not found"
            )

        await self.db.delete(outcome)
        await self.db.commit()

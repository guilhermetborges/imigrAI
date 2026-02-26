from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.immigration_rules.models import (
    Country,
    ImmigrationProgram,
    ProgramVersion,
    ProgramVersionStatus,
    RuleCondition,
    RuleGroup,
    RuleOutcome,
)
from apps.ingestion.models import SourceDocument

_END_OF_TIME = datetime.max.replace(tzinfo=UTC)


class ImmigrationRulesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_country_by_code(self, code: str) -> Country | None:
        query = select(Country).where(Country.code == code.upper())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_country(self, payload: dict) -> Country:
        country = Country(**payload)
        self.db.add(country)
        return country

    async def get_country(self, country_id: UUID) -> Country | None:
        result = await self.db.execute(select(Country).where(Country.id == country_id))
        return result.scalar_one_or_none()

    async def list_countries(self) -> list[Country]:
        result = await self.db.execute(select(Country).order_by(Country.code.asc()))
        return list(result.scalars().all())

    async def list_countries_for_catalog(self) -> list[Country]:
        result = await self.db.execute(
            select(Country).where(Country.is_active.is_(True)).order_by(
                Country.priority_rank.asc().nulls_last(), Country.code.asc()
            )
        )
        return list(result.scalars().all())

    async def get_program_by_country_code(
        self, country_id: UUID, code: str
    ) -> ImmigrationProgram | None:
        query = select(ImmigrationProgram).where(
            and_(ImmigrationProgram.country_id == country_id, ImmigrationProgram.code == code)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_program(self, payload: dict) -> ImmigrationProgram:
        program = ImmigrationProgram(**payload)
        self.db.add(program)
        return program

    async def get_program(self, program_id: UUID) -> ImmigrationProgram | None:
        result = await self.db.execute(
            select(ImmigrationProgram).where(ImmigrationProgram.id == program_id)
        )
        return result.scalar_one_or_none()

    async def list_programs(self, country_id: UUID | None = None) -> list[ImmigrationProgram]:
        query = select(ImmigrationProgram)
        if country_id is not None:
            query = query.where(ImmigrationProgram.country_id == country_id)
        query = query.order_by(ImmigrationProgram.code.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_programs_by_country_code(self, country_code: str) -> list[ImmigrationProgram]:
        query = (
            select(ImmigrationProgram)
            .join(Country, Country.id == ImmigrationProgram.country_id)
            .where(Country.code == country_code.upper(), ImmigrationProgram.is_active.is_(True))
            .order_by(ImmigrationProgram.code.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_program_version_by_program_and_version(
        self,
        program_id: UUID,
        version: str,
    ) -> ProgramVersion | None:
        query = select(ProgramVersion).where(
            and_(ProgramVersion.program_id == program_id, ProgramVersion.version == version)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_program_version(self, payload: dict) -> ProgramVersion:
        program_version = ProgramVersion(**payload)
        self.db.add(program_version)
        return program_version

    async def get_program_version(
        self, program_version_id: UUID, for_update: bool = False
    ) -> ProgramVersion | None:
        query = select(ProgramVersion).where(ProgramVersion.id == program_version_id)
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_program_versions(self, program_id: UUID) -> list[ProgramVersion]:
        query = (
            select(ProgramVersion)
            .where(ProgramVersion.program_id == program_id)
            .order_by(ProgramVersion.effective_from.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_program_version_for_program(
        self, program_id: UUID
    ) -> ProgramVersion | None:
        query = (
            select(ProgramVersion)
            .where(ProgramVersion.program_id == program_id)
            .order_by(ProgramVersion.effective_from.desc(), ProgramVersion.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_source_documents_by_program_version(
        self, program_version_id: UUID
    ) -> list[SourceDocument]:
        query = (
            select(SourceDocument)
            .where(SourceDocument.program_version_id == program_version_id)
            .order_by(SourceDocument.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_active_overlap_for_program_version(
        self,
        program_version: ProgramVersion,
    ) -> ProgramVersion | None:
        target_end = program_version.effective_to or _END_OF_TIME

        query = select(ProgramVersion).where(
            and_(
                ProgramVersion.program_id == program_version.program_id,
                ProgramVersion.status == ProgramVersionStatus.active,
                ProgramVersion.id != program_version.id,
                ProgramVersion.effective_from < target_end,
                func.coalesce(ProgramVersion.effective_to, _END_OF_TIME)
                > program_version.effective_from,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_active_versions_by_program(self, program_id: UUID) -> list[ProgramVersion]:
        query = select(ProgramVersion).where(
            and_(
                ProgramVersion.program_id == program_id,
                ProgramVersion.status == ProgramVersionStatus.active,
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_rule_group(self, payload: dict) -> RuleGroup:
        rule_group = RuleGroup(**payload)
        self.db.add(rule_group)
        return rule_group

    async def get_rule_group(self, rule_group_id: UUID) -> RuleGroup | None:
        result = await self.db.execute(select(RuleGroup).where(RuleGroup.id == rule_group_id))
        return result.scalar_one_or_none()

    async def list_rule_groups(self, program_version_id: UUID) -> list[RuleGroup]:
        query = (
            select(RuleGroup)
            .where(RuleGroup.program_version_id == program_version_id)
            .order_by(RuleGroup.priority.asc(), RuleGroup.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_rule_condition(self, payload: dict) -> RuleCondition:
        condition = RuleCondition(**payload)
        self.db.add(condition)
        return condition

    async def get_rule_condition(self, condition_id: UUID) -> RuleCondition | None:
        result = await self.db.execute(
            select(RuleCondition).where(RuleCondition.id == condition_id)
        )
        return result.scalar_one_or_none()

    async def list_rule_conditions(self, rule_group_id: UUID) -> list[RuleCondition]:
        query = (
            select(RuleCondition)
            .where(RuleCondition.rule_group_id == rule_group_id)
            .order_by(RuleCondition.condition_order.asc(), RuleCondition.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_rule_outcome(self, payload: dict) -> RuleOutcome:
        outcome = RuleOutcome(**payload)
        self.db.add(outcome)
        return outcome

    async def get_rule_outcome(self, outcome_id: UUID) -> RuleOutcome | None:
        result = await self.db.execute(select(RuleOutcome).where(RuleOutcome.id == outcome_id))
        return result.scalar_one_or_none()

    async def list_rule_outcomes(self, rule_group_id: UUID) -> list[RuleOutcome]:
        query = select(RuleOutcome).where(RuleOutcome.rule_group_id == rule_group_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

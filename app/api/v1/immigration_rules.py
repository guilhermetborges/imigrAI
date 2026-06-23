from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from apps.immigration_rules.repositories import ImmigrationRulesRepository
from apps.immigration_rules.schemas import (
    CountryCreate,
    CountryRead,
    CountryUpdate,
    ImmigrationProgramCreate,
    ImmigrationProgramRead,
    ImmigrationProgramUpdate,
    ProgramVersionActivateRequest,
    ProgramVersionCreate,
    ProgramVersionRead,
    ProgramVersionUpdate,
    RuleConditionCreate,
    RuleConditionRead,
    RuleConditionUpdate,
    RuleGroupCreate,
    RuleGroupRead,
    RuleGroupUpdate,
    RuleOutcomeCreate,
    RuleOutcomeRead,
    RuleOutcomeUpdate,
)
from apps.immigration_rules.services import ImmigrationRulesService

router = APIRouter(prefix="/immigration-rules", tags=["immigration-rules"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/countries", status_code=status.HTTP_201_CREATED)
async def create_country(payload: CountryCreate, db: DbSession) -> CountryRead:
    service = ImmigrationRulesService(db)
    country = await service.create_country(payload)
    return CountryRead.model_validate(country)


@router.get("/countries")
async def list_countries(db: DbSession) -> list[CountryRead]:
    repo = ImmigrationRulesRepository(db)
    countries = await repo.list_countries()
    return [CountryRead.model_validate(c) for c in countries]


@router.get("/countries/{country_id}")
async def get_country(country_id: UUID, db: DbSession) -> CountryRead:
    repo = ImmigrationRulesRepository(db)
    country = await repo.get_country(country_id)
    if country is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")
    return CountryRead.model_validate(country)


@router.patch("/countries/{country_id}")
async def update_country(
    country_id: UUID,
    payload: CountryUpdate,
    db: DbSession,
) -> CountryRead:
    service = ImmigrationRulesService(db)
    country = await service.update_country(country_id, payload)
    return CountryRead.model_validate(country)


@router.post("/programs", status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: ImmigrationProgramCreate,
    db: DbSession,
) -> ImmigrationProgramRead:
    service = ImmigrationRulesService(db)
    program = await service.create_program(payload)
    return ImmigrationProgramRead.model_validate(program)


@router.get("/programs")
async def list_programs(
    db: DbSession,
    country_id: UUID | None = None,
) -> list[ImmigrationProgramRead]:
    repo = ImmigrationRulesRepository(db)
    programs = await repo.list_programs(country_id)
    return [ImmigrationProgramRead.model_validate(p) for p in programs]


@router.get("/programs/{program_id}")
async def get_program(program_id: UUID, db: DbSession) -> ImmigrationProgramRead:
    repo = ImmigrationRulesRepository(db)
    program = await repo.get_program(program_id)
    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )
    return ImmigrationProgramRead.model_validate(program)


@router.patch("/programs/{program_id}")
async def update_program(
    program_id: UUID,
    payload: ImmigrationProgramUpdate,
    db: DbSession,
) -> ImmigrationProgramRead:
    service = ImmigrationRulesService(db)
    program = await service.update_program(program_id, payload)
    return ImmigrationProgramRead.model_validate(program)


@router.post("/program-versions", status_code=status.HTTP_201_CREATED)
async def create_program_version(
    payload: ProgramVersionCreate,
    db: DbSession,
) -> ProgramVersionRead:
    service = ImmigrationRulesService(db)
    version = await service.create_program_version(payload)
    return ProgramVersionRead.model_validate(version)


@router.get("/programs/{program_id}/versions")
async def list_program_versions(
    program_id: UUID,
    db: DbSession,
) -> list[ProgramVersionRead]:
    repo = ImmigrationRulesRepository(db)
    versions = await repo.list_program_versions(program_id)
    return [ProgramVersionRead.model_validate(v) for v in versions]


@router.get("/program-versions/{program_version_id}")
async def get_program_version(
    program_version_id: UUID,
    db: DbSession,
) -> ProgramVersionRead:
    repo = ImmigrationRulesRepository(db)
    program_version = await repo.get_program_version(program_version_id)
    if program_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program version not found",
        )
    return ProgramVersionRead.model_validate(program_version)


@router.patch("/program-versions/{program_version_id}")
async def update_program_version(
    program_version_id: UUID,
    payload: ProgramVersionUpdate,
    db: DbSession,
) -> ProgramVersionRead:
    service = ImmigrationRulesService(db)
    version = await service.update_program_version(program_version_id, payload)
    return ProgramVersionRead.model_validate(version)


@router.post("/program-versions/{program_version_id}/activate")
async def activate_program_version(
    program_version_id: UUID,
    payload: ProgramVersionActivateRequest,
    db: DbSession,
) -> ProgramVersionRead:
    service = ImmigrationRulesService(db)
    version = await service.activate_program_version(program_version_id, payload)
    return ProgramVersionRead.model_validate(version)


@router.post("/rule-groups", status_code=status.HTTP_201_CREATED)
async def create_rule_group(
    payload: RuleGroupCreate,
    db: DbSession,
) -> RuleGroupRead:
    service = ImmigrationRulesService(db)
    rule_group = await service.create_rule_group(payload)
    return RuleGroupRead.model_validate(rule_group)


@router.get("/program-versions/{program_version_id}/rule-groups")
async def list_rule_groups(
    program_version_id: UUID,
    db: DbSession,
) -> list[RuleGroupRead]:
    repo = ImmigrationRulesRepository(db)
    groups = await repo.list_rule_groups(program_version_id)
    return [RuleGroupRead.model_validate(g) for g in groups]


@router.get("/rule-groups/{rule_group_id}")
async def get_rule_group(rule_group_id: UUID, db: DbSession) -> RuleGroupRead:
    repo = ImmigrationRulesRepository(db)
    rule_group = await repo.get_rule_group(rule_group_id)
    if rule_group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule group not found")
    return RuleGroupRead.model_validate(rule_group)


@router.patch("/rule-groups/{rule_group_id}")
async def update_rule_group(
    rule_group_id: UUID,
    payload: RuleGroupUpdate,
    db: DbSession,
) -> RuleGroupRead:
    service = ImmigrationRulesService(db)
    rule_group = await service.update_rule_group(rule_group_id, payload)
    return RuleGroupRead.model_validate(rule_group)


@router.delete("/rule-groups/{rule_group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_group(
    rule_group_id: UUID,
    db: DbSession,
) -> Response:
    service = ImmigrationRulesService(db)
    await service.delete_rule_group(rule_group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/rule-conditions", status_code=status.HTTP_201_CREATED)
async def create_rule_condition(
    payload: RuleConditionCreate,
    db: DbSession,
) -> RuleConditionRead:
    service = ImmigrationRulesService(db)
    condition = await service.create_rule_condition(payload)
    return RuleConditionRead.model_validate(condition)


@router.get("/rule-groups/{rule_group_id}/conditions")
async def list_rule_conditions(
    rule_group_id: UUID,
    db: DbSession,
) -> list[RuleConditionRead]:
    repo = ImmigrationRulesRepository(db)
    conditions = await repo.list_rule_conditions(rule_group_id)
    return [RuleConditionRead.model_validate(c) for c in conditions]


@router.get("/rule-conditions/{condition_id}")
async def get_rule_condition(
    condition_id: UUID,
    db: DbSession,
) -> RuleConditionRead:
    repo = ImmigrationRulesRepository(db)
    condition = await repo.get_rule_condition(condition_id)
    if condition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule condition not found",
        )
    return RuleConditionRead.model_validate(condition)


@router.patch("/rule-conditions/{condition_id}")
async def update_rule_condition(
    condition_id: UUID,
    payload: RuleConditionUpdate,
    db: DbSession,
) -> RuleConditionRead:
    service = ImmigrationRulesService(db)
    condition = await service.update_rule_condition(condition_id, payload)
    return RuleConditionRead.model_validate(condition)


@router.delete("/rule-conditions/{condition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_condition(
    condition_id: UUID,
    db: DbSession,
) -> Response:
    service = ImmigrationRulesService(db)
    await service.delete_rule_condition(condition_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/rule-outcomes", status_code=status.HTTP_201_CREATED)
async def create_rule_outcome(
    payload: RuleOutcomeCreate,
    db: DbSession,
) -> RuleOutcomeRead:
    service = ImmigrationRulesService(db)
    outcome = await service.create_rule_outcome(payload)
    return RuleOutcomeRead.model_validate(outcome)


@router.get("/rule-groups/{rule_group_id}/outcomes")
async def list_rule_outcomes(
    rule_group_id: UUID,
    db: DbSession,
) -> list[RuleOutcomeRead]:
    repo = ImmigrationRulesRepository(db)
    outcomes = await repo.list_rule_outcomes(rule_group_id)
    return [RuleOutcomeRead.model_validate(o) for o in outcomes]


@router.get("/rule-outcomes/{outcome_id}")
async def get_rule_outcome(outcome_id: UUID, db: DbSession) -> RuleOutcomeRead:
    repo = ImmigrationRulesRepository(db)
    outcome = await repo.get_rule_outcome(outcome_id)
    if outcome is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule outcome not found")
    return RuleOutcomeRead.model_validate(outcome)


@router.patch("/rule-outcomes/{outcome_id}")
async def update_rule_outcome(
    outcome_id: UUID,
    payload: RuleOutcomeUpdate,
    db: DbSession,
) -> RuleOutcomeRead:
    service = ImmigrationRulesService(db)
    outcome = await service.update_rule_outcome(outcome_id, payload)
    return RuleOutcomeRead.model_validate(outcome)


@router.delete("/rule-outcomes/{outcome_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_outcome(
    outcome_id: UUID,
    db: DbSession,
) -> Response:
    service = ImmigrationRulesService(db)
    await service.delete_rule_outcome(outcome_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

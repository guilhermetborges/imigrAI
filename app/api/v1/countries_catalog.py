from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from apps.immigration_rules.fixtures import rule_coverage_status
from apps.immigration_rules.repositories import ImmigrationRulesRepository
from apps.immigration_rules.schemas import (
    CountryCatalogRead,
    CountryProgramsCatalogRead,
    ProgramCatalogRead,
    ProgramSourceCatalogRead,
)

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=list[CountryCatalogRead])
async def list_country_catalog(db: AsyncSession = Depends(get_db)) -> list[CountryCatalogRead]:
    repo = ImmigrationRulesRepository(db)
    countries = await repo.list_countries_for_catalog()

    payload: list[CountryCatalogRead] = []
    for country in countries:
        programs = await repo.list_programs(country_id=country.id)
        active_programs = [program for program in programs if program.is_active]
        payload.append(
            CountryCatalogRead(
                code=country.code,
                name=country.name,
                priority_rank=country.priority_rank,
                diaspora_population_estimate=country.diaspora_population_estimate,
                program_count=len(active_programs),
                rule_coverage_status=rule_coverage_status(country.code),
            )
        )

    return payload


@router.get("/{country_code}/programs", response_model=CountryProgramsCatalogRead)
async def list_country_programs(
    country_code: str,
    db: AsyncSession = Depends(get_db),
) -> CountryProgramsCatalogRead:
    repo = ImmigrationRulesRepository(db)
    country = await repo.get_country_by_code(country_code)
    if country is None or not country.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")

    programs = await repo.list_programs_by_country_code(country_code)
    program_payload: list[ProgramCatalogRead] = []
    for program in programs:
        latest_version = await repo.get_latest_program_version_for_program(program.id)
        documents: list[ProgramSourceCatalogRead] = []
        if latest_version is not None:
            source_documents = await repo.list_source_documents_by_program_version(
                latest_version.id
            )
            for source_document in source_documents:
                source_key = None
                if source_document.metadata_json:
                    source_key = source_document.metadata_json.get("source_key")
                documents.append(
                    ProgramSourceCatalogRead(
                        source_key=source_key,
                        title=source_document.title,
                        source_url=source_document.source_url,
                    )
                )

        program_payload.append(
            ProgramCatalogRead(
                code=program.code,
                name=program.name,
                description=program.description,
                version=(latest_version.version if latest_version else None),
                version_status=(latest_version.status if latest_version else None),
                source_documents=documents,
            )
        )

    return CountryProgramsCatalogRead(
        country_code=country.code,
        country_name=country.name,
        programs=program_payload,
    )

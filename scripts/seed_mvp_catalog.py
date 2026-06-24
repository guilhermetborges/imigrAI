from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from apps.immigration_rules.fixtures import (
    MVP_COUNTRY_CATALOG,
    MVP_PROGRAM_EFFECTIVE_FROM,
)
from apps.immigration_rules.models import (
    Country,
    ImmigrationProgram,
    ProgramVersion,
    ProgramVersionStatus,
)
from apps.ingestion.models import SourceDocument
from apps.ingestion.repositories import IngestionRepository
from apps.ingestion.schemas import SourceRegistrySeed


def _parse_effective_from() -> datetime:
    return datetime.fromisoformat(MVP_PROGRAM_EFFECTIVE_FROM)


async def seed_mvp_catalog(db: AsyncSession) -> dict[str, int]:
    repo = IngestionRepository(db)
    effective_from = _parse_effective_from()
    summary = {
        "countries_created": 0,
        "countries_updated": 0,
        "programs_created": 0,
        "programs_updated": 0,
        "program_versions_created": 0,
        "program_versions_updated": 0,
        "source_registry_created_or_updated": 0,
        "source_documents_created": 0,
        "source_documents_updated": 0,
    }

    for country_data in MVP_COUNTRY_CATALOG:
        country = await _seed_country(db, country_data, summary)
        await _seed_programs_for_country(db, repo, country, country_data, effective_from, summary)

    await db.commit()
    return summary


async def _seed_country(db: AsyncSession, country_data: dict, summary: dict[str, int]) -> Country:
    country = await db.scalar(select(Country).where(Country.code == country_data["code"]))
    if country is None:
        country = Country(
            code=country_data["code"],
            name=country_data["name"],
            is_active=True,
            priority_rank=country_data["priority_rank"],
            diaspora_population_estimate=country_data["diaspora_population_estimate"],
            prioritization_source_url=country_data["prioritization_source_url"],
        )
        db.add(country)
        summary["countries_created"] += 1
        await db.flush()
    else:
        changed = False
        for field in (
            "name",
            "priority_rank",
            "diaspora_population_estimate",
            "prioritization_source_url",
        ):
            value = country_data[field]
            if getattr(country, field) != value:
                setattr(country, field, value)
                changed = True
        if not country.is_active:
            country.is_active = True
            changed = True
        if changed:
            summary["countries_updated"] += 1
    return country


async def _seed_program(
    db: AsyncSession,
    country: Country,
    program_data: dict,
    summary: dict[str, int],
) -> ImmigrationProgram:
    program = await db.scalar(
        select(ImmigrationProgram).where(
            and_(
                ImmigrationProgram.country_id == country.id,
                ImmigrationProgram.code == program_data["code"],
            )
        )
    )
    if program is None:
        program = ImmigrationProgram(
            country_id=country.id,
            code=program_data["code"],
            name=program_data["name"],
            description=program_data["description"],
            is_active=True,
        )
        db.add(program)
        summary["programs_created"] += 1
        await db.flush()
    else:
        changed = False
        if program.name != program_data["name"]:
            program.name = program_data["name"]
            changed = True
        if program.description != program_data["description"]:
            program.description = program_data["description"]
            changed = True
        if not program.is_active:
            program.is_active = True
            changed = True
        if changed:
            summary["programs_updated"] += 1
    return program


async def _seed_programs_for_country(
    db: AsyncSession,
    repo: IngestionRepository,
    country: Country,
    country_data: dict,
    effective_from: datetime,
    summary: dict[str, int],
) -> None:
    for program_data in country_data["programs"]:
        program = await _seed_program(db, country, program_data, summary)

        await _seed_program_version_and_sources(
            db, repo, program, country_data, program_data, effective_from, summary
        )


async def _seed_program_version_and_sources(
    db: AsyncSession,
    repo: IngestionRepository,
    program: ImmigrationProgram,
    country_data: dict,
    program_data: dict,
    effective_from: datetime,
    summary: dict[str, int],
) -> ProgramVersion:
    program_version = await db.scalar(
        select(ProgramVersion).where(
            and_(
                ProgramVersion.program_id == program.id,
                ProgramVersion.version == program_data["version"],
            )
        )
    )
    if program_version is None:
        program_version = ProgramVersion(
            program_id=program.id,
            version=program_data["version"],
            status=ProgramVersionStatus.draft,
            effective_from=effective_from,
            effective_to=None,
        )
        db.add(program_version)
        summary["program_versions_created"] += 1
        await db.flush()
    elif program_version.effective_from != effective_from:
        program_version.effective_from = effective_from
        summary["program_versions_updated"] += 1

    for source in program_data["sources"]:
        await _seed_source(db, repo, source, country_data, program_version, summary)

    return program_version


async def _seed_source(
    db: AsyncSession,
    repo: IngestionRepository,
    source: dict,
    country_data: dict,
    program_version: ProgramVersion,
    summary: dict[str, int],
) -> None:
    source_seed = SourceRegistrySeed(
        source_key=source["source_key"],
        country_code=country_data["code"],
        country_name=country_data["name"],
        program_code=country_data["code"],
        program_name=country_data["name"],
        source_type=source["source_type"],
        source_url=source["source_url"],
        robots_url=source["robots_url"],
        terms_url=source["terms_url"],
        schedule_cron=source["schedule_cron"],
        metadata_json={
            "seed": "mvp_2026_02",
            "official_source": True,
            "priority_rank": country_data["priority_rank"],
        },
    )
    source_row = await repo.upsert_source_seed(source_seed)
    summary["source_registry_created_or_updated"] += 1

    source_document = await db.scalar(
        select(SourceDocument).where(
            and_(
                SourceDocument.program_version_id == program_version.id,
                SourceDocument.source_url == source["source_url"],
            )
        )
    )
    if source_document is None:
        db.add(
            SourceDocument(
                source_id=source_row.id,
                ingestion_run_item_id=None,
                program_version_id=program_version.id,
                title=source["document_title"],
                source_url=source["source_url"],
                checksum_sha256=None,
                raw_storage_uri=None,
                published_at=None,
                metadata_json={
                    "seed": "mvp_2026_02",
                    "source_key": source["source_key"],
                    "country_code": country_data["code"],
                    "program_code": country_data["code"],
                    "official_source": True,
                },
            )
        )
        summary["source_documents_created"] += 1
    else:
        source_document.source_id = source_row.id
        source_document.title = source["document_title"]
        source_document.metadata_json = {
            "seed": "mvp_2026_02",
            "source_key": source["source_key"],
            "country_code": country_data["code"],
            "program_code": country_data["code"],
            "official_source": True,
        }
        summary["source_documents_updated"] += 1


async def run_seed() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        return await seed_mvp_catalog(db)

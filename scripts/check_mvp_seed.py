from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.db import AsyncSessionLocal
from apps.immigration_rules.fixtures import (
    MVP_COUNTRY_CATALOG,
    expected_country_count,
    expected_program_count,
    expected_source_count,
)
from apps.immigration_rules.models import Country, ImmigrationProgram, ProgramVersion
from apps.ingestion.models import SourceDocument, SourceRegistry


async def check_seed() -> dict[str, object]:
    country_codes = [country["code"] for country in MVP_COUNTRY_CATALOG]

    async with AsyncSessionLocal() as db:
        seeded_country_count = int(
            await db.scalar(
                select(func.count())
                .select_from(Country)
                .where(Country.code.in_(country_codes))
            )
            or 0
        )
        seeded_program_count = int(
            await db.scalar(
                select(func.count())
                .select_from(ImmigrationProgram)
                .join(Country, Country.id == ImmigrationProgram.country_id)
                .where(Country.code.in_(country_codes))
            )
            or 0
        )
        seeded_program_version_count = int(
            await db.scalar(
                select(func.count())
                .select_from(ProgramVersion)
                .join(ImmigrationProgram, ImmigrationProgram.id == ProgramVersion.program_id)
                .join(Country, Country.id == ImmigrationProgram.country_id)
                .where(Country.code.in_(country_codes))
            )
            or 0
        )
        seeded_source_registry_count = int(
            await db.scalar(
                select(func.count())
                .select_from(SourceRegistry)
                .where(SourceRegistry.country_code.in_(country_codes))
            )
            or 0
        )
        seeded_source_document_count = int(
            await db.scalar(
                select(func.count())
                .select_from(SourceDocument)
                .join(ProgramVersion, ProgramVersion.id == SourceDocument.program_version_id)
                .join(ImmigrationProgram, ImmigrationProgram.id == ProgramVersion.program_id)
                .join(Country, Country.id == ImmigrationProgram.country_id)
                .where(Country.code.in_(country_codes))
            )
            or 0
        )

        duplicated_source_documents = await db.execute(
            select(
                SourceDocument.program_version_id,
                SourceDocument.source_url,
                func.count().label("total"),
            )
            .where(SourceDocument.program_version_id.is_not(None))
            .group_by(SourceDocument.program_version_id, SourceDocument.source_url)
            .having(func.count() > 1)
        )
        duplicate_rows = [
            {
                "program_version_id": str(row.program_version_id),
                "source_url": row.source_url,
                "count": int(row.total),
            }
            for row in duplicated_source_documents
        ]

        existing_country_codes_rows = await db.execute(
            select(Country.code).where(Country.code.in_(country_codes))
        )
        existing_country_codes = {row.code for row in existing_country_codes_rows}

    expected_countries = expected_country_count()
    expected_programs = expected_program_count()
    expected_sources = expected_source_count()
    missing_country_codes = sorted(set(country_codes) - existing_country_codes)

    checks = {
        "countries": seeded_country_count >= expected_countries,
        "programs": seeded_program_count >= expected_programs,
        "program_versions": seeded_program_version_count >= expected_programs,
        "source_registry": seeded_source_registry_count >= expected_sources,
        "source_documents": seeded_source_document_count >= expected_sources,
        "source_documents_unique_per_version_url": len(duplicate_rows) == 0,
    }

    return {
        "ok": all(checks.values()),
        "checks": checks,
        "expected": {
            "countries": expected_countries,
            "programs": expected_programs,
            "program_versions": expected_programs,
            "source_registry": expected_sources,
            "source_documents": expected_sources,
        },
        "actual": {
            "countries": seeded_country_count,
            "programs": seeded_program_count,
            "program_versions": seeded_program_version_count,
            "source_registry": seeded_source_registry_count,
            "source_documents": seeded_source_document_count,
        },
        "missing_country_codes": missing_country_codes,
        "source_document_duplicates": duplicate_rows,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(asyncio.run(check_seed()), ensure_ascii=True))

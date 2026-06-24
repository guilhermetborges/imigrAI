from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal
from apps.assessments.fixtures.mvp_rules import MVP_RULE_FIXTURES
from apps.immigration_rules.models import (
    Country,
    ImmigrationProgram,
    ProgramVersion,
    ProgramVersionStatus,
    RuleCondition,
    RuleGroup,
    RuleGroupMatchOperator,
    RuleOperator,
    RuleOutcome,
)


def _to_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value).astimezone(UTC)


async def _seed_fixtures(fixtures: dict[str, dict]) -> None:
    async with AsyncSessionLocal() as db:
        for fixture in fixtures.values():
            country_data = fixture["country"]
            country = await db.scalar(select(Country).where(Country.code == country_data["code"]))
            if country is None:
                country = Country(
                    code=country_data["code"],
                    name=country_data["name"],
                    is_active=True,
                )
                db.add(country)
                await db.flush()

            program_data = fixture["program"]
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
                    description=f"Seed fixture for {country_data['code']}",
                    is_active=True,
                )
                db.add(program)
                await db.flush()

            version_data = fixture["program_version"]
            program_version = await db.scalar(
                select(ProgramVersion).where(
                    and_(
                        ProgramVersion.program_id == program.id,
                        ProgramVersion.version == version_data["version"],
                    )
                )
            )
            if program_version is None:
                program_version = ProgramVersion(
                    program_id=program.id,
                    version=version_data["version"],
                    status=ProgramVersionStatus.active,
                    effective_from=_to_datetime(version_data["effective_from"]),
                    effective_to=_to_datetime(version_data["effective_to"]),
                )
                db.add(program_version)
                await db.flush()

            for group_data in fixture["rule_groups"]:
                await _seed_rule_group(db, program_version, group_data)

        await db.commit()


async def _seed_rule_group(
    db: AsyncSession,
    program_version: ProgramVersion,
    group_data: dict,
) -> None:
    rule_group = await db.scalar(
        select(RuleGroup).where(
            and_(
                RuleGroup.program_version_id == program_version.id,
                RuleGroup.code == group_data["code"],
            )
        )
    )
    if rule_group is None:
        rule_group = RuleGroup(
            program_version_id=program_version.id,
            code=group_data["code"],
            name=group_data["name"],
            priority=group_data["priority"],
            match_operator=RuleGroupMatchOperator(group_data["match_operator"]),
            is_active=True,
        )
        db.add(rule_group)
        await db.flush()

    for condition_data in group_data["conditions"]:
        existing_condition = await db.scalar(
            select(RuleCondition).where(
                and_(
                    RuleCondition.rule_group_id == rule_group.id,
                    RuleCondition.field_key == condition_data["field_key"],
                    RuleCondition.operator == RuleOperator(condition_data["operator"]),
                    RuleCondition.condition_order == condition_data["condition_order"],
                )
            )
        )
        if existing_condition is not None:
            continue

        db.add(
            RuleCondition(
                rule_group_id=rule_group.id,
                field_key=condition_data["field_key"],
                operator=RuleOperator(condition_data["operator"]),
                value_json=condition_data["value_json"],
                condition_order=condition_data["condition_order"],
                is_required=condition_data["is_required"],
            )
        )

    for outcome_data in group_data["outcomes"]:
        existing_outcome = await db.scalar(
            select(RuleOutcome).where(
                and_(
                    RuleOutcome.rule_group_id == rule_group.id,
                    RuleOutcome.outcome_code == outcome_data["outcome_code"],
                )
            )
        )
        if existing_outcome is not None:
            continue

        db.add(
            RuleOutcome(
                rule_group_id=rule_group.id,
                score_delta=outcome_data["score_delta"],
                is_blocking=outcome_data["is_blocking"],
                explanation_message=outcome_data["explanation_message"],
                outcome_code=outcome_data["outcome_code"],
            )
        )


async def seed() -> None:
    await _seed_fixtures(MVP_RULE_FIXTURES)


async def seed_for_countries(country_codes: Iterable[str]) -> None:
    selected = {code.upper() for code in country_codes}
    if not selected:
        return

    filtered = {
        country_code: fixture
        for country_code, fixture in MVP_RULE_FIXTURES.items()
        if country_code.upper() in selected
    }
    await _seed_fixtures(filtered)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed MVP score rule fixtures")
    parser.add_argument(
        "--countries",
        nargs="*",
        default=None,
        help="Optional list of country codes to seed (example: --countries US PT DE)",
    )
    args = parser.parse_args()

    if args.countries:
        asyncio.run(seed_for_countries(args.countries))
    else:
        asyncio.run(seed())
    print("MVP rule fixtures seeded successfully.")

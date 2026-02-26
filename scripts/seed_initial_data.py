from __future__ import annotations

import asyncio
import json

from apps.immigration_rules.fixtures import MVP_RULE_FIXTURE_COUNTRY_CODES
from scripts.seed_mvp_catalog import run_seed as seed_mvp_catalog
from scripts.seed_mvp_rules import seed_for_countries


async def run_seed() -> dict[str, int]:
    catalog_summary = await seed_mvp_catalog()
    await seed_for_countries(MVP_RULE_FIXTURE_COUNTRY_CODES)
    return {
        **catalog_summary,
        "rule_fixture_countries_seeded": len(MVP_RULE_FIXTURE_COUNTRY_CODES),
    }


def main() -> None:
    result = asyncio.run(run_seed())
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()

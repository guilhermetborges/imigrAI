from apps.immigration_rules.fixtures import MVP_COUNTRY_CATALOG
from apps.ingestion.models import SourceType
from apps.ingestion.schemas import SourceRegistrySeed


def _build_default_source_seeds() -> list[SourceRegistrySeed]:
    seeds: list[SourceRegistrySeed] = []
    for country in MVP_COUNTRY_CATALOG:
        for program in country["programs"]:
            for source in program["sources"]:
                seeds.append(
                    SourceRegistrySeed(
                        source_key=source["source_key"],
                        country_code=country["code"],
                        country_name=country["name"],
                        program_code=program["code"],
                        program_name=program["name"],
                        source_type=SourceType(source["source_type"]),
                        source_url=source["source_url"],
                        robots_url=source["robots_url"],
                        terms_url=source["terms_url"],
                        schedule_cron=source["schedule_cron"],
                    )
                )
    return seeds


DEFAULT_SOURCE_SEEDS: list[SourceRegistrySeed] = _build_default_source_seeds()

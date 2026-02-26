from apps.immigration_rules.fixtures import (
    MVP_COUNTRY_CATALOG,
    MVP_RULE_FIXTURE_COUNTRY_CODES,
    expected_country_count,
    expected_program_count,
    expected_source_count,
)


def test_mvp_country_catalog_expected_counts() -> None:
    assert expected_country_count() == 15
    assert expected_program_count() >= 15
    assert expected_source_count() >= 15
    assert len(MVP_COUNTRY_CATALOG) == 15


def test_mvp_rule_fixture_coverage_has_at_least_five_countries() -> None:
    assert len(MVP_RULE_FIXTURE_COUNTRY_CODES) >= 5

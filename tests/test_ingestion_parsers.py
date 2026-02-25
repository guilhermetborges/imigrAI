from decimal import Decimal

from apps.ingestion.extractors import DeterministicExtractor
from apps.ingestion.models import SourceRegistry, SourceType


def _build_source(
    *,
    source_key: str,
    country_code: str,
    country_name: str,
    program_code: str,
    program_name: str,
) -> SourceRegistry:
    return SourceRegistry(
        source_key=source_key,
        country_code=country_code,
        country_name=country_name,
        program_code=program_code,
        program_name=program_name,
        source_type=SourceType.html,
        source_url=f"https://example.com/{source_key}",
        parser_name="deterministic-v1",
        parser_version="1.0.0",
        confidence_threshold=Decimal("0.70"),
        metadata_json={},
    )


def test_parser_us_uscis_detects_age_income_and_language() -> None:
    source = _build_source(
        source_key="us_uscis_main",
        country_code="US",
        country_name="Estados Unidos",
        program_code="US_GENERAL_IMMIGRATION",
        program_name="US Immigration",
    )
    content = b"""
    <html><head><title>USCIS Eligibility</title></head>
    <body>
      <h1>Program Requirements</h1>
      Applicants age 45 or under.
      Minimum income $5000 monthly.
      English level B2 required.
    </body></html>
    """

    extractor = DeterministicExtractor()
    result = extractor.extract(
        source=source, content=content, content_type="text/html", title="USCIS"
    )

    codes = {group.code for group in result.payload.rule_groups}
    assert "age_requirement" in codes
    assert "income_requirement" in codes
    assert "language_requirement" in codes
    assert result.payload.confidence_score >= Decimal("0.80")


def test_parser_pt_aima_detects_income_signal() -> None:
    source = _build_source(
        source_key="pt_aima",
        country_code="PT",
        country_name="Portugal",
        program_code="PT_AIMA_VISAS",
        program_name="Portugal AIMA",
    )
    content = b"""
    <html><body>
    <h2>Residencia</h2>
    O requerente deve apresentar rendimento minimo de EUR 1200.
    </body></html>
    """

    extractor = DeterministicExtractor()
    result = extractor.extract(
        source=source, content=content, content_type="text/html", title="AIMA"
    )

    codes = {group.code for group in result.payload.rule_groups}
    assert "income_requirement" in codes
    assert result.payload.sections


def test_parser_uk_gov_detects_age_signal() -> None:
    source = _build_source(
        source_key="uk_gov_immigration",
        country_code="GB",
        country_name="Reino Unido",
        program_code="UK_VISAS_IMMIGRATION",
        program_name="UK Visas",
    )
    content = b"""
    <html><body>
    <h2>Skilled Worker</h2>
    Age 30 years and above can score additional points.
    </body></html>
    """

    extractor = DeterministicExtractor()
    result = extractor.extract(
        source=source, content=content, content_type="text/html", title="GOV.UK"
    )

    codes = {group.code for group in result.payload.rule_groups}
    assert "age_requirement" in codes


def test_parser_ca_ircc_detects_language_signal() -> None:
    source = _build_source(
        source_key="ca_ircc",
        country_code="CA",
        country_name="Canada",
        program_code="CA_IRCC_IMMIGRATION",
        program_name="IRCC",
    )
    content = b"""
    <html><body>
    <h1>Express Entry</h1>
    Applicants should demonstrate language level C1 for strongest profile.
    </body></html>
    """

    extractor = DeterministicExtractor()
    result = extractor.extract(
        source=source, content=content, content_type="text/html", title="IRCC"
    )

    codes = {group.code for group in result.payload.rule_groups}
    assert "language_requirement" in codes


def test_parser_france_visas_falls_back_to_baseline_rule() -> None:
    source = _build_source(
        source_key="fr_france_visas",
        country_code="FR",
        country_name="Franca",
        program_code="FR_FRANCE_VISAS",
        program_name="France-Visas",
    )
    content = (
        b"<html><body><h1>General information page</h1>"
        b"<p>No structured criteria listed.</p></body></html>"
    )

    extractor = DeterministicExtractor()
    result = extractor.extract(
        source=source,
        content=content,
        content_type="text/html",
        title="France-Visas",
    )

    codes = {group.code for group in result.payload.rule_groups}
    assert "baseline_publication_guard" in codes
    assert result.payload.manual_review_required is True

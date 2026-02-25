from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from apps.assessments.engine import (
    ProgramVersionInput,
    RuleConditionInput,
    RuleGroupInput,
    RuleOutcomeInput,
    ScoreEngine,
    ScoreEngineInputError,
)
from apps.assessments.fixtures.mvp_rules import build_program_version_input, build_rule_group_inputs


def test_profile_with_immediate_blocking() -> None:
    engine = ScoreEngine()
    program_version = build_program_version_input("CA")
    groups = build_rule_group_inputs("CA")

    profile = {
        "idade": 50,
        "escolaridade": "master",
        "profissao": {"codigo": "21231", "nome": "Software Engineer"},
        "idiomas": {"en": {"framework": "CEFR", "level": "C1"}},
        "renda_atual": 8000,
    }

    result = engine.evaluate(
        profile_snapshot=profile,
        program_version=program_version,
        rule_groups=groups,
    )

    assert result.is_blocked is True
    assert result.score_final == Decimal("0.00")
    assert result.faixa == "baixo"
    assert any("Idade acima" in gap for gap in result.gaps_criticos)


def test_high_score_with_language_gap() -> None:
    engine = ScoreEngine()
    program_version = build_program_version_input("CA")
    groups = build_rule_group_inputs("CA")

    profile = {
        "idade": 30,
        "escolaridade": "master",
        "profissao": {"codigo": "21231", "nome": "Software Engineer"},
        "idiomas": {
            "en": {"framework": "CEFR", "level": "B2"},
            "fr": {"framework": "CEFR", "level": "B2"},
        },
        "renda_atual": 6000,
    }

    result = engine.evaluate(
        profile_snapshot=profile,
        program_version=program_version,
        rule_groups=groups,
    )

    assert result.faixa == "alto"
    assert result.score_final >= Decimal("70.00")
    assert any("Gap critico de idioma ingles" in gap for gap in result.gaps_criticos)
    assert any("Frances adiciona pontos" in factor for factor in result.fatores_positivos)


def test_single_variable_change_moves_band() -> None:
    engine = ScoreEngine()
    program_version = build_program_version_input("AU")
    groups = build_rule_group_inputs("AU")

    base_profile = {
        "idade": 30,
        "escolaridade": "bachelor",
        "profissao": {"codigo": "261313", "nome": "Developer Programmer"},
        "idiomas": {"en": {"framework": "CEFR", "level": "B2"}},
        "renda_atual": 4400,
        "tem_restricao_medica": False,
    }

    improved_profile = {**base_profile, "renda_atual": 4600}

    low_income = engine.evaluate(
        profile_snapshot=base_profile,
        program_version=program_version,
        rule_groups=groups,
    )
    high_income = engine.evaluate(
        profile_snapshot=improved_profile,
        program_version=program_version,
        rule_groups=groups,
    )

    assert low_income.faixa == "medio"
    assert high_income.faixa == "alto"
    assert high_income.score_final > low_income.score_final


def test_reprocessing_same_snapshot_produces_same_result() -> None:
    engine = ScoreEngine()
    program_version = build_program_version_input("PT")
    groups = build_rule_group_inputs("PT")

    profile = {
        "idade": 38,
        "escolaridade": "bachelor",
        "profissao": {"codigo": "2512", "nome": "Developer"},
        "idiomas": {
            "pt": {"framework": "CEFR", "level": "B1"},
            "en": {"framework": "CEFR", "level": "B2"},
        },
        "renda_atual": 3500,
    }

    first = engine.evaluate(
        profile_snapshot=profile,
        program_version=program_version,
        rule_groups=groups,
    )
    second = engine.evaluate(
        profile_snapshot=profile,
        program_version=program_version,
        rule_groups=groups,
    )

    assert first.score_final == second.score_final
    assert first.raw_score == second.raw_score
    assert first.faixa == second.faixa
    assert first.rules_version_hash == second.rules_version_hash
    assert first.breakdown == second.breakdown


def test_generic_operators_ne_lte_not_in() -> None:
    engine = ScoreEngine()

    program_version = ProgramVersionInput(
        id=UUID("34c59fec-e7c7-44e6-b1a3-bcf552ff7fac"),
        version="test",
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_to=None,
    )

    group = RuleGroupInput(
        id=UUID("65d1ef73-d6c3-4f22-b87e-d7612dd5cd85"),
        code="operators",
        name="Operators",
        priority=1,
        match_operator="all",
        conditions=(
            RuleConditionInput(
                id=UUID("7e0f282e-f17a-4e13-afd9-c33b2251129b"),
                field_key="idade",
                operator="lte",
                value_json=40,
                condition_order=1,
                is_required=True,
            ),
            RuleConditionInput(
                id=UUID("f9f5f209-6d6a-466f-a7cc-6db8f2602f1e"),
                field_key="profissao_codigo",
                operator="not_in",
                value_json=["99999"],
                condition_order=2,
                is_required=True,
            ),
            RuleConditionInput(
                id=UUID("f2f2f8d0-99a2-4c73-b2ab-8c4062b0f334"),
                field_key="escolaridade",
                operator="ne",
                value_json="fundamental",
                condition_order=3,
                is_required=True,
            ),
        ),
        outcomes=(
            RuleOutcomeInput(
                id=UUID("08d77075-4634-4a8a-916a-c196df20ec9e"),
                score_delta=Decimal("10"),
                is_blocking=False,
                explanation_message="Operators matched",
                outcome_code="OP_MATCH",
            ),
        ),
    )

    profile = {
        "idade": 30,
        "escolaridade": "master",
        "profissao": {"codigo": "261313", "nome": "Developer"},
        "idiomas": {"en": {"framework": "CEFR", "level": "B2"}},
        "renda_atual": 5000,
    }

    result = engine.evaluate(
        profile_snapshot=profile,
        program_version=program_version,
        rule_groups=[group],
    )

    assert result.score_final == Decimal("100.00")
    assert result.fatores_positivos == ("Operators matched",)


def test_missing_required_profile_field_raises_error() -> None:
    engine = ScoreEngine()
    program_version = build_program_version_input("CA")
    groups = build_rule_group_inputs("CA")

    profile = {
        "idade": 30,
        "escolaridade": "master",
        "profissao": {"codigo": "21231", "nome": "Software Engineer"},
        "idiomas": {"en": "C1"},
    }

    with pytest.raises(ScoreEngineInputError):
        engine.evaluate(
            profile_snapshot=profile,
            program_version=program_version,
            rule_groups=groups,
        )

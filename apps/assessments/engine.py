from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

ALGORITHM_VERSION = "score-engine-v1"

_REQUIRED_PROFILE_FIELDS = ("idade", "escolaridade", "profissao", "idiomas", "renda_atual")

_CEFR_TO_NUMERIC = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}

_IELTS_TO_CEFR_NUMERIC = {
    4.0: 2,
    4.5: 3,
    5.0: 3,
    5.5: 4,
    6.0: 4,
    6.5: 5,
    7.0: 5,
    7.5: 6,
    8.0: 6,
    8.5: 6,
    9.0: 6,
}

_EDUCATION_RANK = {
    "fundamental": 1,
    "ensino_medio": 2,
    "tecnico": 3,
    "bachelor": 4,
    "graduacao": 4,
    "master": 5,
    "phd": 6,
    "doutorado": 6,
}


class ScoreEngineInputError(ValueError):
    pass


@dataclass(frozen=True)
class RuleConditionInput:
    id: UUID
    field_key: str
    operator: str
    value_json: Any
    condition_order: int
    is_required: bool


@dataclass(frozen=True)
class RuleOutcomeInput:
    id: UUID
    score_delta: Decimal
    is_blocking: bool
    explanation_message: str
    outcome_code: str | None


@dataclass(frozen=True)
class RuleGroupInput:
    id: UUID
    code: str
    name: str
    priority: int
    match_operator: str
    conditions: tuple[RuleConditionInput, ...]
    outcomes: tuple[RuleOutcomeInput, ...]


@dataclass(frozen=True)
class ProgramVersionInput:
    id: UUID
    version: str
    effective_from: datetime
    effective_to: datetime | None


@dataclass(frozen=True)
class ScoreBreakdownItem:
    rule_group_id: UUID
    rule_group_code: str
    rule_condition_id: UUID | None
    rule_outcome_id: UUID
    applied: bool
    score_delta: Decimal
    is_blocking: bool
    explanation_message: str
    condition_checks: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ScoreComputationResult:
    algorithm_version: str
    rules_version_hash: str
    score_final: Decimal
    raw_score: Decimal
    faixa: str
    is_blocked: bool
    is_eligible: bool
    fatores_positivos: tuple[str, ...]
    gaps_criticos: tuple[str, ...]
    breakdown: tuple[ScoreBreakdownItem, ...]


class ScoreEngine:
    def __init__(self, algorithm_version: str = ALGORITHM_VERSION) -> None:
        self.algorithm_version = algorithm_version

    def evaluate(
        self,
        *,
        profile_snapshot: dict[str, Any],
        program_version: ProgramVersionInput,
        rule_groups: list[RuleGroupInput],
    ) -> ScoreComputationResult:
        normalized_profile = self._normalize_profile(profile_snapshot)
        sorted_groups = sorted(rule_groups, key=lambda g: (g.priority, g.code, str(g.id)))

        rules_version_hash = self.compute_rules_version_hash(program_version, sorted_groups)

        blocking_items = self._evaluate_blocking_pass(sorted_groups, normalized_profile)
        if blocking_items:
            blocking_messages = tuple(item.explanation_message for item in blocking_items)
            return ScoreComputationResult(
                algorithm_version=self.algorithm_version,
                rules_version_hash=rules_version_hash,
                score_final=Decimal("0.00"),
                raw_score=Decimal("0.00"),
                faixa="baixo",
                is_blocked=True,
                is_eligible=False,
                fatores_positivos=(),
                gaps_criticos=blocking_messages,
                breakdown=tuple(blocking_items),
            )

        scored_items = self._evaluate_scoring_pass(sorted_groups, normalized_profile)
        raw_score = sum((item.score_delta for item in scored_items), Decimal("0.00"))

        normalized_score = self._normalize_score(raw_score, sorted_groups)
        faixa = self._to_faixa(normalized_score)

        positive_factors = tuple(
            item.explanation_message for item in scored_items if item.score_delta > 0
        )
        critical_gaps = tuple(
            item.explanation_message for item in scored_items if item.score_delta < 0
        )

        return ScoreComputationResult(
            algorithm_version=self.algorithm_version,
            rules_version_hash=rules_version_hash,
            score_final=normalized_score,
            raw_score=self._quantize(raw_score),
            faixa=faixa,
            is_blocked=False,
            is_eligible=normalized_score >= Decimal("60.00"),
            fatores_positivos=positive_factors,
            gaps_criticos=critical_gaps,
            breakdown=tuple(scored_items),
        )

    @staticmethod
    def compute_rules_version_hash(
        program_version: ProgramVersionInput,
        rule_groups: list[RuleGroupInput],
    ) -> str:
        payload: dict[str, Any] = {
            "program_version": {
                "id": str(program_version.id),
                "version": program_version.version,
                "effective_from": program_version.effective_from.astimezone(UTC).isoformat(),
                "effective_to": (
                    program_version.effective_to.astimezone(UTC).isoformat()
                    if program_version.effective_to
                    else None
                ),
            },
            "rule_groups": [
                {
                    "id": str(group.id),
                    "code": group.code,
                    "priority": group.priority,
                    "match_operator": group.match_operator,
                    "conditions": [
                        {
                            "id": str(condition.id),
                            "field_key": condition.field_key,
                            "operator": condition.operator,
                            "value_json": condition.value_json,
                            "condition_order": condition.condition_order,
                            "is_required": condition.is_required,
                        }
                        for condition in sorted(
                            group.conditions,
                            key=lambda c: (c.condition_order, c.field_key, str(c.id)),
                        )
                    ],
                    "outcomes": [
                        {
                            "id": str(outcome.id),
                            "score_delta": str(outcome.score_delta),
                            "is_blocking": outcome.is_blocking,
                            "explanation_message": outcome.explanation_message,
                            "outcome_code": outcome.outcome_code,
                        }
                        for outcome in sorted(
                            group.outcomes,
                            key=lambda o: (o.is_blocking, str(o.id)),
                        )
                    ],
                }
                for group in rule_groups
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _evaluate_blocking_pass(
        self,
        rule_groups: list[RuleGroupInput],
        normalized_profile: dict[str, Any],
    ) -> list[ScoreBreakdownItem]:
        blocking_items: list[ScoreBreakdownItem] = []

        for group in rule_groups:
            condition_checks, group_applies = self._evaluate_group_conditions(
                group, normalized_profile
            )
            if not group_applies:
                continue

            for outcome in group.outcomes:
                if not outcome.is_blocking:
                    continue
                blocking_items.append(
                    ScoreBreakdownItem(
                        rule_group_id=group.id,
                        rule_group_code=group.code,
                        rule_condition_id=None,
                        rule_outcome_id=outcome.id,
                        applied=True,
                        score_delta=self._quantize(outcome.score_delta),
                        is_blocking=True,
                        explanation_message=outcome.explanation_message,
                        condition_checks=tuple(condition_checks),
                    )
                )

        return blocking_items

    def _evaluate_scoring_pass(
        self,
        rule_groups: list[RuleGroupInput],
        normalized_profile: dict[str, Any],
    ) -> list[ScoreBreakdownItem]:
        items: list[ScoreBreakdownItem] = []

        for group in rule_groups:
            condition_checks, group_applies = self._evaluate_group_conditions(
                group, normalized_profile
            )

            for outcome in group.outcomes:
                if outcome.is_blocking:
                    continue

                applied = group_applies
                delta = self._quantize(outcome.score_delta if applied else Decimal("0"))

                items.append(
                    ScoreBreakdownItem(
                        rule_group_id=group.id,
                        rule_group_code=group.code,
                        rule_condition_id=None,
                        rule_outcome_id=outcome.id,
                        applied=applied,
                        score_delta=delta,
                        is_blocking=False,
                        explanation_message=outcome.explanation_message,
                        condition_checks=tuple(condition_checks),
                    )
                )

        return items

    def _evaluate_group_conditions(
        self,
        group: RuleGroupInput,
        normalized_profile: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], bool]:
        ordered_conditions = sorted(
            group.conditions,
            key=lambda condition: (
                condition.condition_order,
                condition.field_key,
                str(condition.id),
            ),
        )

        checks: list[dict[str, Any]] = []
        truth_values: list[bool] = []

        for condition in ordered_conditions:
            actual_value = self._resolve_field(normalized_profile, condition.field_key)
            matched = self._evaluate_condition(
                operator=condition.operator,
                actual_value=actual_value,
                expected_value=condition.value_json,
            )
            checks.append(
                {
                    "rule_condition_id": str(condition.id),
                    "field_key": condition.field_key,
                    "operator": condition.operator,
                    "expected": condition.value_json,
                    "actual": actual_value,
                    "matched": matched,
                }
            )
            truth_values.append(matched)

        if not truth_values:
            return checks, True

        if group.match_operator == "any":
            return checks, any(truth_values)
        return checks, all(truth_values)

    def _normalize_profile(self, profile_snapshot: dict[str, Any]) -> dict[str, Any]:
        missing = [field for field in _REQUIRED_PROFILE_FIELDS if field not in profile_snapshot]
        if missing:
            raise ScoreEngineInputError(
                "Missing required profile fields: " + ", ".join(sorted(missing))
            )

        normalized = dict(profile_snapshot)

        normalized["idade"] = int(profile_snapshot["idade"])
        normalized["renda_atual"] = float(profile_snapshot["renda_atual"])

        education = str(profile_snapshot["escolaridade"]).strip().lower()
        normalized["escolaridade"] = education
        normalized["escolaridade_rank"] = _EDUCATION_RANK.get(education, 0)

        profession = profile_snapshot["profissao"]
        if isinstance(profession, dict):
            normalized["profissao_codigo"] = str(profession.get("codigo", "")).strip()
            normalized["profissao_nome"] = str(profession.get("nome", "")).strip()
        else:
            normalized["profissao_codigo"] = str(profession).strip()
            normalized["profissao_nome"] = str(profession).strip()

        normalized["idiomas_nivel"] = self._normalize_languages(profile_snapshot["idiomas"])
        return normalized

    def _normalize_languages(self, languages: Any) -> dict[str, int]:
        if not isinstance(languages, dict):
            raise ScoreEngineInputError("idiomas must be an object keyed by language code")

        normalized: dict[str, int] = {}
        for language, payload in languages.items():
            language_key = str(language).strip().lower()
            normalized[language_key] = self._language_level_to_numeric(payload)
        return normalized

    def _language_level_to_numeric(self, payload: Any) -> int:
        if isinstance(payload, (int, float)):
            return int(payload)

        if isinstance(payload, str):
            level = payload.strip().upper()
            if level in _CEFR_TO_NUMERIC:
                return _CEFR_TO_NUMERIC[level]
            return int(float(level))

        if isinstance(payload, dict):
            framework = str(payload.get("framework", "CEFR")).upper()
            level = payload.get("level")

            if framework == "CEFR":
                level_key = str(level).upper()
                if level_key not in _CEFR_TO_NUMERIC:
                    raise ScoreEngineInputError(f"Invalid CEFR level: {level}")
                return _CEFR_TO_NUMERIC[level_key]

            if framework == "IELTS":
                score = round(float(level), 1)
                if score not in _IELTS_TO_CEFR_NUMERIC:
                    raise ScoreEngineInputError(f"Unsupported IELTS level: {level}")
                return _IELTS_TO_CEFR_NUMERIC[score]

        raise ScoreEngineInputError(f"Unsupported language payload: {payload}")

    def _normalize_score(
        self,
        raw_score: Decimal,
        rule_groups: list[RuleGroupInput],
    ) -> Decimal:
        non_blocking_outcomes: list[Decimal] = [
            Decimal(outcome.score_delta)
            for group in rule_groups
            for outcome in group.outcomes
            if not outcome.is_blocking
        ]

        min_possible = sum(
            (min(delta, Decimal("0")) for delta in non_blocking_outcomes),
            Decimal("0"),
        )
        max_possible = sum(
            (max(delta, Decimal("0")) for delta in non_blocking_outcomes),
            Decimal("0"),
        )

        if max_possible == min_possible:
            return Decimal("100.00") if raw_score > 0 else Decimal("0.00")

        normalized = ((raw_score - min_possible) / (max_possible - min_possible)) * Decimal("100")
        clamped = min(max(normalized, Decimal("0")), Decimal("100"))
        return self._quantize(clamped)

    def _to_faixa(self, score: Decimal) -> str:
        if score < Decimal("40"):
            return "baixo"
        if score < Decimal("70"):
            return "medio"
        return "alto"

    def _resolve_field(self, data: dict[str, Any], path: str) -> Any:
        current: Any = data
        for token in path.split("."):
            if not isinstance(current, dict) or token not in current:
                return None
            current = current[token]
        return current

    def _evaluate_condition(self, *, operator: str, actual_value: Any, expected_value: Any) -> bool:
        if operator == "exists":
            expected = True
            if isinstance(expected_value, bool):
                expected = expected_value
            return (actual_value is not None) is expected

        if operator == "eq":
            return actual_value == expected_value
        if operator == "ne":
            return actual_value != expected_value

        if operator in {"gt", "gte", "lt", "lte"}:
            return self._compare_numeric(operator, actual_value, expected_value)

        if operator == "between":
            return self._is_between(actual_value, expected_value)

        if operator == "in":
            return self._is_in(actual_value, expected_value)

        if operator == "not_in":
            return not self._is_in(actual_value, expected_value)

        raise ScoreEngineInputError(f"Unsupported operator: {operator}")

    def _compare_numeric(self, operator: str, actual_value: Any, expected_value: Any) -> bool:
        if actual_value is None:
            return False
        actual_num = float(actual_value)
        expected_num = float(expected_value)
        comparisons = {
            "gt": actual_num > expected_num,
            "gte": actual_num >= expected_num,
            "lt": actual_num < expected_num,
            "lte": actual_num <= expected_num,
        }
        return comparisons[operator]

    def _is_between(self, actual_value: Any, expected_value: Any) -> bool:
        if actual_value is None:
            return False
        if not isinstance(expected_value, list) or len(expected_value) != 2:
            raise ScoreEngineInputError("between operator expects list with [min, max]")
        lower = float(expected_value[0])
        upper = float(expected_value[1])
        actual_num = float(actual_value)
        return lower <= actual_num <= upper

    def _is_in(self, actual_value: Any, expected_value: Any) -> bool:
        if not isinstance(expected_value, list):
            raise ScoreEngineInputError("in operator expects list")
        if isinstance(actual_value, list):
            return any(item in expected_value for item in actual_value)
        return actual_value in expected_value

    def _quantize(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from html.parser import HTMLParser
from typing import Any

from apps.ingestion.models import ParserMode, SourceRegistry, SourceType
from apps.ingestion.schemas import (
    NormalizedProgramPayload,
    NormalizedRuleCondition,
    NormalizedRuleGroup,
    NormalizedRuleOutcome,
)

logger = logging.getLogger(__name__)

_CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
_INCOME_PATTERN = re.compile(
    r"(minimum|minim[oa]?|at least|>=)\D{0,20}(\d[\d\.,]{2,})",
    flags=re.IGNORECASE,
)
_AGE_PATTERN = re.compile(
    r"(age|idade|edad|years|anos)\D{0,20}([1-9]\d)",
    flags=re.IGNORECASE,
)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._ignore_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignore_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignore_depth > 0:
            self._ignore_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignore_depth > 0:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self._parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._parts)


@dataclass(slots=True)
class ExtractResult:
    payload: NormalizedProgramPayload
    text_content: str


class DeterministicExtractor:
    def __init__(self, *, max_sections: int = 20) -> None:
        self.max_sections = max_sections

    def extract(
        self,
        *,
        source: SourceRegistry,
        content: bytes,
        content_type: str | None,
        title: str,
    ) -> ExtractResult:
        text = self._to_text(
            source_type=source.source_type, content=content, content_type=content_type
        )
        sections = self._to_sections(text)
        groups, signals = self._build_rule_groups(source=source, text=text)

        confidence = Decimal(str(min(0.95, 0.55 + (0.1 * signals))))
        manual_review_required = confidence < Decimal(str(source.confidence_threshold))

        payload = NormalizedProgramPayload(
            country_code=source.country_code,
            country_name=source.country_name,
            program_code=source.program_code,
            program_name=source.program_name,
            source_url=source.source_url,
            source_title=title,
            extracted_at=datetime.now(UTC),
            parser_used=source.parser_name,
            parser_mode=ParserMode.deterministic,
            confidence_score=confidence,
            manual_review_required=manual_review_required,
            summary_text=sections[0]["text_content"][:500] if sections else text[:500],
            metadata_json={"signals_detected": signals, "source_key": source.source_key},
            sections=sections,
            rule_groups=groups,
        )
        return ExtractResult(payload=payload, text_content=text)

    def _to_text(self, *, source_type: SourceType, content: bytes, content_type: str | None) -> str:
        if source_type == SourceType.api or "json" in (content_type or "").lower():
            return self._extract_json_text(content)
        if source_type == SourceType.pdf or "pdf" in (content_type or "").lower():
            return self._extract_pdf_text(content)
        return self._extract_html_text(content)

    def _extract_html_text(self, content: bytes) -> str:
        parser = _HTMLTextExtractor()
        parser.feed(content.decode("utf-8", errors="ignore"))
        text = parser.get_text()
        return text[:100_000]

    def _extract_json_text(self, content: bytes) -> str:
        try:
            payload = json.loads(content.decode("utf-8"))
        except Exception:
            return content.decode("utf-8", errors="ignore")[:100_000]
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)[:100_000]

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
        except Exception:
            return content.decode("latin-1", errors="ignore")[:100_000]

        from io import BytesIO

        reader = PdfReader(BytesIO(content))
        text_parts: list[str] = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)[:100_000]

    def _to_sections(self, text: str) -> list[dict[str, Any]]:
        chunks = [chunk.strip() for chunk in re.split(r"\n{2,}", text) if chunk.strip()]
        if not chunks:
            chunks = [text.strip()] if text.strip() else []

        sections: list[dict[str, Any]] = []
        for idx, chunk in enumerate(chunks[: self.max_sections], start=1):
            heading = chunk.split("\n", 1)[0][:120]
            sections.append(
                {
                    "section_key": f"sec_{idx:03d}",
                    "heading": heading or None,
                    "section_order": idx,
                    "text_content": chunk[:8_000],
                    "metadata_json": {},
                }
            )
        return sections

    def _build_rule_groups(
        self, *, source: SourceRegistry, text: str
    ) -> tuple[list[NormalizedRuleGroup], int]:
        lowered = text.lower()
        groups: list[NormalizedRuleGroup] = []
        signals = 0

        age_match = _AGE_PATTERN.search(lowered)
        if age_match:
            age_value = int(age_match.group(2))
            signals += 1
            groups.append(
                NormalizedRuleGroup(
                    code="age_requirement",
                    name="Age Requirement",
                    description="Extracted age-related threshold from official source.",
                    priority=20,
                    conditions=[
                        NormalizedRuleCondition(
                            field_key="idade",
                            operator="lte",
                            value_json=age_value,
                            condition_order=1,
                            is_required=True,
                        )
                    ],
                    outcomes=[
                        NormalizedRuleOutcome(
                            score_delta=Decimal("15"),
                            explanation_message=f"Age requirement up to {age_value} years matched.",
                            outcome_code="AGE_OK",
                        ),
                        NormalizedRuleOutcome(
                            score_delta=Decimal("-20"),
                            explanation_message=(
                                f"Age above {age_value} years may reduce eligibility."
                            ),
                            outcome_code="AGE_RISK",
                        ),
                    ],
                )
            )

        income_match = _INCOME_PATTERN.search(text)
        if income_match:
            raw_income = income_match.group(2).replace(",", "").replace(".", "")
            minimum_income = max(int(raw_income), 1)
            signals += 1
            groups.append(
                NormalizedRuleGroup(
                    code="income_requirement",
                    name="Minimum Income Requirement",
                    description="Detected minimum income threshold in source text.",
                    priority=30,
                    conditions=[
                        NormalizedRuleCondition(
                            field_key="renda_atual",
                            operator="gte",
                            value_json=minimum_income,
                            condition_order=1,
                            is_required=True,
                        )
                    ],
                    outcomes=[
                        NormalizedRuleOutcome(
                            score_delta=Decimal("20"),
                            explanation_message=(
                                f"Income meets detected threshold ({minimum_income})."
                            ),
                            outcome_code="INCOME_OK",
                        )
                    ],
                )
            )

        language_level = self._extract_language_level(lowered)
        if language_level:
            signals += 1
            groups.append(
                NormalizedRuleGroup(
                    code="language_requirement",
                    name="Language Requirement",
                    description="Detected language level requirement in source.",
                    priority=40,
                    conditions=[
                        NormalizedRuleCondition(
                            field_key="idiomas_nivel.en",
                            operator="gte",
                            value_json=self._cefr_to_rank(language_level),
                            condition_order=1,
                            is_required=False,
                        )
                    ],
                    outcomes=[
                        NormalizedRuleOutcome(
                            score_delta=Decimal("15"),
                            explanation_message=(
                                f"English level >= {language_level} aligned with source."
                            ),
                            outcome_code="LANG_OK",
                        )
                    ],
                )
            )

        # Baseline deterministic rule keeps payload valid even when source has low structure.
        groups.append(
            NormalizedRuleGroup(
                code="baseline_publication_guard",
                name=f"Baseline guard for {source.country_code}",
                description="Safety baseline while parser confidence is evolving.",
                priority=100,
                conditions=[
                    NormalizedRuleCondition(
                        field_key="escolaridade_rank",
                        operator="gte",
                        value_json=0,
                        condition_order=1,
                        is_required=True,
                    )
                ],
                outcomes=[
                    NormalizedRuleOutcome(
                        score_delta=Decimal("5"),
                        explanation_message="Baseline rule extracted deterministically.",
                        outcome_code="BASELINE",
                    )
                ],
            )
        )
        return groups, signals

    def _extract_language_level(self, text: str) -> str | None:
        for level in reversed(_CEFR_LEVELS):
            if level.lower() in text:
                return level
        return None

    def _cefr_to_rank(self, level: str) -> int:
        return _CEFR_LEVELS.index(level) + 1


class LLMFallbackExtractor:
    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        timeout_seconds: int,
        temperature: float,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    def extract(
        self,
        *,
        source: SourceRegistry,
        text_content: str,
        fallback_title: str,
    ) -> NormalizedProgramPayload:
        payload = self._extract_with_provider(
            source=source,
            text_content=text_content,
            fallback_title=fallback_title,
        )
        return payload.model_copy(
            update={
                "parser_mode": ParserMode.llm_fallback,
                "manual_review_required": True,
                "confidence_score": Decimal("0.60"),
            }
        )

    def _extract_with_provider(
        self,
        *,
        source: SourceRegistry,
        text_content: str,
        fallback_title: str,
    ) -> NormalizedProgramPayload:
        if not self.api_key:
            return self._local_stub(source=source, text_content=text_content, title=fallback_title)

        try:
            from openai import OpenAI
        except Exception:
            return self._local_stub(source=source, text_content=text_content, title=fallback_title)

        client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        prompt = (
            "Extraia regra de imigracao em JSON com campos: "
            "country_code, country_name, program_code, program_name, rule_groups[]. "
            "Se ambiguo, retorne manual_review_required=true."
        )
        user_payload = {
            "country_code": source.country_code,
            "country_name": source.country_name,
            "program_code": source.program_code,
            "program_name": source.program_name,
            "source_url": source.source_url,
            "text": text_content[:20_000],
        }
        try:
            completion = client.chat.completions.create(
                model=self.model_name,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
                ],
            )
            content = completion.choices[0].message.content or "{}"
            loaded = json.loads(content)
            loaded.setdefault("country_code", source.country_code)
            loaded.setdefault("country_name", source.country_name)
            loaded.setdefault("program_code", source.program_code)
            loaded.setdefault("program_name", source.program_name)
            loaded.setdefault("source_url", source.source_url)
            loaded.setdefault("source_title", fallback_title)
            loaded.setdefault("sections", [])
            loaded.setdefault("metadata_json", {"llm_provider": "openai"})
            loaded.setdefault("parser_used", "openai-fallback")
            loaded.setdefault("parser_mode", ParserMode.llm_fallback)
            loaded.setdefault("extracted_at", datetime.now(UTC))
            loaded.setdefault("confidence_score", Decimal("0.60"))
            loaded.setdefault("manual_review_required", True)
            return NormalizedProgramPayload.model_validate(loaded)
        except Exception:
            logger.warning("llm_fallback_provider_failed", exc_info=True)
            return self._local_stub(source=source, text_content=text_content, title=fallback_title)

    def _local_stub(
        self,
        *,
        source: SourceRegistry,
        text_content: str,
        title: str,
    ) -> NormalizedProgramPayload:
        return NormalizedProgramPayload(
            country_code=source.country_code,
            country_name=source.country_name,
            program_code=source.program_code,
            program_name=source.program_name,
            source_url=source.source_url,
            source_title=title,
            extracted_at=datetime.now(UTC),
            parser_used="llm-fallback-stub",
            parser_mode=ParserMode.llm_fallback,
            confidence_score=Decimal("0.55"),
            manual_review_required=True,
            summary_text=text_content[:500],
            metadata_json={"reason": "deterministic confidence below threshold"},
            sections=[],
            rule_groups=[
                NormalizedRuleGroup(
                    code="manual_review_gate",
                    name="Manual Review Gate",
                    description="LLM fallback could not safely infer deterministic rule set.",
                    priority=999,
                    conditions=[
                        NormalizedRuleCondition(
                            field_key="escolaridade_rank",
                            operator="gte",
                            value_json=0,
                            condition_order=1,
                            is_required=True,
                        )
                    ],
                    outcomes=[
                        NormalizedRuleOutcome(
                            score_delta=Decimal("0"),
                            is_blocking=False,
                            explanation_message="Manual review required before publication.",
                            outcome_code="MANUAL_REVIEW",
                        )
                    ],
                )
            ],
        )

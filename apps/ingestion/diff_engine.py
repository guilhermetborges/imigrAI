from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from apps.immigration_rules.models import ProgramVersion
from apps.ingestion.schemas import DiffSummary, NormalizedProgramPayload


class DiffEngine:
    def compute_semantic_hash(self, payload: NormalizedProgramPayload) -> str:
        canonical = json.dumps(
            payload.model_dump(mode="json", exclude={"extracted_at"}),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def compare(
        self,
        *,
        payload: NormalizedProgramPayload,
        current_hash: str,
        previous_hash: str | None,
        previous_program_version: ProgramVersion | None,
    ) -> DiffSummary:
        if previous_hash and previous_hash == current_hash:
            return DiffSummary(
                changed=False,
                previous_hash=previous_hash,
                current_hash=current_hash,
                semantic_similarity=1.0,
                notes="No change detected by semantic hash.",
            )

        current_groups = {group.code for group in payload.rule_groups}
        current_conditions = self._condition_signatures_from_payload(payload)

        previous_groups: set[str] = set()
        previous_conditions: set[str] = set()
        if previous_program_version is not None:
            previous_groups = {group.code for group in previous_program_version.rule_groups}
            previous_conditions = self._condition_signatures_from_program_version(
                previous_program_version
            )

        group_intersection = current_groups & previous_groups
        group_union = current_groups | previous_groups
        similarity = (len(group_intersection) / len(group_union)) if group_union else 0.0

        return DiffSummary(
            changed=True,
            previous_hash=previous_hash,
            current_hash=current_hash,
            semantic_similarity=round(similarity, 4),
            added_rule_groups=len(current_groups - previous_groups),
            removed_rule_groups=len(previous_groups - current_groups),
            added_conditions=len(current_conditions - previous_conditions),
            removed_conditions=len(previous_conditions - current_conditions),
            notes=None if previous_program_version else "First published version for this program.",
        )

    def _condition_signatures_from_payload(self, payload: NormalizedProgramPayload) -> set[str]:
        signatures: set[str] = set()
        for group in payload.rule_groups:
            for condition in group.conditions:
                signatures.add(
                    self._signature(
                        (
                            group.code,
                            condition.field_key,
                            str(condition.operator),
                            condition.value_json,
                        )
                    )
                )
        return signatures

    def _condition_signatures_from_program_version(self, version: ProgramVersion) -> set[str]:
        signatures: set[str] = set()
        for group in version.rule_groups:
            for condition in group.conditions:
                signatures.add(
                    self._signature(
                        (
                            group.code,
                            condition.field_key,
                            str(condition.operator.value),
                            condition.value_json,
                        )
                    )
                )
        return signatures

    def _signature(self, value: Iterable[Any]) -> str:
        canonical = json.dumps(tuple(value), sort_keys=True, ensure_ascii=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

import json
from collections.abc import Sequence
from typing import Protocol

from pydantic import ValidationError

from app.core.config import BaseConfig
from apps.roadmaps.schemas import RoadmapContract, RoadmapStepContract


class LLMProviderError(RuntimeError):
    pass


class LLMProviderTimeoutError(LLMProviderError):
    pass


class LLMProviderResponseError(LLMProviderError):
    pass


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    def generate_roadmap(self, input_payload: dict) -> RoadmapContract:
        raise NotImplementedError


class OpenAILLMProvider:
    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        timeout_seconds: int,
        temperature: float,
    ) -> None:
        if not api_key:
            raise LLMProviderError("OPENAI_API_KEY is required when llm_provider=openai")
        self.model_name = model_name
        self.temperature = temperature
        try:
            from openai import APITimeoutError, OpenAI
        except ImportError as exc:  # pragma: no cover - dependency/runtime mismatch
            raise LLMProviderError("openai package is required for OpenAILLMProvider") from exc

        self._timeout_error = APITimeoutError
        self.client = OpenAI(api_key=api_key, timeout=timeout_seconds)

    def generate_roadmap(self, input_payload: dict) -> RoadmapContract:
        system_prompt = (
            "Voce gera roadmaps de imigracao apenas com base no score e gaps informados. "
            "Nao invente exigencias legais. Se informacao for insuficiente, retorne "
            "manual_review_required=true. Responda somente JSON valido."
        )
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(input_payload, ensure_ascii=True, sort_keys=True),
                    },
                ],
            )
        except self._timeout_error as exc:
            raise LLMProviderTimeoutError("OpenAI request timed out") from exc
        except Exception as exc:  # pragma: no cover - provider SDK/network failures
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

        content = completion.choices[0].message.content or "{}"
        try:
            return RoadmapContract.model_validate_json(content)
        except ValidationError as exc:
            raise LLMProviderResponseError(
                f"OpenAI returned invalid roadmap schema: {exc}"
            ) from exc


class ClaudeLLMProviderStub:
    provider_name = "claude_stub"

    def __init__(self, *, model_name: str) -> None:
        self.model_name = model_name

    def generate_roadmap(self, input_payload: dict) -> RoadmapContract:
        gaps: Sequence[str] = input_payload.get("gaps_criticos", []) or []
        objetivo = (
            "Fechar gaps criticos e maximizar score para o programa alvo sem violar requisitos."
        )
        steps: list[RoadmapStepContract] = []
        if gaps:
            for idx, gap in enumerate(gaps, start=1):
                steps.append(
                    RoadmapStepContract(
                        step_order=idx,
                        titulo=f"Mitigar gap {idx}",
                        descricao=f"Atacar gap identificado: {gap}",
                        prazo_estimado_semanas=6,
                        dependencias=[idx - 1] if idx > 1 else [],
                        risco="medio",
                        criterio_conclusao=f"Gap '{gap}' nao aparece no reprocessamento.",
                        gap_relacionado=gap,
                        is_required=True,
                    )
                )
        else:
            steps.append(
                RoadmapStepContract(
                    step_order=1,
                    titulo="Consolidar elegibilidade",
                    descricao="Manter perfil atual e organizar evidencias para aplicacao.",
                    prazo_estimado_semanas=4,
                    dependencias=[],
                    risco="baixo",
                    criterio_conclusao="Checklist documental completo.",
                    gap_relacionado=None,
                    is_required=True,
                )
            )

        return RoadmapContract(
            roadmap_schema_version=input_payload.get("roadmap_schema_version", ""),
            objetivo=objetivo,
            manual_review_required=True,
            passos_priorizados=steps,
        )


def build_llm_provider(settings: BaseConfig) -> LLMProvider:
    if settings.llm_provider == "claude":
        return ClaudeLLMProviderStub(model_name=settings.anthropic_model)
    return OpenAILLMProvider(
        api_key=settings.openai_api_key,
        model_name=settings.openai_model,
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
    )

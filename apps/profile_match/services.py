from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.accounts.models import User
from apps.profile_match.repositories import ProfileMatchRepository
from apps.profile_match.schemas import (
    CountryMatchRead,
    ProfileMatchClaimRequest,
    ProfileMatchResultRead,
    ProfileMatchSubmitRead,
    ProfileMatchSubmitRequest,
)

SUBMISSION_NOT_FOUND = "Submission not found"


@dataclass(frozen=True)
class CountryRule:
    code: str
    name: str
    region: str
    language_mode: str
    min_funds_brl: float
    preferred_professions: set[str]
    job_offer_factor: float
    family_factor: float
    citizenship_speed: str
    base_boost: float = 0.0


CEFR_SCORES: dict[str, float] = {
    "A1": 0.20,
    "A2": 0.35,
    "B1": 0.55,
    "B2": 0.70,
    "C1": 0.85,
    "C2": 1.00,
}

EDUCATION_SCORES: dict[str, float] = {
    "ensino_medio": 0.45,
    "tecnico": 0.58,
    "graduacao": 0.72,
    "mestrado": 0.86,
    "doutorado": 1.00,
}

COUNTRY_RULES: tuple[CountryRule, ...] = (
    CountryRule(
        "US",
        "Estados Unidos",
        "americas",
        "english",
        130_000,
        {"tecnologia", "engenharia", "saude", "negocios"},
        1.30,
        1.10,
        "regular",
        0.01,
    ),
    CountryRule(
        "CA",
        "Canada",
        "americas",
        "hybrid",
        90_000,
        {"tecnologia", "engenharia", "saude", "educacao"},
        1.20,
        1.15,
        "regular",
        0.03,
    ),
    CountryRule(
        "GB",
        "Reino Unido",
        "europa",
        "english",
        95_000,
        {"tecnologia", "engenharia", "saude", "negocios"},
        1.20,
        1.05,
        "regular",
        0.00,
    ),
    CountryRule(
        "IE",
        "Irlanda",
        "europa",
        "english",
        80_000,
        {"tecnologia", "engenharia", "saude", "educacao"},
        1.15,
        1.00,
        "regular",
        0.01,
    ),
    CountryRule(
        "PT",
        "Portugal",
        "europa",
        "local",
        55_000,
        {"tecnologia", "engenharia", "servicos", "negocios"},
        1.05,
        1.15,
        "fast",
        0.05,
    ),
    CountryRule(
        "DE",
        "Alemanha",
        "europa",
        "local",
        85_000,
        {"engenharia", "tecnologia", "saude", "educacao"},
        1.20,
        1.00,
        "regular",
        0.01,
    ),
    CountryRule(
        "FR",
        "Franca",
        "europa",
        "french",
        75_000,
        {"engenharia", "saude", "negocios", "educacao"},
        1.10,
        1.05,
        "regular",
        0.00,
    ),
    CountryRule(
        "ES",
        "Espanha",
        "europa",
        "local",
        60_000,
        {"servicos", "negocios", "tecnologia", "engenharia"},
        1.05,
        1.10,
        "regular",
        0.02,
    ),
    CountryRule(
        "IT",
        "Italia",
        "europa",
        "local",
        62_000,
        {"servicos", "negocios", "engenharia", "educacao"},
        1.00,
        1.05,
        "regular",
        0.00,
    ),
    CountryRule(
        "NL",
        "Paises Baixos",
        "europa",
        "english",
        88_000,
        {"tecnologia", "engenharia", "negocios", "educacao"},
        1.15,
        1.00,
        "regular",
        0.01,
    ),
    CountryRule(
        "CH",
        "Suica",
        "europa",
        "hybrid",
        120_000,
        {"engenharia", "saude", "tecnologia", "negocios"},
        1.25,
        1.00,
        "regular",
        -0.01,
    ),
    CountryRule(
        "BE",
        "Belgica",
        "europa",
        "hybrid",
        78_000,
        {"engenharia", "tecnologia", "saude", "negocios"},
        1.10,
        1.05,
        "regular",
        0.00,
    ),
    CountryRule(
        "JP",
        "Japao",
        "asia",
        "local",
        100_000,
        {"tecnologia", "engenharia", "educacao", "negocios"},
        1.15,
        0.95,
        "regular",
        -0.01,
    ),
    CountryRule(
        "AR",
        "Argentina",
        "americas",
        "local",
        45_000,
        {"negocios", "servicos", "educacao", "tecnologia"},
        0.95,
        1.10,
        "fast",
        0.03,
    ),
    CountryRule(
        "PY",
        "Paraguai",
        "americas",
        "local",
        40_000,
        {"negocios", "servicos", "engenharia", "educacao"},
        0.95,
        1.10,
        "fast",
        0.04,
    ),
)


class ProfileMatchService:
    algorithm_version = "country-fit-v1"

    def __init__(self, db: AsyncSession) -> None:
        self.repo = ProfileMatchRepository(db)

    async def submit_profile(
        self,
        *,
        payload: ProfileMatchSubmitRequest,
        current_user: User | None,
    ) -> ProfileMatchSubmitRead:
        matches = self._rank_profile(payload)
        profile_snapshot = payload.model_dump(mode="json", exclude={"guest_session_id"})
        result_json = [match.model_dump(mode="json") for match in matches]

        submission = await self.repo.create_submission(
            user_id=current_user.id if current_user is not None else None,
            guest_session_id=payload.guest_session_id,
            algorithm_version=self.algorithm_version,
            profile_json=profile_snapshot,
            result_json=result_json,
        )
        await self.repo.commit()
        await self.repo.refresh(submission)

        full_result = self._to_result_read(submission)
        requires_login = current_user is None
        return ProfileMatchSubmitRead(
            submission_id=submission.id,
            requires_login=requires_login,
            result=None if requires_login else full_result,
        )

    async def claim_submission(
        self,
        *,
        payload: ProfileMatchClaimRequest,
        user: User,
    ) -> ProfileMatchResultRead:
        submission = await self.repo.get_submission(payload.submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUBMISSION_NOT_FOUND)

        if submission.user_id is None:
            if submission.guest_session_id != payload.guest_session_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Submission does not belong to this browser session",
                )
            await self.repo.claim_submission(submission, user.id)
            await self.repo.commit()
            await self.repo.refresh(submission)
        elif submission.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUBMISSION_NOT_FOUND)

        return self._to_result_read(submission)

    async def get_results(self, *, submission_id: UUID, user: User) -> ProfileMatchResultRead:
        submission = await self.repo.get_submission(submission_id)
        if submission is None or submission.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUBMISSION_NOT_FOUND)
        return self._to_result_read(submission)

    def _to_result_read(self, submission) -> ProfileMatchResultRead:
        matches = [CountryMatchRead.model_validate(item) for item in submission.result_json]
        return ProfileMatchResultRead(
            submission_id=submission.id,
            algorithm_version=submission.algorithm_version,
            created_at=submission.created_at,
            profile_snapshot=submission.profile_json,
            matches=matches,
        )

    def _rank_profile(self, payload: ProfileMatchSubmitRequest) -> list[CountryMatchRead]:
        age_feature = self._age_score(payload.age)
        education_feature = EDUCATION_SCORES[payload.education_level]
        experience_feature = self._clamp(payload.experience_years / 10.0)
        english_feature = CEFR_SCORES[payload.english_level]
        french_feature = CEFR_SCORES[payload.french_level]
        funds_pool = payload.savings_brl + (payload.monthly_income_brl * 8)

        matches: list[CountryMatchRead] = []
        for rule in COUNTRY_RULES:
            language_feature = self._language_score(
                rule=rule,
                english_feature=english_feature,
                french_feature=french_feature,
                willing_to_learn_language=payload.willing_to_learn_language,
            )
            funds_feature = self._clamp(funds_pool / rule.min_funds_brl)
            profession_feature = self._profession_score(rule, payload.profession_area)
            region_feature = (
                1.0 if payload.preferred_region in {"indiferente", rule.region} else 0.40
            )
            fast_citizenship_feature = self._citizenship_score(
                wants_fast=payload.wants_fast_citizenship,
                country_speed=rule.citizenship_speed,
            )
            job_offer_feature = 1.0 if payload.has_job_offer else 0.20
            family_feature = 1.0 if payload.has_family_abroad else 0.35

            weighted_score = (
                (age_feature * 0.11)
                + (education_feature * 0.11)
                + (experience_feature * 0.15)
                + (language_feature * 0.19)
                + (funds_feature * 0.15)
                + (profession_feature * 0.12)
                + (region_feature * 0.06)
                + (fast_citizenship_feature * 0.06)
                + (job_offer_feature * 0.03 * rule.job_offer_factor)
                + (family_feature * 0.02 * rule.family_factor)
                + rule.base_boost
            )
            match_score = round(self._clamp(weighted_score, lower=0.0, upper=0.995) * 100, 2)

            highlights = self._build_highlights(
                rule=rule,
                language_feature=language_feature,
                funds_feature=funds_feature,
                profession_feature=profession_feature,
                has_job_offer=payload.has_job_offer,
                has_family_abroad=payload.has_family_abroad,
            )
            matches.append(
                CountryMatchRead(
                    country_code=rule.code,
                    country_name=rule.name,
                    match_score=match_score,
                    highlights=highlights,
                )
            )

        matches.sort(key=lambda item: item.match_score, reverse=True)
        return matches

    def _age_score(self, age: int) -> float:
        if 22 <= age <= 34:
            return 1.0
        if 18 <= age <= 40:
            return 0.82
        if 41 <= age <= 50:
            return 0.62
        return 0.45

    def _language_score(
        self,
        *,
        rule: CountryRule,
        english_feature: float,
        french_feature: float,
        willing_to_learn_language: bool,
    ) -> float:
        if rule.language_mode == "english":
            return english_feature
        if rule.language_mode == "french":
            return self._clamp(max(french_feature, english_feature * 0.45))
        if rule.language_mode == "hybrid":
            return self._clamp(max(english_feature * 0.80, french_feature * 0.80))

        local_score = 0.25 + (english_feature * 0.35)
        if willing_to_learn_language:
            local_score += 0.25
        if rule.code in {"CH", "BE"} and french_feature >= 0.70:
            local_score += 0.10
        return self._clamp(local_score)

    def _profession_score(self, rule: CountryRule, profession_area: str) -> float:
        if profession_area in rule.preferred_professions:
            return 1.0
        if profession_area in {"tecnologia", "engenharia", "saude"}:
            return 0.70
        return 0.52

    def _citizenship_score(self, *, wants_fast: bool, country_speed: str) -> float:
        if wants_fast:
            return 1.0 if country_speed == "fast" else 0.55
        return 0.80 if country_speed == "fast" else 0.75

    def _build_highlights(
        self,
        *,
        rule: CountryRule,
        language_feature: float,
        funds_feature: float,
        profession_feature: float,
        has_job_offer: bool,
        has_family_abroad: bool,
    ) -> list[str]:
        highlights: list[str] = []
        if language_feature >= 0.75:
            highlights.append("Seu idioma atual ja atende boa parte das trilhas desse pais.")
        elif rule.language_mode == "local":
            highlights.append("Com plano de idioma local, seu perfil ganha tracao nesse destino.")

        if profession_feature >= 0.95:
            highlights.append("Sua area profissional esta entre as mais demandadas nesse mercado.")

        if funds_feature >= 0.80:
            highlights.append(
                "Sua reserva financeira esta proxima do patamar esperado para entrada."
            )
        else:
            highlights.append(
                "Aumentar reserva financeira melhora muito a elegibilidade nesse pais."
            )

        if has_job_offer and rule.job_offer_factor >= 1.10:
            highlights.append("Oferta de trabalho tem impacto relevante para acelerar o processo.")
        elif has_family_abroad and rule.family_factor >= 1.05:
            highlights.append("Rede familiar pode facilitar caminhos de adaptacao e comprovacao.")

        while len(highlights) < 3:
            highlights.append(
                "Seu score depende de consistencia documental e estrategia de aplicacao."
            )
        return highlights[:3]

    def _clamp(self, value: float, *, lower: float = 0.0, upper: float = 1.0) -> float:
        return max(lower, min(upper, value))

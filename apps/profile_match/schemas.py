from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CEFRLevels = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
EducationLevels = Literal["ensino_medio", "tecnico", "graduacao", "mestrado", "doutorado"]
ProfessionAreas = Literal[
    "tecnologia",
    "engenharia",
    "saude",
    "negocios",
    "educacao",
    "servicos",
    "outros",
]
PreferredRegions = Literal["americas", "europa", "asia", "indiferente"]


class ProfileMatchSubmitRequest(BaseModel):
    age: int = Field(ge=18, le=70)
    education_level: EducationLevels
    experience_years: int = Field(ge=0, le=45)
    english_level: CEFRLevels
    french_level: CEFRLevels
    savings_brl: float = Field(ge=0, le=10_000_000)
    monthly_income_brl: float = Field(ge=0, le=1_000_000)
    profession_area: ProfessionAreas
    has_job_offer: bool = False
    has_family_abroad: bool = False
    willing_to_learn_language: bool = True
    wants_fast_citizenship: bool = False
    preferred_region: PreferredRegions = "indiferente"
    guest_session_id: str = Field(min_length=8, max_length=64)


class CountryMatchRead(BaseModel):
    country_code: str
    country_name: str
    match_score: float
    highlights: list[str]


class ProfileMatchResultRead(BaseModel):
    submission_id: UUID
    algorithm_version: str
    created_at: datetime
    profile_snapshot: dict
    matches: list[CountryMatchRead]


class ProfileMatchSubmitRead(BaseModel):
    submission_id: UUID
    requires_login: bool
    result: ProfileMatchResultRead | None = None


class ProfileMatchClaimRequest(BaseModel):
    submission_id: UUID
    guest_session_id: str = Field(min_length=8, max_length=64)


class ProfileMatchSubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    guest_session_id: str
    algorithm_version: str
    profile_json: dict
    result_json: list[dict]
    created_at: datetime
    claimed_at: datetime | None

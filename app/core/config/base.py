from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["dev", "staging", "prod"] = "dev"
    app_name: str = "imigrai-api"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    timezone: str = "UTC"

    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://imigrai:imigrai@postgres:5432/imigrai"
    alembic_database_url: str = "postgresql+psycopg://imigrai:imigrai@postgres:5432/imigrai"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout_seconds: int = 30
    redis_url: str = "redis://redis:6379/0"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    score_task_max_retries: int = 3
    score_task_soft_time_limit_seconds: int = 25
    score_task_time_limit_seconds: int = 35
    roadmap_task_max_retries: int = 3
    roadmap_task_soft_time_limit_seconds: int = 90
    roadmap_task_time_limit_seconds: int = 120
    ingestion_task_max_retries: int = 3
    ingestion_task_soft_time_limit_seconds: int = 120
    ingestion_task_time_limit_seconds: int = 180
    ingestion_retry_backoff_base_seconds: int = 2

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7
    score_algorithm_version: str = "score-engine-v1"
    roadmap_schema_version: str = "roadmap.v1"

    llm_provider: Literal["openai", "claude"] = "openai"
    llm_timeout_seconds: int = 45
    llm_temperature: float = 0.1
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-latest"
    pro_roadmap_feature_key: str = "roadmap.pro"
    assessment_feature_key: str = "assessments.monthly"
    processing_priority_feature_key: str = "processing.priority"
    history_extended_feature_key: str = "history.extended"
    country_comparison_feature_key: str = "countries.comparison"

    free_assessment_monthly_limit: int = 3
    pro_plan_code: str = "pro"
    free_plan_code: str = "free"
    pro_plan_name: str = "Pro Monthly"
    free_plan_name: str = "Free"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_pro_price_id: str | None = None
    supabase_project_url: str | None = None
    supabase_service_role_key: str | None = None

    ingestion_internal_token: str | None = None
    ingestion_user_agent: str = "imigrAI-ingestion-bot/1.0"
    ingestion_fetch_timeout_seconds: int = 40
    ingestion_enforce_robots: bool = True
    ingestion_bronze_bucket: str = "immigration-bronze"
    ingestion_local_fallback_dir: str = ".cache/ingestion"
    ingestion_gateway_max_retries: int = 3
    ingestion_gateway_base_backoff_seconds: float = 0.5
    ingestion_quarantine_after_failures: int = 3
    ingestion_quarantine_hours: int = 24

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> BaseConfig:
    from app.core.config.dev import DevConfig
    from app.core.config.prod import ProdConfig

    env = BaseConfig().app_env
    if env == "prod":
        return ProdConfig()
    if env == "staging":
        return ProdConfig(app_env="staging")
    return DevConfig()

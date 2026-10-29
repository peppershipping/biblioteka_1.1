
"""Configuration settings loaded from environment variables."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    docs_enabled: bool = True

    database_url: str = (
        "postgresql+psycopg://biblioteka:biblioteka@localhost:5432/biblioteka"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20

    jwt_secret_key: str = INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:5173"

    rate_limit_enabled: bool = True
    rate_limit_default: int = 100
    rate_limit_auth: int = 10

    redis_url: str | None = None
    cache_catalog_ttl: int = 300
    cache_recommendations_ttl: int = 3600

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout: float = 8.0
    openai_retries: int = 1

    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    seed_demo_data: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip() and origin.strip() != "*"
        ]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @model_validator(mode="after")
    def _forbid_default_secret_in_production(self) -> "Settings":
        if (
            self.app_env == "production"
            and self.jwt_secret_key == INSECURE_DEFAULT_SECRET
        ):
            raise ValueError(
                "Set a custom JWT_SECRET_KEY in production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

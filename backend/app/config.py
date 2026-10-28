"""
Конфигурация приложения. Все значения читаются из переменных окружения
<<<<<<< HEAD
(см. backend/.env.example) — секреты не хранятся в коде и не коммитятся.
=======
(см. .env.example) — так один и тот же образ работает и в docker-compose,
и локально, без правки кода.
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
"""

from functools import lru_cache

<<<<<<< HEAD
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "dev-insecure-secret-change-me"

=======
from pydantic_settings import BaseSettings, SettingsConfigDict

>>>>>>> 088ebc434e4e609566051a7126e169906afacece

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

<<<<<<< HEAD
    app_env: str = "development"
    log_level: str = "INFO"
    docs_enabled: bool = True

    database_url: str = "postgresql+psycopg://biblioteka:biblioteka@localhost:5432/biblioteka"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # --- токены (ТЗ 15.2: access 15 минут, refresh 7 дней) ---
    jwt_secret_key: str = INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:5173"

    # --- rate limiting (ТЗ 15.3: ~100 запросов/мин на IP, строже для login/register) ---
    rate_limit_enabled: bool = True
    rate_limit_default: int = 100
    rate_limit_auth: int = 10

    # --- кэш (ТЗ 15.4); без REDIS_URL кэш выключен ---
    redis_url: str | None = None
    cache_catalog_ttl: int = 300
    cache_recommendations_ttl: int = 3600

    # --- внешняя языковая модель (Chat Completions-совместимый API) ---
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout: float = 8.0
    openai_retries: int = 1

    # --- начальные данные ---
    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    seed_demo_data: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip() and o.strip() != "*"]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @model_validator(mode="after")
    def _forbid_default_secret_in_production(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret_key == INSECURE_DEFAULT_SECRET:
            raise ValueError("В production необходимо задать собственный JWT_SECRET_KEY")
        return self
=======
    database_url: str = "postgresql+psycopg://biblioteka:biblioteka@localhost:5432/biblioteka"

    jwt_secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
>>>>>>> 088ebc434e4e609566051a7126e169906afacece


@lru_cache
def get_settings() -> Settings:
    return Settings()

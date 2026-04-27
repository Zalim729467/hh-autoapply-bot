"""Application configuration loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str
    ADMIN_TG_ID: int

    # DB / Redis
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    # Crypto
    COOKIES_ENC_KEY: str = ""
    BACKUP_GPG_PASSPHRASE: str = ""

    # AI (used from stage 7+)
    AI_PROVIDER: str = "openrouter"
    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    AI_MODEL: str = "openai/gpt-4o-mini"

    # Misc
    DEFAULT_TZ: str = "Europe/Moscow"
    DAILY_LIMIT_DEFAULT: int = 200
    DELAY_MIN_SEC: int = 5
    DELAY_MAX_SEC: int = 25
    LOG_LEVEL: str = "INFO"

    # Rate limit (per Telegram user)
    RATE_LIMIT_PER_SEC: float = 1.0

    @property
    def alembic_database_url(self) -> str:
        """Alembic uses sync driver (psycopg2)."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

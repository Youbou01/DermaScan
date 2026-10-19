"""Application settings.

Every secret and every environment-dependent value comes from environment
variables (or a local, git-ignored `.env` file). Missing or malformed values
fail fast at startup instead of at the first request.
"""

from datetime import date
from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # .env also holds POSTGRES_* values that only docker compose reads.
        extra="ignore",
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    database_url: PostgresDsn
    db_echo: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Freeze the home-feed "Top rated" daily rotation (YYYY-MM-DD). Empty = real UTC today.
    home_feed_date: date | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

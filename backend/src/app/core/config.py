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
    enable_obf_fallback: bool = True
    # Freeze the home-feed "Top rated" daily rotation (YYYY-MM-DD). Empty = real UTC today.
    home_feed_date: date | None = None

    # --- LLM Gateway ---
    llm_providers: str = "ollama,gemini,groq"
    llm_chain_enrich: str = "ollama,gemini"
    llm_chain_rate: str = "gemini,groq,ollama"
    llm_chain_vision: str = "gemini,ollama"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_vision_model: str = "llava:7b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    gemini_daily_request_cap: int = 1500
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    groq_daily_request_cap: int = 14400
    llm_min_confidence: float = 0.6
    llm_max_retries: int = 2

    # --- Storage / CDN ---
    s3_endpoint_url: str | None = None
    s3_bucket: str = "dermascan"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    image_cdn_base_url: str = "http://localhost:9000/dermascan"

    # --- Admin ---
    admin_api_key: str | None = None
    admin_ui_user: str | None = None
    admin_ui_password: str | None = None

    # --- Scraping ---
    scraper_respect_robots: bool = False
    scraper_proxy_list: str | None = None
    scraper_user_agents: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

import json
from typing import TypeVar

import structlog
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.modules.enrichment.llm.cache import (
    compute_cache_key,
    get_cached_response,
    save_cached_response,
)
from app.modules.enrichment.llm.client import (
    LLMChainExhaustedError,
    LLMClient,
    LLMError,
    LLMQuotaExhaustedError,
    LLMRateLimitError,
    LLMResult,
)
from app.modules.enrichment.llm.fake import FakeLLMClient
from app.modules.enrichment.llm.gemini import GeminiClient
from app.modules.enrichment.llm.openai_compat import OpenAICompatClient
from app.modules.enrichment.llm.ratelimit import (
    RateLimiterRegistry,
    check_daily_cap,
    increment_usage,
)

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class LLMRouter:
    def __init__(
        self,
        settings: Settings | None = None,
        clients: dict[str, LLMClient] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.clients: dict[str, LLMClient] = dict(clients or {})

    def get_client(self, provider: str) -> LLMClient:
        if provider in self.clients:
            return self.clients[provider]

        client: LLMClient
        # In test mode or when no API key / local server configured, default to fake
        if self.settings.app_env == "test":
            client = FakeLLMClient(provider=provider, model="fake-test")
            self.clients[provider] = client
            return client

        if provider == "ollama":
            client = OpenAICompatClient(
                provider="ollama",
                model=self.settings.ollama_model,
                base_url=self.settings.ollama_base_url,
            )
        elif provider == "groq":
            client = OpenAICompatClient(
                provider="groq",
                model=self.settings.groq_model,
                base_url="https://api.groq.com/openai/v1",
                api_key=self.settings.groq_api_key,
            )
        elif provider == "gemini":
            client = GeminiClient(
                api_key=self.settings.gemini_api_key or "",
                model=self.settings.gemini_model,
            )
        else:
            client = FakeLLMClient(provider=provider, model="fallback-fake")

        self.clients[provider] = client
        return client

    def get_chain(self, task: str) -> list[str]:
        if task == "enrich":
            raw = self.settings.llm_chain_enrich
        elif task == "rate":
            raw = self.settings.llm_chain_rate
        elif task == "vision":
            raw = self.settings.llm_chain_vision
        else:
            raw = self.settings.llm_providers
        return [p.strip() for p in raw.split(",") if p.strip()]

    def _get_daily_cap(self, provider: str) -> int | None:
        if provider == "gemini":
            return self.settings.gemini_daily_request_cap
        if provider == "groq":
            return self.settings.groq_daily_request_cap
        return None

    async def generate_json(
        self,
        session: AsyncSession,
        task: str,
        system: str,
        prompt: str,
        schema: type[T],
        prompt_version: int = 1,
        schema_version: int = 1,
        images: list[str] | None = None,
        provider_chain: list[str] | None = None,
        bypass_cache: bool = False,
    ) -> tuple[T, LLMResult]:
        """Generate validated JSON with cache, rate limits, provider fallthrough and repair."""
        cache_key = compute_cache_key(task, prompt_version, schema_version, prompt)

        if not bypass_cache:
            cached_data = await get_cached_response(session, cache_key)
            if cached_data is not None:
                try:
                    validated = schema.model_validate(cached_data)
                    result = LLMResult(
                        content=json.dumps(cached_data),
                        parsed=cached_data,
                        provider="cache",
                        model="cache",
                        tokens_used=0,
                        cached=True,
                        latency_ms=0.0,
                    )
                    return validated, result
                except ValidationError:
                    logger.warning("stale_invalid_cached_json_ignored", cache_key=cache_key)

        chain = provider_chain or self.get_chain(task)
        schema_dict = schema.model_json_schema()
        last_error: Exception | None = None

        for provider in chain:
            try:
                # 1. Check daily quota in DB
                daily_cap = self._get_daily_cap(provider)
                await check_daily_cap(session, provider, daily_cap)

                # 2. Check token bucket rate limit
                RateLimiterRegistry.check_rate_limit(provider)
            except (LLMQuotaExhaustedError, LLMRateLimitError) as exc:
                logger.warning(
                    "provider_rate_limited_or_capped",
                    provider=provider,
                    task=task,
                    error=str(exc),
                )
                last_error = exc
                continue

            client = self.get_client(provider)
            current_prompt = prompt
            repair_attempts = 0
            max_retries = self.settings.llm_max_retries

            while repair_attempts <= max_retries:
                try:
                    res = await client.generate(
                        system=system,
                        prompt=current_prompt,
                        schema=schema_dict,
                        images=images,
                    )
                except LLMRateLimitError as exc:
                    logger.warning("provider_429_fallthrough", provider=provider, error=str(exc))
                    last_error = exc
                    break
                except LLMError as exc:
                    logger.warning("provider_error_retry", provider=provider, error=str(exc))
                    last_error = exc
                    repair_attempts += 1
                    current_prompt = (
                        f"{prompt}\n\nYour previous response encountered an error. "
                        f"Output only valid JSON satisfying the schema."
                    )
                    continue

                if res.parsed is None:
                    repair_attempts += 1
                    logger.info(
                        "repairing_unparseable_json",
                        provider=provider,
                        attempt=repair_attempts,
                    )
                    current_prompt = (
                        f"{prompt}\n\nYour response was not valid JSON. "
                        f"Return ONLY a valid JSON object matching the schema."
                    )
                    continue

                try:
                    validated = schema.model_validate(res.parsed)
                    # Success: record cache and usage
                    await save_cached_response(
                        session=session,
                        key=cache_key,
                        provider=provider,
                        model=res.model,
                        response_json=res.parsed,
                    )
                    await increment_usage(
                        session=session,
                        provider=provider,
                        tokens=res.tokens_used,
                    )
                    return validated, res
                except ValidationError as err:
                    repair_attempts += 1
                    logger.info(
                        "repairing_schema_validation_error",
                        provider=provider,
                        attempt=repair_attempts,
                        error=str(err),
                    )
                    current_prompt = (
                        f"{prompt}\n\nYour JSON was invalid: {err}. "
                        f"Correct the fields and return ONLY valid JSON matching the schema."
                    )

        raise LLMChainExhaustedError(
            f"All providers in chain {chain} exhausted for task '{task}'. Last error: {last_error}"
        )

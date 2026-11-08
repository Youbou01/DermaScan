from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.enrichment.llm.client import (
    LLMChainExhaustedError,
    LLMRateLimitError,
)
from app.modules.enrichment.llm.fake import FakeLLMClient
from app.modules.enrichment.llm.router import LLMRouter
from app.modules.enrichment.models import LLMUsage


class SampleSchema(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=10.0)


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://skincare:test@localhost:5432/skincare_test",
        llm_providers="fake1,fake2",
        llm_chain_enrich="fake1,fake2",
        llm_max_retries=2,
    )


async def test_llm_cache_hit_returns_cached_result(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    fake1 = FakeLLMClient(provider="fake1", default_response={"name": "Water", "score": 10.0})
    router = LLMRouter(settings=test_settings, clients={"fake1": fake1})

    # First call: cache miss, saves to DB
    val1, res1 = await router.generate_json(
        session=db_session,
        task="test_task",
        system="sys",
        prompt="rate water",
        schema=SampleSchema,
    )
    assert val1.name == "Water"
    assert res1.cached is False
    assert len(fake1.calls) == 1

    # Second call: cache hit
    val2, res2 = await router.generate_json(
        session=db_session,
        task="test_task",
        system="sys",
        prompt="rate water",
        schema=SampleSchema,
    )
    assert val2.name == "Water"
    assert res2.cached is True
    assert len(fake1.calls) == 1  # No additional call made


async def test_repair_retry_on_invalid_json(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    # First response is malformed raw text, second is valid JSON
    fake = FakeLLMClient(
        provider="fake1",
        responses=[
            "This is definitely not JSON",
            {"name": "Glycerin", "score": 9.5},
        ],
    )
    router = LLMRouter(settings=test_settings, clients={"fake1": fake})

    val, _res = await router.generate_json(
        session=db_session,
        task="test_repair",
        system="sys",
        prompt="rate glycerin",
        schema=SampleSchema,
    )
    assert val.name == "Glycerin"
    assert val.score == 9.5
    assert len(fake.calls) == 2
    assert "not valid JSON" in fake.calls[1]["prompt"]


async def test_repair_retry_on_schema_validation_error(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    # First response fails score <= 10.0 constraint, second fixes it
    fake = FakeLLMClient(
        provider="fake1",
        responses=[
            {"name": "Alcohol", "score": 99.0},  # Invalid score > 10
            {"name": "Alcohol", "score": 5.0},
        ],
    )
    router = LLMRouter(settings=test_settings, clients={"fake1": fake})

    val, _res = await router.generate_json(
        session=db_session,
        task="test_schema_repair",
        system="sys",
        prompt="rate alcohol",
        schema=SampleSchema,
    )
    assert val.name == "Alcohol"
    assert val.score == 5.0
    assert len(fake.calls) == 2
    assert "Your JSON was invalid" in fake.calls[1]["prompt"]


async def test_provider_fallthrough_on_429_rate_limit(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    fake1 = FakeLLMClient(provider="fake1", responses=[LLMRateLimitError("HTTP 429")])
    fake2 = FakeLLMClient(provider="fake2", default_response={"name": "Niacinamide", "score": 8.5})
    router = LLMRouter(settings=test_settings, clients={"fake1": fake1, "fake2": fake2})

    val, res = await router.generate_json(
        session=db_session,
        task="test_fallthrough",
        system="sys",
        prompt="rate niacinamide",
        schema=SampleSchema,
        provider_chain=["fake1", "fake2"],
    )
    assert val.name == "Niacinamide"
    assert res.provider == "fake2"
    assert len(fake1.calls) == 1
    assert len(fake2.calls) == 1


async def test_daily_cap_exhaustion_skips_provider(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    # Mark fake1 as having reached cap
    today = datetime.now(UTC).date()
    db_session.add(LLMUsage(provider="fake1", date=today, requests=100, tokens=5000))
    await db_session.flush()

    fake1 = FakeLLMClient(provider="fake1", default_response={"name": "Bad", "score": 1.0})
    fake2 = FakeLLMClient(provider="fake2", default_response={"name": "Good", "score": 9.0})

    router = LLMRouter(settings=test_settings, clients={"fake1": fake1, "fake2": fake2})
    # Set cap on fake1
    router._get_daily_cap = lambda p: 50 if p == "fake1" else None  # type: ignore[assignment]

    val, res = await router.generate_json(
        session=db_session,
        task="test_cap",
        system="sys",
        prompt="rate product",
        schema=SampleSchema,
        provider_chain=["fake1", "fake2"],
    )
    assert val.name == "Good"
    assert res.provider == "fake2"
    assert len(fake1.calls) == 0  # fake1 was skipped completely due to daily cap


async def test_chain_exhausted_raises_error(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    fake1 = FakeLLMClient(provider="fake1", responses=[LLMRateLimitError("429")])
    fake2 = FakeLLMClient(provider="fake2", responses=[LLMRateLimitError("429")])
    router = LLMRouter(settings=test_settings, clients={"fake1": fake1, "fake2": fake2})

    with pytest.raises(LLMChainExhaustedError):
        await router.generate_json(
            session=db_session,
            task="test_exhausted",
            system="sys",
            prompt="fail",
            schema=SampleSchema,
            provider_chain=["fake1", "fake2"],
        )

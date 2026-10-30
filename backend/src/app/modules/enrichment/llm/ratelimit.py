import time
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrichment.llm.client import LLMQuotaExhaustedError, LLMRateLimitError
from app.modules.enrichment.models import LLMUsage


class InMemoryTokenBucket:
    """In-memory rate limiter for requests per minute (RPM)."""

    def __init__(self, rpm: int = 60) -> None:
        self.capacity: float = float(rpm)
        self.tokens: float = float(rpm)
        self.rate: float = float(rpm) / 60.0  # tokens per second
        self.last_update: float = time.monotonic()

    def acquire(self, tokens: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiterRegistry:
    _buckets: ClassVar[dict[str, InMemoryTokenBucket]] = {}

    @classmethod
    def get_bucket(cls, provider: str, rpm: int = 60) -> InMemoryTokenBucket:
        if provider not in cls._buckets:
            cls._buckets[provider] = InMemoryTokenBucket(rpm=rpm)
        return cls._buckets[provider]

    @classmethod
    def check_rate_limit(cls, provider: str, rpm: int = 60) -> None:
        bucket = cls.get_bucket(provider, rpm=rpm)
        if not bucket.acquire(1.0):
            raise LLMRateLimitError(f"Local RPM limit exceeded for provider {provider}")


async def check_daily_cap(
    session: AsyncSession,
    provider: str,
    daily_cap: int | None = None,
) -> None:
    if daily_cap is None or daily_cap <= 0:
        return

    today = datetime.now(UTC).date()
    stmt = select(LLMUsage.requests).where(
        LLMUsage.provider == provider,
        LLMUsage.date == today,
    )
    result = await session.execute(stmt)
    current_requests = result.scalar_one_or_none() or 0

    if current_requests >= daily_cap:
        raise LLMQuotaExhaustedError(
            f"Daily quota of {daily_cap} requests exhausted for provider {provider}"
        )


async def increment_usage(
    session: AsyncSession,
    provider: str,
    tokens: int = 0,
) -> None:
    today = datetime.now(UTC).date()
    stmt = (
        insert(LLMUsage)
        .values(
            provider=provider,
            date=today,
            requests=1,
            tokens=tokens,
        )
        .on_conflict_do_update(
            index_elements=[LLMUsage.provider, LLMUsage.date],
            set_={
                "requests": LLMUsage.requests + 1,
                "tokens": LLMUsage.tokens + tokens,
            },
        )
    )
    await session.execute(stmt)

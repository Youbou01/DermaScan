from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrichment.models import LLMCache, LLMUsage


class EnrichmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_cached(self, key: str) -> dict[str, Any] | None:
        stmt = select(LLMCache.response_json).where(LLMCache.key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_cached(
        self,
        key: str,
        provider: str,
        model: str,
        response_json: dict[str, Any],
    ) -> None:
        stmt = (
            insert(LLMCache)
            .values(
                key=key,
                provider=provider,
                model=model,
                response_json=response_json,
            )
            .on_conflict_do_update(
                index_elements=[LLMCache.key],
                set_={
                    "provider": provider,
                    "model": model,
                    "response_json": response_json,
                },
            )
        )
        await self.session.execute(stmt)

    async def get_daily_requests(self, provider: str, target_date: date | None = None) -> int:
        d = target_date or datetime.now(UTC).date()
        stmt = select(LLMUsage.requests).where(
            LLMUsage.provider == provider,
            LLMUsage.date == d,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() or 0

    async def increment_usage(self, provider: str, tokens: int = 0) -> None:
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
        await self.session.execute(stmt)

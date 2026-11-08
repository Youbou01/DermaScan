import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrichment.models import LLMCache


def compute_cache_key(
    task: str,
    prompt_version: int | str,
    schema_version: int | str,
    normalized_input: str,
) -> str:
    raw = f"{task}|{prompt_version}|{schema_version}|{normalized_input.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def get_cached_response(session: AsyncSession, key: str) -> dict[str, Any] | None:
    stmt = select(LLMCache.response_json).where(LLMCache.key == key)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def save_cached_response(
    session: AsyncSession,
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
    await session.execute(stmt)

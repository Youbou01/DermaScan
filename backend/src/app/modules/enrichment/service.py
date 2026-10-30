from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.modules.enrichment.llm.client import LLMResult
from app.modules.enrichment.llm.router import LLMRouter
from app.modules.enrichment.repository import EnrichmentRepository

T = TypeVar("T", bound=BaseModel)


class EnrichmentService:
    def __init__(
        self,
        session: AsyncSession,
        router: LLMRouter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.router = router or LLMRouter(settings=self.settings)
        self.repo = EnrichmentRepository(session)

    async def generate_json(
        self,
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
        return await self.router.generate_json(
            session=self.session,
            task=task,
            system=system,
            prompt=prompt,
            schema=schema,
            prompt_version=prompt_version,
            schema_version=schema_version,
            images=images,
            provider_chain=provider_chain,
            bypass_cache=bypass_cache,
        )

    async def get_cached(self, key: str) -> dict[str, Any] | None:
        return await self.repo.get_cached(key)

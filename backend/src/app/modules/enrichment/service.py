import uuid
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.modules.enrichment.llm.client import LLMResult
from app.modules.enrichment.llm.router import LLMRouter
from app.modules.enrichment.prompts.alias_adjudication import (
    ALIAS_ADJUDICATION_SYSTEM_PROMPT,
    build_alias_adjudication_prompt,
)
from app.modules.enrichment.prompts.ingredient_rating import (
    INGREDIENT_RATING_SYSTEM_PROMPT,
    build_ingredient_rating_prompt,
)
from app.modules.enrichment.repository import EnrichmentRepository
from app.modules.enrichment.schemas import (
    AliasAdjudicationResult,
    IngredientRatingBatchResult,
)
from app.modules.enrichment.validator import (
    compute_consensus_rating,
    validate_and_clean_plain_text,
)
from app.modules.ingredients import AliasSource, IngredientService, RatingSource

logger = structlog.get_logger(__name__)

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
        self.ingredient_service = IngredientService(session)

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

    async def rate_ingredients(
        self,
        ingredient_ids: list[uuid.UUID],
        second_opinion: bool = True,
    ) -> int:
        """Batch rate ingredients with regulatory override, two-model consensus, and plain texts."""
        if not ingredient_ids:
            return 0

        batch_size = 10
        total_rated = 0

        for i in range(0, len(ingredient_ids), batch_size):
            batch = ingredient_ids[i : i + batch_size]
            infos = await self.ingredient_service.get_many(batch, locale="en")

            to_query: list[dict[str, Any]] = []
            id_by_inci: dict[str, uuid.UUID] = {}

            for ing_id, info in infos.items():
                # Regulatory override: Prohibited substances skip LLM rating call
                if info.is_prohibited:
                    await self.ingredient_service.set_rating(
                        ingredient_id=ing_id,
                        rating=0.5,
                        confidence=1.0,
                        source=RatingSource.REGULATORY,
                        source_ref="EU CosIng Annex II (Prohibited)",
                    )
                    total_rated += 1
                    continue

                id_by_inci[info.inci_name] = ing_id
                to_query.append(
                    {
                        "inci": info.inci_name,
                        "is_restricted": info.is_restricted,
                        "is_allergen": info.is_allergen,
                    }
                )

            if not to_query:
                continue

            prompt = build_ingredient_rating_prompt(to_query)
            chain = self.router.get_chain("rate")
            primary_provider = chain[0] if chain else "fake"

            # 1. Primary model call
            primary_res, _ = await self.generate_json(
                task="rate",
                system=INGREDIENT_RATING_SYSTEM_PROMPT,
                prompt=prompt,
                schema=IngredientRatingBatchResult,
                provider_chain=[primary_provider],
            )

            primary_map = {item.inci: item for item in primary_res.ingredients}

            # 2. Second opinion model call (if requested and second provider available)
            second_map: dict[str, Any] = {}
            second_provider: str | None = None
            if second_opinion and len(chain) > 1:
                second_provider = chain[1]
                try:
                    second_res, _ = await self.generate_json(
                        task="rate",
                        system=INGREDIENT_RATING_SYSTEM_PROMPT,
                        prompt=prompt,
                        schema=IngredientRatingBatchResult,
                        provider_chain=[second_provider],
                    )
                    second_map = {item.inci: item for item in second_res.ingredients}
                except Exception as exc:
                    logger.warning("second_opinion_rating_failed", error=str(exc))

            # 3. Apply consensus, sanitize texts, and record ratings
            for inci, ing_id in id_by_inci.items():
                p_item = primary_map.get(inci)
                if not p_item:
                    continue

                s_item = second_map.get(inci)
                if s_item is not None:
                    final_rating, final_conf, review_status = compute_consensus_rating(
                        r1=p_item.rating,
                        c1=p_item.confidence,
                        r2=s_item.rating,
                        c2=s_item.confidence,
                    )
                    used_model = f"{primary_provider}+{second_provider}"
                else:
                    final_rating, final_conf, review_status = compute_consensus_rating(
                        r1=p_item.rating,
                        c1=p_item.confidence,
                    )
                    used_model = primary_provider

                # Plain-language text validation and length limits
                summary_en = validate_and_clean_plain_text(p_item.summary.get("en"), max_words=20)
                summary_fr = validate_and_clean_plain_text(p_item.summary.get("fr"), max_words=20)
                concern_en = (
                    validate_and_clean_plain_text(p_item.concern_note.get("en"), max_words=30)
                    if p_item.concern_note
                    else None
                )
                concern_fr = (
                    validate_and_clean_plain_text(p_item.concern_note.get("fr"), max_words=30)
                    if p_item.concern_note
                    else None
                )

                summary_i18n = {k: v for k, v in {"en": summary_en, "fr": summary_fr}.items() if v}
                concern_i18n = {k: v for k, v in {"en": concern_en, "fr": concern_fr}.items() if v}

                ok = await self.ingredient_service.set_rating(
                    ingredient_id=ing_id,
                    rating=final_rating,
                    confidence=final_conf,
                    source=RatingSource.AI,
                    model=used_model,
                    review_status=review_status,
                    functions=p_item.functions,
                    summary_i18n=summary_i18n,
                    concern_note_i18n=concern_i18n,
                    mark_dirty=True,
                )
                if ok:
                    total_rated += 1

                # Proposed aliases
                for alias in p_item.aliases:
                    if alias.name and len(alias.name) <= 120:
                        await self.ingredient_service.add_alias(
                            ingredient_id=ing_id,
                            alias=alias.name,
                            language=alias.language,
                            source=AliasSource.AI,
                        )

        return total_rated

    async def adjudicate_aliases(
        self,
        unmatched_tokens: list[str],
        confidence_threshold: float = 0.8,
    ) -> int:
        """Adjudicate unmatched label tokens against canonical candidates using pg_trgm + LLM."""
        if not unmatched_tokens:
            return 0

        items_to_adjudicate: list[dict[str, Any]] = []
        token_candidates: dict[str, list[str]] = {}

        for token in unmatched_tokens:
            clean_token = token.strip()
            if not clean_token:
                continue
            suggestions = await self.ingredient_service.suggest(
                clean_token, limit=5, min_similarity=0.4
            )
            if not suggestions:
                continue

            candidates = [s.inci_name for s in suggestions]
            token_candidates[clean_token] = candidates
            items_to_adjudicate.append(
                {
                    "token": clean_token,
                    "candidates": candidates,
                }
            )

        if not items_to_adjudicate:
            return 0

        prompt = build_alias_adjudication_prompt(items_to_adjudicate)
        chain = self.router.get_chain("rate")
        provider = chain[0] if chain else "fake"

        res, _ = await self.generate_json(
            task="adjudicate",
            system=ALIAS_ADJUDICATION_SYSTEM_PROMPT,
            prompt=prompt,
            schema=AliasAdjudicationResult,
            provider_chain=[provider],
        )

        accepted_count = 0
        for item in res.adjudications:
            if not item.matched_candidate or item.confidence < confidence_threshold:
                continue

            candidate_inci = item.matched_candidate
            # Verify candidate was among suggested candidates
            valid_candidates = token_candidates.get(item.token, [])
            if candidate_inci not in valid_candidates:
                continue

            matches = await self.ingredient_service.match([candidate_inci])
            if matches and matches[0].ingredient_id is not None:
                ing_id = matches[0].ingredient_id
                added = await self.ingredient_service.add_alias(
                    ingredient_id=ing_id,
                    alias=item.token,
                    source=AliasSource.AI,
                )
                if added:
                    accepted_count += 1

        return accepted_count

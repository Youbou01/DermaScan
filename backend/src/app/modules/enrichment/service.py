import uuid
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.modules.catalog.category_service import CategoryService
from app.modules.catalog.enums import EnrichmentStatus
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
from app.modules.enrichment.prompts.product_enrichment import (
    PRODUCT_ENRICHMENT_SYSTEM_PROMPT,
    build_product_enrichment_prompt,
)
from app.modules.enrichment.repository import EnrichmentRepository
from app.modules.enrichment.schemas import (
    AliasAdjudicationResult,
    EnrichmentOutcome,
    IngredientRatingBatchResult,
    OcrIngredientsResult,
    ProductEnrichmentResult,
)
from app.modules.enrichment.validator import (
    compute_consensus_rating,
    validate_and_clean_plain_text,
)
from app.modules.ingredients import (
    AliasSource,
    IngredientService,
    RatingSource,
    normalize,
    parse_ingredient_label,
)

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

    async def enrich_product(
        self,
        mapped: dict[str, Any],
        raw_payload: dict[str, Any] | None = None,
    ) -> EnrichmentOutcome:
        """Enrich a mapped product record using the LLM gateway with deterministic validation."""
        category_nodes = await CategoryService(self.session).get_tree(locale="en")
        valid_categories: list[dict[str, str]] = []

        def collect_nodes(nodes: list[Any]) -> None:
            for n in nodes:
                valid_categories.append({"slug": n.slug, "name": n.name})
                if n.children:
                    collect_nodes(n.children)

        collect_nodes(category_nodes)

        prompt = build_product_enrichment_prompt(mapped, valid_categories)
        chain = self.router.get_chain("enrich")

        try:
            res, _ = await self.generate_json(
                task="enrich",
                system=PRODUCT_ENRICHMENT_SYSTEM_PROMPT,
                prompt=prompt,
                schema=ProductEnrichmentResult,
                provider_chain=chain,
            )
        except Exception as exc:
            logger.error("product_enrichment_llm_failed", error=str(exc))
            return EnrichmentOutcome(status=EnrichmentStatus.FAILED, reason=f"llm_error: {exc}")

        # Post-LLM Deterministic Validation (Section 8.2)
        # 1. Skincare confirmation
        if not res.is_skincare or res.is_skincare_confidence < 0.6:
            return EnrichmentOutcome(
                status=EnrichmentStatus.FAILED, reason="not_skincare", result=res
            )

        # 2. Ingredient count bounds
        if len(res.ingredients_inci) < 2:
            return EnrichmentOutcome(
                status=EnrichmentStatus.QUARANTINED, reason="insufficient_ingredients", result=res
            )
        if len(res.ingredients_inci) > 120:
            return EnrichmentOutcome(
                status=EnrichmentStatus.QUARANTINED, reason="too_many_ingredients", result=res
            )

        # 3. Item length constraint
        if any(
            len(item.original) > 120 or (item.inci and len(item.inci) > 120)
            for item in res.ingredients_inci
        ):
            return EnrichmentOutcome(
                status=EnrichmentStatus.QUARANTINED, reason="item_too_long", result=res
            )

        # 4. Token Jaccard check with label parser
        raw_text = str(mapped.get("raw_ingredients_text") or "")
        parser_parsed = parse_ingredient_label(raw_text)
        parser_tokens = {normalize(item.text) for item in parser_parsed if normalize(item.text)}
        llm_tokens = {
            normalize(item.inci or item.original)
            for item in res.ingredients_inci
            if normalize(item.inci or item.original)
        }

        if parser_tokens and llm_tokens:
            jaccard = len(parser_tokens & llm_tokens) / len(parser_tokens | llm_tokens)
            if jaccard < 0.5:
                return EnrichmentOutcome(
                    status=EnrichmentStatus.QUARANTINED, reason="parser_llm_disagree", result=res
                )

        # 5. Field confidence thresholding
        min_conf = self.settings.llm_min_confidence
        clean_brand = res.brand if (res.brand_confidence >= min_conf) else None
        clean_category = res.category_slug if (res.category_confidence >= min_conf) else None

        clean_result = ProductEnrichmentResult(
            is_skincare=res.is_skincare,
            is_skincare_confidence=res.is_skincare_confidence,
            brand=clean_brand,
            brand_confidence=res.brand_confidence,
            name_clean=res.name_clean,
            name_i18n=res.name_i18n,
            source_lang=res.source_lang,
            category_slug=clean_category,
            category_confidence=res.category_confidence,
            ingredients_inci=res.ingredients_inci,
            ingredients_confidence=res.ingredients_confidence,
            flags=res.flags,
        )

        return EnrichmentOutcome(status=EnrichmentStatus.DONE, reason=None, result=clean_result)

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

    async def ocr_ingredients(self, image_data: bytes) -> OcrIngredientsResult:
        """Extract ingredient list text from a product packaging photo using vision LLM."""
        import base64

        b64_image = base64.b64encode(image_data).decode("utf-8")
        system_prompt = (
            "You are a computer vision specialist in skincare products. "
            "Your task is to transcribe the ingredient list printed on the "
            "product packaging label accurately and verbatim. "
            "Return JSON conforming to the schema."
        )
        prompt = (
            "Transcribe the ingredients list printed on this product package image. "
            "Ignore marketing claims, directions of use, and warnings. "
            "Return ingredients_text, confidence (0.0 to 1.0), and is_readable (true/false)."
        )
        validated, _ = await self.router.generate_json(
            task="ocr_ingredients",
            system=system_prompt,
            prompt=prompt,
            schema=OcrIngredientsResult,
            session=self.session,
            images=[b64_image],
        )
        return validated

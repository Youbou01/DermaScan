"""The ingredients module's public service."""

import uuid
from collections.abc import Awaitable, Callable, Collection, Sequence
from decimal import Decimal
from typing import ClassVar

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.i18n import DEFAULT_LOCALE
from app.modules.ingredients.enums import RatingSource, ReviewStatus
from app.modules.ingredients.matching import candidate_keys
from app.modules.ingredients.models import IngredientTranslation, derive_risk_from_rating
from app.modules.ingredients.normalizer import normalize
from app.modules.ingredients.repository import IngredientRepository
from app.modules.ingredients.schemas import (
    IngredientInfo,
    IngredientMatch,
    IngredientSuggestion,
    MatchType,
)

logger = structlog.get_logger(__name__)


class IngredientService:
    _dirty_hooks: ClassVar[
        list[Callable[[AsyncSession, Collection[uuid.UUID]], Awaitable[int]]]
    ] = []

    @classmethod
    def register_dirty_hook(
        cls, hook: Callable[[AsyncSession, Collection[uuid.UUID]], Awaitable[int]]
    ) -> None:
        if hook not in cls._dirty_hooks:
            cls._dirty_hooks.append(hook)

    def __init__(self, session: AsyncSession) -> None:
        self._repository = IngredientRepository(session)

    async def match(self, raw_items: Sequence[str]) -> list[IngredientMatch]:
        """Match label items to known ingredients. Returns one result per input, same order.

        Rules (ADR-0009), in order:
          1. The whole item's normalized text is a known name  -> EXACT.
          2. Otherwise try its parts ("Aqua (Water)" -> "aqua", "water"). If the parts that
             are known all point to the SAME ingredient           -> COMPONENT.
          3. Anything else, including parts pointing to different ingredients -> NONE.

        There is deliberately no fuzzy matching here: "sodium laureth sulfate" and "sodium
        lauryl sulfate" are 72% similar yet are different ingredients with different risk.
        Use `suggest()` to show such candidates to a human instead.
        """
        candidates = [candidate_keys(item) for item in raw_items]
        every_key = set().union(*(c.all_keys() for c in candidates)) if candidates else set()
        known = await self._repository.find_ids_by_normalized_aliases(every_key)

        matches: list[IngredientMatch] = []
        for raw_text, candidate in zip(raw_items, candidates, strict=True):
            if candidate.whole in known:
                matches.append(
                    IngredientMatch(
                        raw_text=raw_text,
                        ingredient_id=known[candidate.whole],
                        match_type=MatchType.EXACT,
                    )
                )
                continue
            found = {known[key] for key in candidate.components if key in known}
            if len(found) == 1:
                matches.append(
                    IngredientMatch(
                        raw_text=raw_text, ingredient_id=found.pop(), match_type=MatchType.COMPONENT
                    )
                )
            else:
                matches.append(
                    IngredientMatch(
                        raw_text=raw_text, ingredient_id=None, match_type=MatchType.NONE
                    )
                )
        return matches

    async def get_many(
        self, ingredient_ids: Collection[uuid.UUID], locale: str
    ) -> dict[uuid.UUID, IngredientInfo]:
        """Ingredient details by id. The rationale is in `locale`, else English, else None."""
        ingredients = await self._repository.get_many(ingredient_ids)
        translations = await self._repository.get_translations(
            ingredients.keys(), {locale, DEFAULT_LOCALE}
        )
        by_ingredient: dict[uuid.UUID, dict[str, str]] = {}
        for translation in translations:
            by_ingredient.setdefault(translation.ingredient_id, {})[translation.locale] = (
                translation.rationale
            )

        infos: dict[uuid.UUID, IngredientInfo] = {}
        for ingredient_id, ingredient in ingredients.items():
            texts = by_ingredient.get(ingredient_id, {})
            infos[ingredient_id] = IngredientInfo(
                id=ingredient_id,
                inci_name=ingredient.inci_name,
                risk_level=RiskLevel(ingredient.risk_level),
                rationale=texts.get(locale) or texts.get(DEFAULT_LOCALE),
                source_ref=ingredient.source_ref,
            )
        return infos

    async def suggest(
        self, text: str, *, limit: int = 5, min_similarity: float = 0.4
    ) -> list[IngredientSuggestion]:
        """Known names that LOOK like `text`, best first, one entry per ingredient.

        For humans only (review report, ingredient search box): a suggestion is never
        applied automatically.
        """
        key = normalize(text)
        if not key:
            return []
        rows = await self._repository.find_similar_aliases(
            key,
            limit=limit * 4,
            min_similarity=min_similarity,  # aliases of one ingredient repeat
        )
        best: dict[uuid.UUID, IngredientSuggestion] = {}
        for ingredient_id, inci_name, alias, similarity in rows:
            if ingredient_id not in best:  # rows are sorted best-first
                best[ingredient_id] = IngredientSuggestion(
                    ingredient_id=ingredient_id,
                    inci_name=inci_name,
                    alias=alias,
                    similarity=round(similarity, 3),
                )
        return list(best.values())[:limit]

    async def set_rating(
        self,
        ingredient_id: uuid.UUID,
        rating: Decimal | float | None,
        confidence: Decimal | float | None = None,
        source: RatingSource = RatingSource.AI,
        source_ref: str | None = None,
        model: str | None = None,
        version: int = 1,
        review_status: ReviewStatus | None = None,
        functions: list[str] | None = None,
        summary_i18n: dict[str, str] | None = None,
        concern_note_i18n: dict[str, str] | None = None,
        mark_dirty: bool = True,
        dirty_notifier: Callable[[Collection[uuid.UUID]], Awaitable[int]] | None = None,
    ) -> bool:
        """Single authoritative writer of ingredient rating, risk_level, and regulatory state.

        Marks affected catalog products score_dirty = True when rating changes.
        """
        ingredient = await self._repository.get(ingredient_id)
        if not ingredient:
            return False

        # Protect curated ratings from being overwritten by AI
        if ingredient.rating_source == RatingSource.CURATED and source != RatingSource.CURATED:
            logger.info("cannot_overwrite_curated_rating", ingredient_id=str(ingredient_id))
            return False

        final_rating: Decimal | None
        final_source: RatingSource
        final_ref: str | None

        # Regulatory pre-rule: Annex II prohibited forces 0.5 rating and regulatory source
        if ingredient.is_prohibited:
            final_rating = Decimal("0.5")
            final_source = RatingSource.REGULATORY
            final_ref = source_ref or "EU CosIng Annex II (Prohibited)"
        else:
            final_rating = Decimal(str(rating)) if rating is not None else None
            final_source = source
            # Annex III / fragrance allergen cap: cannot exceed 8.0
            if (
                (ingredient.is_restricted or ingredient.is_allergen)
                and final_rating is not None
                and final_rating > Decimal("8.0")
            ):
                final_rating = Decimal("8.0")
            final_ref = source_ref

        # DB constraint requires source_ref when risk is moderate or high
        if final_rating is not None and final_rating < Decimal("7.0") and not final_ref:
            final_ref = f"{final_source.value}:{model or 'assessment'}"

        expected_risk = derive_risk_from_rating(final_rating)
        ingredient.risk_level = expected_risk
        ingredient.rating = final_rating
        ingredient.source_ref = final_ref
        ingredient.rating_source = final_source
        if confidence is not None:
            ingredient.rating_confidence = Decimal(str(confidence))
        ingredient.rating_version = version
        if model is not None:
            ingredient.rating_model = model
        if functions is not None:
            ingredient.functions = functions

        if review_status is not None:
            ingredient.review_status = review_status
        elif (
            final_rating is not None
            and final_rating < Decimal("4.0")
            and final_source == RatingSource.AI
        ):
            ingredient.review_status = ReviewStatus.NEEDS_REVIEW
        else:
            ingredient.review_status = ReviewStatus.AUTO

        # Translations update
        locales = set((summary_i18n or {}).keys()) | set((concern_note_i18n or {}).keys())
        for loc in locales:
            trans = await self._repository.get_translation(ingredient_id, loc)
            sum_text = (summary_i18n or {}).get(loc)
            con_text = (concern_note_i18n or {}).get(loc)
            if trans is None:
                rationale = con_text or sum_text or ""
                new_trans = IngredientTranslation(
                    ingredient_id=ingredient_id,
                    locale=loc,
                    rationale=rationale,
                    summary=sum_text,
                    concern_note=con_text,
                )
                self._repository._session.add(new_trans)
            else:
                if sum_text is not None:
                    trans.summary = sum_text
                if con_text is not None:
                    trans.concern_note = con_text
                if not trans.rationale and (con_text or sum_text):
                    trans.rationale = con_text or sum_text or ""

        await self._repository._session.flush()

        if mark_dirty:
            if dirty_notifier:
                await dirty_notifier([ingredient_id])
            for hook in self._dirty_hooks:
                await hook(self._repository._session, [ingredient_id])

        return True

"""The ingredients module's public service."""

import uuid
from collections.abc import Collection, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.i18n import DEFAULT_LOCALE
from app.modules.ingredients.matching import candidate_keys
from app.modules.ingredients.normalizer import normalize
from app.modules.ingredients.repository import IngredientRepository
from app.modules.ingredients.schemas import (
    IngredientInfo,
    IngredientMatch,
    IngredientSuggestion,
    MatchType,
)


class IngredientService:
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

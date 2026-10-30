"""SQL for the ingredients module. Private: other modules use `IngredientService`."""

import uuid
from collections.abc import Collection

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingredients.enums import AliasSource
from app.modules.ingredients.models import Ingredient, IngredientAlias, IngredientTranslation


class IngredientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_ids_by_normalized_aliases(self, keys: Collection[str]) -> dict[str, uuid.UUID]:
        """One query for any number of names. `normalized_alias` is unique, so each key
        maps to at most one ingredient."""
        if not keys:
            return {}
        result = await self._session.execute(
            select(IngredientAlias.normalized_alias, IngredientAlias.ingredient_id).where(
                IngredientAlias.normalized_alias.in_(keys)
            )
        )
        return dict(result.all())

    async def get_many(self, ids: Collection[uuid.UUID]) -> dict[uuid.UUID, Ingredient]:
        if not ids:
            return {}
        result = await self._session.scalars(select(Ingredient).where(Ingredient.id.in_(ids)))
        return {ingredient.id: ingredient for ingredient in result}

    async def get_translations(
        self, ids: Collection[uuid.UUID], locales: Collection[str]
    ) -> list[IngredientTranslation]:
        if not ids:
            return []
        result = await self._session.scalars(
            select(IngredientTranslation).where(
                IngredientTranslation.ingredient_id.in_(ids),
                IngredientTranslation.locale.in_(locales),
            )
        )
        return list(result)

    async def find_similar_aliases(
        self, normalized: str, *, limit: int, min_similarity: float
    ) -> list[tuple[uuid.UUID, str, str, float]]:
        """Aliases that look like `normalized`: (ingredient_id, inci_name, alias, similarity).

        `%` is pg_trgm's "similar enough" operator and is what the trigram index serves;
        the explicit `similarity >= ...` applies our own, stricter threshold on top.
        """
        similarity = func.similarity(IngredientAlias.normalized_alias, normalized)
        result = await self._session.execute(
            select(
                IngredientAlias.ingredient_id,
                Ingredient.inci_name,
                IngredientAlias.alias,
                similarity.label("similarity"),
            )
            .join(Ingredient, Ingredient.id == IngredientAlias.ingredient_id)
            .where(
                IngredientAlias.normalized_alias.op("%")(normalized), similarity >= min_similarity
            )
            .order_by(similarity.desc(), IngredientAlias.alias)
            .limit(limit)
        )
        return [(row[0], row[1], row[2], float(row[3])) for row in result.all()]

    async def get(self, ingredient_id: uuid.UUID) -> Ingredient | None:
        return await self._session.get(Ingredient, ingredient_id)

    async def get_by_inci(self, inci_name: str) -> Ingredient | None:
        stmt = select(Ingredient).where(Ingredient.inci_name == inci_name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_translation(
        self, ingredient_id: uuid.UUID, locale: str
    ) -> IngredientTranslation | None:
        stmt = select(IngredientTranslation).where(
            IngredientTranslation.ingredient_id == ingredient_id,
            IngredientTranslation.locale == locale,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_alias_if_not_exists(
        self,
        ingredient_id: uuid.UUID,
        alias: str,
        normalized_alias: str,
        language: str | None = None,
        source: AliasSource = AliasSource.AI,
    ) -> bool:
        stmt = (
            insert(IngredientAlias)
            .values(
                id=uuid.uuid7(),
                ingredient_id=ingredient_id,
                alias=alias,
                normalized_alias=normalized_alias,
                language=language,
                source=source,
            )
            .on_conflict_do_nothing(index_elements=[IngredientAlias.normalized_alias])
            .returning(IngredientAlias.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

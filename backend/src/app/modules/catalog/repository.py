"""SQL for the catalog module. Private: the outside world uses `CatalogService`."""

import uuid
from collections.abc import Collection
from typing import Any, cast

from sqlalchemy import CursorResult, Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.modules.catalog.models import Category, Product, ProductIngredient


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _with_detail_loaded() -> Select[Product]:
        """Everything a product detail page needs, loaded explicitly (relationships are
        lazy="raise") and in a fixed number of queries, however many ingredients there are."""
        return select(Product).options(
            joinedload(Product.brand),
            joinedload(Product.primary_category).selectinload(Category.translations),
            selectinload(Product.ingredients),  # ordered by position (see the relationship)
        )

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        return await self._session.scalar(
            self._with_detail_loaded().where(Product.id == product_id)
        )

    async def get_by_barcode(self, barcode: str) -> Product | None:
        """`barcode` must already be a normalized GTIN-13."""
        return await self._session.scalar(
            self._with_detail_loaded().where(Product.barcode == barcode)
        )

    async def find_dirty_or_stale_products(
        self, batch_size: int = 100, min_scoring_version: int = 3
    ) -> list[Product]:
        stmt = (
            self._with_detail_loaded()
            .where(
                (Product.score_dirty.is_(True))
                | (Product.scoring_version.is_(None))
                | (Product.scoring_version < min_scoring_version)
            )
            .order_by(Product.updated_at.desc())
            .limit(batch_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_unmatched_ingredients(self, limit: int = 500) -> list[ProductIngredient]:
        stmt = (
            select(ProductIngredient).where(ProductIngredient.ingredient_id.is_(None)).limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_products_dirty_for_ingredients(
        self, ingredient_ids: Collection[uuid.UUID]
    ) -> int:
        if not ingredient_ids:
            return 0
        stmt = (
            update(Product)
            .where(
                Product.id.in_(
                    select(ProductIngredient.product_id)
                    .where(ProductIngredient.ingredient_id.in_(ingredient_ids))
                    .distinct()
                )
            )
            .values(score_dirty=True)
        )
        result = await self._session.execute(stmt)
        return int(cast(CursorResult[Any], result).rowcount)

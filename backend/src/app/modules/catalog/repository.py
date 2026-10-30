"""SQL for the catalog module. Private: the outside world uses `CatalogService`."""

import uuid
from collections.abc import Collection
from typing import Any, cast

from sqlalchemy import CursorResult, Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.modules.catalog.enums import ProductSource
from app.modules.catalog.models import Brand, Category, Product, ProductIngredient


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

    async def get_by_source(self, source: ProductSource, source_id: str) -> Product | None:
        return await self._session.scalar(
            self._with_detail_loaded().where(
                Product.source == source, Product.source_id == source_id
            )
        )

    async def get_or_create_brand(self, brand_name: str) -> Brand:
        clean = brand_name.strip()
        existing = await self._session.scalar(
            select(Brand).where(func.lower(Brand.name) == func.lower(clean))
        )
        if existing is not None:
            return existing
        brand = Brand(name=clean)
        self._session.add(brand)
        await self._session.flush()
        return brand

    async def delete_product_ingredients(self, product_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(ProductIngredient).where(ProductIngredient.product_id == product_id)
        )
        await self._session.flush()

    async def find_similar_products(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.4,
    ) -> list[tuple[Product, float]]:
        sim = func.similarity(Product.name_normalized, query)
        stmt = (
            self._with_detail_loaded()
            .add_columns(sim.label("similarity"))
            .where(sim >= min_similarity)
            .order_by(sim.desc())
            .limit(limit)
        )
        res = await self._session.execute(stmt)
        results: list[tuple[Product, float]] = []
        for row in res.all():
            prod = cast(Product, row[0])
            score = float(row[1])
            results.append((prod, score))
        return results

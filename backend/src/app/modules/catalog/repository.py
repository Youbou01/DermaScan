"""SQL for the catalog module. Private: the outside world uses `CatalogService`."""

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.modules.catalog.models import Category, Product


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

"""Business logic for a user's saved products and view history."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, ProductCardOut
from app.modules.personal_library.repository import PersonalLibraryRepository
from app.modules.personal_library.schemas import ProductPageOut


class PersonalLibraryService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = PersonalLibraryRepository(session)
        self._catalog = CatalogService(session)

    async def save_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._catalog.get_product_detail(product_id, "en")
        await self._repository.save_product(user_id, product_id)

    async def unsave_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._repository.unsave_product(user_id, product_id)

    async def is_saved(self, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        return await self._repository.is_saved(user_id, product_id)

    async def saved_products(
        self, user_id: uuid.UUID, locale: str, limit: int, cursor: str | None
    ) -> ProductPageOut:
        rows, next_cursor = await self._repository.list_saved_products(user_id, limit, cursor)
        products = await self._product_cards([row.product_id for row in rows], locale)
        return ProductPageOut(items=products, next_cursor=next_cursor)

    async def record_recently_viewed(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._catalog.get_product_detail(product_id, "en")
        await self._repository.record_view(user_id, product_id)

    async def recently_viewed(
        self, user_id: uuid.UUID, locale: str, limit: int, cursor: str | None
    ) -> ProductPageOut:
        rows, next_cursor = await self._repository.list_recently_viewed(user_id, limit, cursor)
        products = await self._product_cards([row.product_id for row in rows], locale)
        return ProductPageOut(items=products, next_cursor=next_cursor)

    async def _product_cards(
        self, product_ids: list[uuid.UUID], locale: str
    ) -> list[ProductCardOut]:
        cards: list[ProductCardOut] = []
        for product_id in product_ids:
            detail = await self._catalog.get_product_detail(product_id, locale)
            cards.append(
                ProductCardOut(
                    id=detail.id,
                    name=detail.name,
                    brand=detail.brand,
                    image_url=detail.image_url,
                    score=detail.score,
                    score_band=detail.score_band,
                    score_is_estimated=detail.score_is_estimated,
                    category_slug=detail.category.slug if detail.category else None,
                )
            )
        return cards

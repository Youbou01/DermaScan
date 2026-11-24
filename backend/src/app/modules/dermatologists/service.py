"""Curated informational guidance and related catalog links."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, ProductCardOut, ProductNotFoundError
from app.modules.dermatologists.repository import DermatologistsRepository
from app.modules.dermatologists.schemas import (
    DermatologistOut,
    DermatologistRecommendationOut,
    RecommendationsOut,
)


class DermatologistsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = DermatologistsRepository(session)
        self._catalog = CatalogService(session)

    async def recommendations(self, skin_type: str | None, locale: str) -> RecommendationsOut:
        rows = await self._repository.list_recommendations(skin_type)
        product_ids = await self._repository.related_product_ids([item.id for item, _ in rows])
        items: list[DermatologistRecommendationOut] = []
        for content, dermatologist in rows:
            products: list[ProductCardOut] = []
            for product_id in product_ids.get(content.id, []):
                try:
                    detail = await self._catalog.get_product_detail(product_id, locale)
                except ProductNotFoundError:
                    continue
                products.append(
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
            items.append(
                DermatologistRecommendationOut(
                    id=content.id,
                    dermatologist=(
                        DermatologistOut(
                            display_name=dermatologist.display_name,
                            credentials=dermatologist.credentials,
                            specialty=dermatologist.specialty,
                            is_verified=dermatologist.is_verified,
                            verification_source_url=dermatologist.verification_source_url,
                        )
                        if dermatologist is not None
                        else None
                    ),
                    title=content.title_fr if locale == "fr" else content.title_en,
                    advice=content.advice_fr if locale == "fr" else content.advice_en,
                    source_title=content.source_title,
                    source_url=content.source_url,
                    related_products=products,
                )
            )
        return RecommendationsOut(
            recommendations=items,
            disclaimer=(
                "Informations générales de soin de la peau. Elles ne constituent pas un diagnostic "
                "et ne remplacent pas l'avis d'un dermatologue."
                if locale == "fr"
                else "General skin care information only. It is not a diagnosis and does not replace "
                "advice from a dermatologist."
            ),
        )


async def get_recommendations_for_user(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    skin_type: str | None,
    locale: str,
) -> RecommendationsOut:
    if skin_type is None and user_id is not None:
        from app.modules.identity import get_saved_skin_type

        skin_type = await get_saved_skin_type(session, user_id)
    return await DermatologistsService(session).recommendations(skin_type, locale)

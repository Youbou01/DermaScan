"""SQL access for curated dermatologist references and recommendation content."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dermatologists.models import (
    Dermatologist,
    RecommendationContent,
    RecommendationProduct,
)


class DermatologistsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recommendations(
        self, skin_type: str | None
    ) -> list[tuple[RecommendationContent, Dermatologist | None]]:
        if skin_type is not None:
            specific = await self._recommendations_for(skin_type)
            if specific:
                return specific
        return await self._recommendations_for(None)

    async def _recommendations_for(
        self, skin_type: str | None
    ) -> list[tuple[RecommendationContent, Dermatologist | None]]:
        statement = (
            select(RecommendationContent, Dermatologist)
            .outerjoin(Dermatologist, Dermatologist.id == RecommendationContent.dermatologist_id)
            .where(RecommendationContent.skin_type == skin_type)
            .order_by(RecommendationContent.id)
        )
        rows = (await self._session.execute(statement)).all()
        return [(row[0], row[1]) for row in rows]

    async def related_product_ids(
        self, recommendation_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        if not recommendation_ids:
            return {}
        statement = (
            select(RecommendationProduct.recommendation_id, RecommendationProduct.product_id)
            .where(RecommendationProduct.recommendation_id.in_(recommendation_ids))
            .order_by(RecommendationProduct.position)
        )
        result: dict[uuid.UUID, list[uuid.UUID]] = {}
        for recommendation_id, product_id in (await self._session.execute(statement)).all():
            result.setdefault(recommendation_id, []).append(product_id)
        return result

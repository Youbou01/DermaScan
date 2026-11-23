"""SQL access for offers. Other modules use OfferService instead."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.offers.models import ProductOffer, Retailer


class OfferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_product(self, product_id: uuid.UUID) -> list[tuple[ProductOffer, Retailer]]:
        statement = (
            select(ProductOffer, Retailer)
            .join(Retailer, Retailer.id == ProductOffer.retailer_id)
            .where(ProductOffer.product_id == product_id)
            .order_by(ProductOffer.price, Retailer.name, ProductOffer.id)
        )
        return [(offer, retailer) for offer, retailer in (await self._session.execute(statement))]

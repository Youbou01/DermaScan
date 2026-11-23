"""SQL access for offers. Other modules use OfferService instead."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.offers.enums import StockState
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

    async def upsert_retailer(self, *, name: str, domain: str) -> Retailer:
        """Atomic insert-or-update keyed by the unique domain."""
        statement = (
            pg_insert(Retailer)
            .values(name=name, domain=domain)
            .on_conflict_do_update(index_elements=["domain"], set_={"name": name})
            .returning(Retailer)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(statement)).scalar_one()

    async def get_offer(self, product_id: uuid.UUID, retailer_id: uuid.UUID) -> ProductOffer | None:
        statement = select(ProductOffer).where(
            ProductOffer.product_id == product_id,
            ProductOffer.retailer_id == retailer_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def upsert_offer(
        self,
        *,
        product_id: uuid.UUID,
        retailer_id: uuid.UUID,
        price: Decimal,
        currency: str,
        url: str,
        stock_state: StockState,
        source: str,
        last_checked_at: datetime,
        content_hash: str,
    ) -> bool:
        """Insert or update one offer. Returns True when the row is new or its data changed."""
        existing = await self.get_offer(product_id, retailer_id)
        if existing is None:
            self._session.add(
                ProductOffer(
                    product_id=product_id,
                    retailer_id=retailer_id,
                    price=price,
                    currency=currency,
                    url=url,
                    stock_state=stock_state,
                    source=source,
                    last_checked_at=last_checked_at,
                    content_hash=content_hash,
                )
            )
            await self._session.flush()
            return True

        existing.last_checked_at = last_checked_at
        changed = existing.content_hash != content_hash
        if changed:
            existing.price = price
            existing.currency = currency
            existing.url = url
            existing.stock_state = stock_state
            existing.source = source
            existing.content_hash = content_hash
        await self._session.flush()
        return changed

"""Pydantic schemas for the offers API."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.offers.enums import StockState


class RetailerOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    domain: str
    logo_url: str | None
    is_affiliate: bool
    affiliate_label: str | None


class OfferOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    retailer: RetailerOut
    price: Decimal = Field(description="Exact decimal price, serialized as a string.")
    currency: str = Field(description="ISO 4217 code, 3 uppercase letters.")
    url: str
    stock_state: StockState
    freshness: Literal["fresh", "stale"] = Field(
        description="'stale' when last_checked_at is older than OFFER_STALE_AFTER_DAYS."
    )
    last_checked_at: datetime
    is_cheapest: bool = Field(description="Computed at read time, never stored.")


class OfferListOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: uuid.UUID
    cheapest_offer_id: uuid.UUID | None = Field(
        description="Null when no eligible offer exists or eligible offers mix currencies."
    )
    mixed_currencies: bool
    offers: list[OfferOut]

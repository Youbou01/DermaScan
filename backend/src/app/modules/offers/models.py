"""Persistence models owned by the offers module."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.offers.enums import StockState


class Retailer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "retailer"

    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    logo_url: Mapped[str | None] = mapped_column(Text)
    is_affiliate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    affiliate_label: Mapped[str | None] = mapped_column(String(100))


class ProductOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_offer"
    __table_args__ = (
        enum_check("stock_state", StockState),
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso"),
        UniqueConstraint("product_id", "retailer_id", name="uq_product_offer_product_retailer"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    retailer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("retailer.id"), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3))
    url: Mapped[str] = mapped_column(Text)
    stock_state: Mapped[StockState] = mapped_column(enum_type(StockState))
    source: Mapped[str] = mapped_column(String(32))
    last_checked_at: Mapped[datetime] = mapped_column()
    content_hash: Mapped[str] = mapped_column(String(64))

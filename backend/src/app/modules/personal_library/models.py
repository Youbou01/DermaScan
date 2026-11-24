"""Persistence models owned by the personal library module."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base


class SavedProduct(Base):
    __tablename__ = "saved_product"
    __table_args__ = (
        Index("ix_saved_product_user_saved_at_product", "user_id", "saved_at", "product_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecentlyViewedProduct(Base):
    __tablename__ = "recently_viewed_product"
    __table_args__ = (
        Index(
            "ix_recently_viewed_user_viewed_at_product",
            "user_id",
            "viewed_at",
            "product_id",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

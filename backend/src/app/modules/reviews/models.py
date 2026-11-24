"""Persistence models owned by the reviews module."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.reviews.enums import ReviewCacheStatus, ReviewSource


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review"
    __table_args__ = (
        enum_check("source", ReviewSource),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint(
            "source <> 'app' OR (user_id IS NOT NULL AND rating IS NOT NULL)",
            name="app_review_requires_user_and_rating",
        ),
        Index(
            "uq_review_app_user_product",
            "product_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL AND source = 'app'"),
        ),
        Index(
            "uq_review_external_source_id",
            "product_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "ix_review_product_created_at_id",
            "product_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_review_user_created_at_id",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[ReviewSource] = mapped_column(
        enum_type(ReviewSource),
        default=ReviewSource.APP,
        server_default=ReviewSource.APP.value,
    )
    author_name: Mapped[str] = mapped_column(String(120))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    body: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(128))
    external_url: Mapped[str | None] = mapped_column(Text)


class ReviewSourceCache(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "review_source_cache"
    __table_args__ = (
        enum_check("source", ReviewSource),
        enum_check("status", ReviewCacheStatus),
        UniqueConstraint("product_id", "source", name="uq_review_source_cache_product_source"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[ReviewSource] = mapped_column(enum_type(ReviewSource))
    status: Mapped[ReviewCacheStatus] = mapped_column(
        enum_type(ReviewCacheStatus),
        default=ReviewCacheStatus.FRESH,
        server_default=ReviewCacheStatus.FRESH.value,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

"""Curated dermatologist references and skin care recommendation content."""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base, UUIDPrimaryKeyMixin


class Dermatologist(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dermatologist"

    display_name: Mapped[str] = mapped_column(String(160))
    credentials: Mapped[str] = mapped_column(String(80))
    specialty: Mapped[str] = mapped_column(String(120))
    is_verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    verification_source_url: Mapped[str] = mapped_column(String(500))


class RecommendationContent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dermatologist_recommendation"
    __table_args__ = (
        CheckConstraint(
            "skin_type IS NULL OR skin_type IN "
            "('normal', 'dry', 'oily', 'combination', 'sensitive')",
            name="skin_type_valid",
        ),
        UniqueConstraint(
            "dermatologist_id", "skin_type", name="uq_dermatologist_recommendation_skin"
        ),
        Index(
            "uq_dermatologist_recommendation_generic",
            "dermatologist_id",
            unique=True,
            postgresql_where=text("skin_type IS NULL"),
        ),
        Index("ix_dermatologist_recommendation_skin_type", "skin_type"),
    )

    dermatologist_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dermatologist.id", ondelete="SET NULL"), index=True, nullable=True
    )
    skin_type: Mapped[str | None] = mapped_column(String(32))
    title_en: Mapped[str] = mapped_column(String(160))
    title_fr: Mapped[str] = mapped_column(String(160))
    advice_en: Mapped[str] = mapped_column(Text)
    advice_fr: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(500))


class RecommendationProduct(Base):
    __tablename__ = "dermatologist_recommendation_product"
    __table_args__ = (
        CheckConstraint("position >= 1", name="position_positive"),
        UniqueConstraint(
            "recommendation_id", "position", name="uq_recommendation_product_position"
        ),
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dermatologist_recommendation.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger)

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.enums import RiskLevel
from app.core.orm import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.catalog.enums import EnrichmentStatus, ImageStatus, ProductSource
from app.modules.catalog.search_text import normalize_name


class Brand(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "brand"
    # Case-insensitive uniqueness: "Nivea" and "nivea" must be the same brand.
    __table_args__ = (Index("uq_brand_name_lower", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(255))


class Category(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "category"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("category.id", ondelete="RESTRICT"), index=True
    )
    # Stable key shared by seed files and the mobile app (icons, i18n): 'moisturizer'.
    slug: Mapped[str] = mapped_column(String(64), unique=True)

    translations: Mapped[list[CategoryTranslation]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )


class CategoryTranslation(Base):
    __tablename__ = "category_translation"
    __table_args__ = (CheckConstraint("locale ~ '^[a-z]{2}$'", name="locale_format"),)

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("category.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product"
    __table_args__ = (
        enum_check("score_band", RiskLevel),
        enum_check("source", ProductSource),
        enum_check("enrichment_status", EnrichmentStatus),
        enum_check("image_status", ImageStatus),
        # Barcodes are normalized to GTIN-13 before they reach the database.
        CheckConstraint("barcode ~ '^[0-9]{13}$'", name="barcode_gtin13"),
        CheckConstraint("score IS NULL OR score BETWEEN 0 AND 100", name="score_range"),
        CheckConstraint(
            "score_coverage IS NULL OR score_coverage BETWEEN 0 AND 1", name="coverage_range"
        ),
        # Makes imports idempotent: re-running an import updates instead of duplicating.
        UniqueConstraint("source", "source_id", name="uq_product_source_source_id"),
        # Home-feed shelves (migration a1b2c3d4e5f6). Keep in sync with Alembic.
        Index(
            "ix_product_score_desc_id",
            text("score DESC"),
            "id",
            postgresql_where=text("score IS NOT NULL AND score_band <> 'unknown'"),
        ),
        Index(
            "ix_product_created_at_desc_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        # Keyset pagination (D7). created_at is already covered by ix_product_created_at_desc_id.
        Index(
            "ix_product_score_id_keyset",
            text("score DESC"),
            text("id DESC"),
            postgresql_where=text("score IS NOT NULL"),
        ),
        Index(
            "ix_product_name_normalized_trgm",
            "name_normalized",
            postgresql_using="gin",
            postgresql_ops={"name_normalized": "gin_trgm_ops"},
        ),
        Index(
            "ix_product_score_dirty_partial",
            "score_dirty",
            postgresql_where=text("score_dirty = true"),
        ),
    )

    barcode: Mapped[str] = mapped_column(String(13), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    name_normalized: Mapped[str] = mapped_column(Text)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brand.id", ondelete="RESTRICT"), index=True
    )
    primary_category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("category.id", ondelete="RESTRICT"), index=True
    )
    image_url: Mapped[str | None] = mapped_column(Text)
    raw_ingredients_text: Mapped[str | None] = mapped_column(Text)

    # Precomputed by the scoring code, never by users or on each request.
    score: Mapped[int | None] = mapped_column(SmallInteger)  # 0-100, NULL = not scored
    score_band: Mapped[RiskLevel] = mapped_column(
        enum_type(RiskLevel),
        default=RiskLevel.UNKNOWN,
        server_default=RiskLevel.UNKNOWN.value,
    )
    # Share of ingredients we recognized (0-1). Low coverage => "insufficient data".
    score_coverage: Mapped[float | None] = mapped_column(Float)

    @validates("name")
    def _set_name_normalized(self, _key: str, value: str) -> str:
        self.name_normalized = normalize_name(value)
        return value

    scoring_version: Mapped[int | None] = mapped_column(SmallInteger)
    score_is_estimated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    score_dirty: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    source_lang: Mapped[str | None] = mapped_column(String(2))
    name_i18n: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    brand_source: Mapped[str | None] = mapped_column(Text)
    category_source: Mapped[str | None] = mapped_column(Text)
    field_provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        enum_type(EnrichmentStatus),
        default=EnrichmentStatus.PENDING,
        server_default=EnrichmentStatus.PENDING.value,
        index=True,
    )
    enrichment_version: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")

    image_source_url: Mapped[str | None] = mapped_column(Text)
    image_status: Mapped[ImageStatus] = mapped_column(
        enum_type(ImageStatus),
        default=ImageStatus.NONE,
        server_default=ImageStatus.NONE.value,
        index=True,
    )
    image_quality: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    data_quality: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    source: Mapped[ProductSource] = mapped_column(enum_type(ProductSource))
    source_id: Mapped[str | None] = mapped_column(String(64))

    brand: Mapped[Brand | None] = relationship(lazy="raise")
    primary_category: Mapped[Category | None] = relationship(lazy="raise")
    ingredients: Mapped[list[ProductIngredient]] = relationship(
        back_populates="product",
        order_by="ProductIngredient.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


class ProductIngredient(Base):
    """One row per ingredient on a product's label, in label order (descending
    concentration). `ingredient_id IS NULL` means "not recognized yet": those rows
    ARE the review queue for new aliases (no separate table needed).

    `ingredient_id` is a plain foreign key to a table owned by the `ingredients`
    module. There is deliberately NO relationship() to Ingredient: that would
    import another module's ORM model. Catalog asks the ingredients service.
    """

    __tablename__ = "product_ingredient"
    __table_args__ = (CheckConstraint("position >= 1", name="position_positive"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    raw_text: Mapped[str] = mapped_column(Text)
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingredient.id", ondelete="RESTRICT"), index=True
    )

    product: Mapped[Product] = relationship(back_populates="ingredients", lazy="raise")


class BarcodeMiss(Base):
    """Demand list: valid barcodes that were scanned but are not in the catalog."""

    __tablename__ = "barcode_miss"
    __table_args__ = (
        CheckConstraint("barcode ~ '^[0-9]{13}$'", name="barcode_gtin13"),
        CheckConstraint("count >= 1", name="count_positive"),
    )

    barcode: Mapped[str] = mapped_column(String(13), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())

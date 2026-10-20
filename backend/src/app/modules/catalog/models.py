import uuid

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RiskLevel
from app.core.orm import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.catalog.enums import ProductSource


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
<<<<<<< HEAD
=======
        # Keyset pagination (D7). created_at is already covered by ix_product_created_at_desc_id.
        Index(
            "ix_product_score_id_keyset",
            text("score DESC"),
            text("id DESC"),
            postgresql_where=text("score IS NOT NULL"),
        ),
>>>>>>> 1fd479cb87dbe5bed5fa5de16d93293b1e777d0e
    )

    barcode: Mapped[str] = mapped_column(String(13), unique=True)
    name: Mapped[str] = mapped_column(String(255))
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
    scoring_version: Mapped[int | None] = mapped_column(SmallInteger)

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

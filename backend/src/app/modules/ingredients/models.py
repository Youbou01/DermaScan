import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RiskLevel
from app.core.orm import Base, UUIDPrimaryKeyMixin, enum_check, enum_type


class Ingredient(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ingredient"
    __table_args__ = (
        enum_check("risk_level", RiskLevel),
        # Defensibility rule enforced by the database itself: an ingredient rated
        # moderate/high must cite where the rating comes from.
        CheckConstraint(
            "risk_level NOT IN ('moderate', 'high') OR source_ref IS NOT NULL",
            name="flagged_requires_source",
        ),
    )

    inci_name: Mapped[str] = mapped_column(String(255), unique=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_type(RiskLevel),
        default=RiskLevel.UNKNOWN,
        server_default=RiskLevel.UNKNOWN.value,
    )
    # e.g. "EU 1223/2009 Annex III, entry 12" or an SCCS opinion URL.
    source_ref: Mapped[str | None] = mapped_column(Text)

    # lazy="raise": relationships are never loaded implicitly. In async code an
    # implicit load crashes anyway, and this also surfaces N+1 queries early.
    # Load explicitly with selectinload() in the repository.
    aliases: Mapped[list[IngredientAlias]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    translations: Mapped[list[IngredientTranslation]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )


class IngredientAlias(UUIDPrimaryKeyMixin, Base):
    """One row per known name of an ingredient (INCI name, E-number, French name,
    spelling variant...). Invariant (kept by the service): every ingredient also has
    an alias for its own INCI name, so matching only ever queries this table."""

    __tablename__ = "ingredient_alias"
    __table_args__ = (
        # Trigram index: makes "which known names look like this text?" fast (suggestions,
        # ingredient search). Exact matching uses the unique index on normalized_alias.
        Index(
            "ix_ingredient_alias_normalized_alias_trgm",
            "normalized_alias",
            postgresql_using="gin",
            postgresql_ops={"normalized_alias": "gin_trgm_ops"},
        ),
    )

    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredient.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(255))
    # lowercase, unaccented, punctuation-stripped. Globally unique so a label name
    # can never be ambiguous between two ingredients.
    normalized_alias: Mapped[str] = mapped_column(String(255), unique=True)

    ingredient: Mapped[Ingredient] = relationship(back_populates="aliases", lazy="raise")


class IngredientTranslation(Base):
    __tablename__ = "ingredient_translation"
    __table_args__ = (CheckConstraint("locale ~ '^[a-z]{2}$'", name="locale_format"),)

    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredient.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(2), primary_key=True)  # 'en', 'fr', later 'ar'
    # Why the ingredient is rated the way it is. English is the fallback.
    rationale: Mapped[str] = mapped_column(Text)

import uuid
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.enums import RiskLevel
from app.core.orm import Base, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.ingredients.enums import AliasSource, RatingSource, ReviewStatus


def derive_risk_from_rating(rating: Decimal | float | None) -> RiskLevel:
    if rating is None:
        return RiskLevel.UNKNOWN
    val = float(rating)
    if val >= 7.0:
        return RiskLevel.LOW
    if val >= 4.0:
        return RiskLevel.MODERATE
    return RiskLevel.HIGH


class Ingredient(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ingredient"
    __table_args__ = (
        enum_check("risk_level", RiskLevel),
        enum_check("rating_source", RatingSource),
        enum_check("review_status", ReviewStatus),
        CheckConstraint(
            "rating IS NULL OR (rating >= 0 AND rating <= 10)",
            name="rating_range",
        ),
        CheckConstraint(
            "(rating IS NULL AND risk_level = 'unknown') "
            "OR (rating >= 7.0 AND risk_level = 'low') "
            "OR (rating >= 4.0 AND rating < 7.0 AND risk_level = 'moderate') "
            "OR (rating < 4.0 AND risk_level = 'high')",
            name="rating_risk_level_sync",
        ),
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
    source_ref: Mapped[str | None] = mapped_column(Text)

    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    rating_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    rating_source: Mapped[RatingSource] = mapped_column(
        enum_type(RatingSource),
        default=RatingSource.UNRATED,
        server_default=RatingSource.UNRATED.value,
    )
    rating_version: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    rating_model: Mapped[str | None] = mapped_column(Text)
    functions: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    is_prohibited: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    is_restricted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    is_allergen: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    cosing_id: Mapped[str | None] = mapped_column(Text, index=True)
    cas: Mapped[str | None] = mapped_column(Text)
    taxonomy_id: Mapped[str | None] = mapped_column(Text, index=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus),
        default=ReviewStatus.AUTO,
        server_default=ReviewStatus.AUTO.value,
    )

    @validates("rating")
    def _validate_rating(self, _key: str, value: Decimal | float | None) -> Decimal | None:
        if value is not None:
            expected_risk = derive_risk_from_rating(value)
            if getattr(self, "risk_level", None) != expected_risk:
                self.__dict__["risk_level"] = expected_risk
            return Decimal(str(value))
        if getattr(self, "risk_level", None) != RiskLevel.UNKNOWN:
            self.__dict__["risk_level"] = RiskLevel.UNKNOWN
        return None

    @validates("risk_level")
    def _validate_risk_level(self, _key: str, value: RiskLevel) -> RiskLevel:
        curr_rating = getattr(self, "rating", None)
        if curr_rating is None:
            if value == RiskLevel.LOW:
                self.__dict__["rating"] = Decimal("9.0")
            elif value == RiskLevel.MODERATE:
                self.__dict__["rating"] = Decimal("5.5")
            elif value == RiskLevel.HIGH:
                self.__dict__["rating"] = Decimal("2.0")
        return value

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
    __tablename__ = "ingredient_alias"
    __table_args__ = (
        enum_check("source", AliasSource),
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
    normalized_alias: Mapped[str] = mapped_column(String(255), unique=True)
    language: Mapped[str | None] = mapped_column(String(2))
    source: Mapped[AliasSource] = mapped_column(
        enum_type(AliasSource),
        default=AliasSource.SEED,
        server_default=AliasSource.SEED.value,
    )

    ingredient: Mapped[Ingredient] = relationship(back_populates="aliases", lazy="raise")


class IngredientTranslation(Base):
    __tablename__ = "ingredient_translation"
    __table_args__ = (CheckConstraint("locale ~ '^[a-z]{2}$'", name="locale_format"),)

    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredient.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(2), primary_key=True)
    rationale: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    concern_note: Mapped[str | None] = mapped_column(Text)

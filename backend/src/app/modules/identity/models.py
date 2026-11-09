import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.identity.enums import SkinType


class UserAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_account"
    # Case-insensitive uniqueness: "Ada@x.com" and "ada@x.com" are the same account.
    __table_args__ = (Index("uq_user_account_email_lower", text("lower(email)"), unique=True),)

    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))


class UserProfile(Base):
    __tablename__ = "user_profile"
    __table_args__ = (enum_check("skin_type", SkinType),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    skin_type: Mapped[SkinType | None] = mapped_column(enum_type(SkinType))
    is_pregnant_or_nursing: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    health_conditions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    # No created_at, so TimestampMixin does not fit; same pattern as the mixin.
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class UserAllergy(Base):
    __tablename__ = "user_allergy"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredient.id", ondelete="RESTRICT"), primary_key=True
    )


class UserBlacklistProduct(Base):
    __tablename__ = "user_blacklist_product"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True
    )
    reason: Mapped[str | None] = mapped_column(Text)


class UserBlacklistIngredient(Base):
    __tablename__ = "user_blacklist_ingredient"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredient.id", ondelete="RESTRICT"), primary_key=True
    )
    reason: Mapped[str | None] = mapped_column(Text)

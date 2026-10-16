"""SQLAlchemy declarative base, shared column mixins and column helpers."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from sqlalchemy import CheckConstraint, DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names: without this, Alembic cannot reliably drop or
# alter constraints later, and every developer's database ends up different.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {datetime: DateTime(timezone=True)}


class UUIDPrimaryKeyMixin:
    """UUIDv7 primary key: time-ordered (index-friendly), not guessable/enumerable."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7, sort_order=-100)


class TimestampMixin:
    """Filled by the database. Note: `onupdate` only fires for ORM updates; bulk
    Core `UPDATE` statements must set `updated_at` explicitly."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), sort_order=100)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), sort_order=101
    )


def enum_type(enum_cls: type[StrEnum]) -> Enum:
    """Store a StrEnum as VARCHAR (not a native PG enum, which is painful to evolve:
    `ALTER TYPE`, not auto-detected by Alembic). Pair every use with `enum_check()`
    in the model's `__table_args__` to get the database-level constraint.
    Call once per column: do not share one Enum instance between columns.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=False,  # explicit, single constraint via enum_check() instead
        validate_strings=True,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )


def enum_check(column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    """`CHECK (column IN (...))`, named `ck_<table>_<column>` by the naming convention."""
    allowed = ", ".join(f"'{member.value}'" for member in enum_cls)
    return CheckConstraint(f"{column} IN ({allowed})", name=column)

"""Persistence models owned by the routines module."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.orm import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.routines.enums import RoutineSlot, RoutineStepType


class Routine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "routine"
    __table_args__ = (
        enum_check("slot", RoutineSlot),
        UniqueConstraint("user_id", "slot", name="uq_routine_user_slot"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), index=True
    )
    slot: Mapped[RoutineSlot] = mapped_column(enum_type(RoutineSlot))
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    steps: Mapped[list[RoutineStep]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
        order_by="RoutineStep.step_order",
    )


class RoutineStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "routine_step"
    __table_args__ = (
        enum_check("step_type", RoutineStepType),
        CheckConstraint("step_order >= 1", name="step_order_positive"),
        UniqueConstraint("routine_id", "step_order", name="uq_routine_step_order"),
    )

    routine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routine.id", ondelete="CASCADE"), index=True
    )
    step_order: Mapped[int] = mapped_column(SmallInteger)
    step_type: Mapped[RoutineStepType] = mapped_column(enum_type(RoutineStepType))
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    routine: Mapped[Routine] = relationship(back_populates="steps", lazy="raise")


class RoutineCompletionLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "routine_completion_log"
    __table_args__ = (
        UniqueConstraint("routine_id", "completed_date", name="uq_routine_completion_day"),
    )

    routine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routine.id", ondelete="CASCADE"), index=True
    )
    completed_date: Mapped[date] = mapped_column(Date)


class RoutineShareLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "routine_share_link"
    __table_args__ = (
        CheckConstraint("view_count >= 0", name="view_count_nonnegative"),
        Index("ix_routine_share_link_routine_created", "routine_id", "created_at"),
    )

    routine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routine.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    view_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

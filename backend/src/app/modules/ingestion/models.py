import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.ingestion.enums import QuarantineStatus, RawProductSource


class RawProduct(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "raw_product"
    __table_args__ = (
        enum_check("source", RawProductSource),
        UniqueConstraint(
            "source", "source_id", "content_hash", name="uq_raw_product_source_source_id_hash"
        ),
        Index("ix_raw_product_source_source_id", "source", "source_id"),
    )

    source: Mapped[RawProductSource] = mapped_column(enum_type(RawProductSource))
    source_id: Mapped[str] = mapped_column(String(128))
    url: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class IngestionRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ingestion_run"

    source: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")


class QuarantineItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quarantine_item"
    __table_args__ = (
        enum_check("status", QuarantineStatus),
        Index("ix_quarantine_item_status_created_at", "status", "created_at"),
    )

    raw_product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("raw_product.id", ondelete="SET NULL"), index=True
    )
    stage: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[QuarantineStatus] = mapped_column(
        enum_type(QuarantineStatus),
        default=QuarantineStatus.PENDING,
        server_default=QuarantineStatus.PENDING.value,
        index=True,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class ScrapeStaging(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "scrape_staging"

    url: Mapped[str] = mapped_column(Text, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    extracted_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="SET NULL"), index=True
    )


class CalibrationReference(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "calibration_reference"

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product.id", ondelete="SET NULL"), index=True
    )
    barcode: Mapped[str] = mapped_column(String(13), index=True)
    reference_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    source: Mapped[str] = mapped_column(String(64), index=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Integer, PrimaryKeyConstraint, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base


class LLMCache(Base):
    __tablename__ = "llm_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(128))
    response_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class LLMUsage(Base):
    __tablename__ = "llm_usage"
    __table_args__ = (PrimaryKeyConstraint("provider", "date"),)

    provider: Mapped[str] = mapped_column(String(64))
    date: Mapped[date] = mapped_column(Date)
    requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

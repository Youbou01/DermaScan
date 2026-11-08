import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.modules.ingestion.enums import QuarantineStatus, RawProductSource


class QuarantineItemOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    raw_product_id: uuid.UUID | None
    stage: str
    reason: str
    payload: dict[str, Any]
    status: QuarantineStatus
    reviewed_by: str | None = None
    created_at: datetime


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    source: str
    started_at: datetime
    finished_at: datetime | None = None
    counters: dict[str, Any]


class RawProductOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    source: RawProductSource
    source_id: str
    url: str | None
    payload: dict[str, Any]
    content_hash: str
    fetched_at: datetime

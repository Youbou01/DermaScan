import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.enums import QuarantineStatus
from app.modules.ingestion.models import IngestionRun, QuarantineItem, RawProduct
from app.modules.ingestion.repository import IngestionRepository
from app.modules.ingestion.schemas import (
    IngestionRunOut,
    QuarantineItemOut,
    RawProductOut,
)


def _to_raw_out(raw: RawProduct) -> RawProductOut:
    return RawProductOut(
        id=raw.id,
        source=raw.source,
        source_id=raw.source_id,
        url=raw.url,
        payload=raw.payload,
        content_hash=raw.content_hash,
        fetched_at=raw.fetched_at,
    )


def _to_quarantine_out(q: QuarantineItem) -> QuarantineItemOut:
    return QuarantineItemOut(
        id=q.id,
        raw_product_id=q.raw_product_id,
        stage=q.stage,
        reason=q.reason,
        payload=q.payload,
        status=q.status,
        reviewed_by=q.reviewed_by,
        created_at=q.created_at,
    )


def _to_run_out(r: IngestionRun) -> IngestionRunOut:
    return IngestionRunOut(
        id=r.id,
        source=r.source,
        started_at=r.started_at,
        finished_at=r.finished_at,
        counters=r.counters,
    )


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = IngestionRepository(session)

    async def get_raw_product(self, raw_id: uuid.UUID) -> RawProductOut | None:
        raw = await self._repo.get_raw_product_by_id(raw_id)
        return _to_raw_out(raw) if raw else None

    async def quarantine(
        self,
        raw_product_id: uuid.UUID | None,
        stage: str,
        reason: str,
        payload: dict[str, Any],
    ) -> QuarantineItemOut:
        item = await self._repo.create_quarantine_item(
            raw_product_id=raw_product_id,
            stage=stage,
            reason=reason,
            payload=payload,
        )
        return _to_quarantine_out(item)

    async def list_quarantine(
        self,
        status: QuarantineStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[QuarantineItemOut]:
        items = await self._repo.list_quarantine_items(status=status, limit=limit, offset=offset)
        return [_to_quarantine_out(i) for i in items]

    async def get_quarantine_item(self, quarantine_id: uuid.UUID) -> QuarantineItemOut | None:
        item = await self._repo.get_quarantine_item(quarantine_id)
        return _to_quarantine_out(item) if item else None

    async def approve_quarantine(
        self, quarantine_id: uuid.UUID, reviewed_by: str | None = None
    ) -> bool:
        item = await self._repo.update_quarantine_status(
            quarantine_id=quarantine_id,
            status=QuarantineStatus.APPROVED,
            reviewed_by=reviewed_by,
        )
        return item is not None

    async def reject_quarantine(
        self, quarantine_id: uuid.UUID, reviewed_by: str | None = None
    ) -> bool:
        item = await self._repo.update_quarantine_status(
            quarantine_id=quarantine_id,
            status=QuarantineStatus.REJECTED,
            reviewed_by=reviewed_by,
        )
        return item is not None

    async def create_run(self, source: str) -> IngestionRunOut:
        run = await self._repo.create_run(source=source)
        return _to_run_out(run)

    async def finish_run(
        self, run_id: uuid.UUID, counters: dict[str, Any]
    ) -> IngestionRunOut | None:
        run = await self._repo.finish_run(run_id=run_id, counters=counters)
        return _to_run_out(run) if run else None

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[IngestionRunOut]:
        runs = await self._repo.list_runs(limit=limit, offset=offset)
        return [_to_run_out(r) for r in runs]

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.enums import QuarantineStatus, RawProductSource
from app.modules.ingestion.models import IngestionRun, QuarantineItem, RawProduct


class IngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_raw_product_by_id(self, raw_id: uuid.UUID) -> RawProduct | None:
        return await self._session.get(RawProduct, raw_id)

    async def get_raw_product_by_source_id(
        self, source: RawProductSource, source_id: str
    ) -> RawProduct | None:
        stmt = (
            select(RawProduct)
            .where(RawProduct.source == source, RawProduct.source_id == source_id)
            .order_by(RawProduct.fetched_at.desc())
            .limit(1)
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_quarantine_item(
        self,
        raw_product_id: uuid.UUID | None,
        stage: str,
        reason: str,
        payload: dict[str, Any],
    ) -> QuarantineItem:
        item = QuarantineItem(
            raw_product_id=raw_product_id,
            stage=stage,
            reason=reason,
            payload=payload,
            status=QuarantineStatus.PENDING,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_quarantine_item(self, quarantine_id: uuid.UUID) -> QuarantineItem | None:
        return await self._session.get(QuarantineItem, quarantine_id)

    async def list_quarantine_items(
        self,
        status: QuarantineStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[QuarantineItem]:
        stmt = select(QuarantineItem).order_by(QuarantineItem.created_at.desc())
        if status is not None:
            stmt = stmt.where(QuarantineItem.status == status)
        stmt = stmt.limit(limit).offset(offset)
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def update_quarantine_status(
        self,
        quarantine_id: uuid.UUID,
        status: QuarantineStatus,
        reviewed_by: str | None = None,
    ) -> QuarantineItem | None:
        item = await self._session.get(QuarantineItem, quarantine_id)
        if item is None:
            return None
        item.status = status
        item.reviewed_by = reviewed_by
        await self._session.flush()
        return item

    async def create_run(self, source: str) -> IngestionRun:
        run = IngestionRun(
            source=source,
            started_at=datetime.now(UTC),
            counters={},
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def finish_run(self, run_id: uuid.UUID, counters: dict[str, Any]) -> IngestionRun | None:
        run = await self._session.get(IngestionRun, run_id)
        if run is None:
            return None
        run.finished_at = datetime.now(UTC)
        run.counters = counters
        await self._session.flush()
        return run

    async def list_runs(self, limit: int = 50, offset: int = 0) -> Sequence[IngestionRun]:
        stmt = (
            select(IngestionRun)
            .order_by(IngestionRun.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

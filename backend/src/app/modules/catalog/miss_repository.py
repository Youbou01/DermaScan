"""SQL for the barcode demand list. Private: used by `CatalogService`."""

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import BarcodeMiss


class BarcodeMissRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, barcode: str) -> None:
        """Insert the barcode, or increment its counter if it was already missed."""
        stmt = insert(BarcodeMiss).values(barcode=barcode)
        stmt = stmt.on_conflict_do_update(
            index_elements=[BarcodeMiss.barcode],
            set_={"count": BarcodeMiss.count + 1, "last_seen_at": func.now()},
        )
        await self._session.execute(stmt)

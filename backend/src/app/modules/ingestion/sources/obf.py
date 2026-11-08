import csv
import gzip
import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import structlog
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.enums import RawProductSource
from app.modules.ingestion.models import RawProduct
from app.modules.ingestion.sources.base import (
    RawRecord,
    SourceAdapter,
    compute_content_hash,
)

logger = structlog.get_logger(__name__)

OBF_API_URL = "https://world.openbeautyfacts.org/api/v2/product/{code}.json"
OBF_USER_AGENT = "DermaScan-Ingestion/1.0 (Free Skincare Intelligence)"


class OBFSourceAdapter(SourceAdapter):
    """Adapter for Open Beauty Facts bulk dumps (CSV/JSONL) and live barcode API."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = client
        self._timeout = timeout

    @property
    def source_name(self) -> str:
        return RawProductSource.OPEN_BEAUTY_FACTS.value

    def to_raw(self, payload: dict[str, Any], url: str | None = None) -> RawRecord:
        source_id = str(payload.get("code") or payload.get("id") or "").strip()
        content_hash = compute_content_hash(payload)
        return RawRecord(
            source=self.source_name,
            source_id=source_id,
            content_hash=content_hash,
            payload=payload,
            url=url,
        )

    async def fetch(self, source_id: str) -> dict[str, Any] | None:
        clean_code = source_id.strip()
        if not clean_code:
            return None

        url = OBF_API_URL.format(code=clean_code)
        headers = {"User-Agent": OBF_USER_AGENT}

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)

        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1 and "product" in data:
                    prod = data["product"]
                    if isinstance(prod, dict):
                        return prod
            return None
        except httpx.HTTPError as exc:
            logger.warning("obf_fetch_http_error", code=clean_code, error=str(exc))
            return None
        finally:
            if owns_client:
                await client.aclose()

    async def discover(
        self,
        dump_path: Path | str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        if not dump_path:
            return

        resolved_path = Path(dump_path)
        if not resolved_path.exists():  # noqa: ASYNC240
            logger.error("obf_dump_file_not_found", path=str(resolved_path))
            return

        is_gzip = resolved_path.suffix == ".gz"
        name_lower = resolved_path.name.lower()

        if ".jsonl" in name_lower:
            async for record in self._stream_jsonl(resolved_path, is_gzip):
                yield record
        else:
            async for record in self._stream_csv(resolved_path, is_gzip):
                yield record

    async def _stream_jsonl(
        self,
        path: Path,
        is_gzip: bool,
    ) -> AsyncIterator[dict[str, Any]]:
        opener = gzip.open if is_gzip else open
        with opener(path, mode="rt", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        yield parsed
                except json.JSONDecodeError:
                    continue

    async def _stream_csv(
        self,
        path: Path,
        is_gzip: bool,
    ) -> AsyncIterator[dict[str, Any]]:
        opener = gzip.open if is_gzip else open
        with opener(path, mode="rt", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t" if "\t" in f.readline() else ",")
            f.seek(0)
            for row in reader:
                if row and any(row.values()):
                    yield dict(row)


async def store_raw_product(
    session: AsyncSession,
    record: RawRecord,
) -> uuid.UUID | None:
    """Store raw product idempotently using (source, source_id, content_hash).

    Returns UUID of the inserted row, or None if row already existed.
    """
    new_id = uuid.uuid7()
    stmt = (
        insert(RawProduct)
        .values(
            id=new_id,
            source=RawProductSource(record.source),
            source_id=record.source_id,
            url=record.url,
            payload=record.payload,
            content_hash=record.content_hash,
        )
        .on_conflict_do_nothing(
            index_elements=[RawProduct.source, RawProduct.source_id, RawProduct.content_hash]
        )
        .returning(RawProduct.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

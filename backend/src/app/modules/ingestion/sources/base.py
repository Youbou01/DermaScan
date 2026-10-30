import hashlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


def compute_content_hash(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of a JSON-serializable dictionary."""
    canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class RawRecord:
    source: str
    source_id: str
    content_hash: str
    payload: dict[str, Any]
    url: str | None = None


class SourceAdapter(Protocol):
    @property
    def source_name(self) -> str: ...

    def discover(
        self,
        dump_path: Path | str | None = None,
    ) -> AsyncIterator[dict[str, Any]]: ...

    async def fetch(self, source_id: str) -> dict[str, Any] | None: ...

    def to_raw(self, payload: dict[str, Any], url: str | None = None) -> RawRecord: ...

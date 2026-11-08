import gzip
import json
from pathlib import Path

import pytest

from app.modules.ingestion.sources.base import compute_content_hash
from app.modules.ingestion.sources.obf import OBFSourceAdapter


def test_compute_content_hash_deterministic() -> None:
    d1 = {"a": 1, "b": "text", "c": [1, 2, 3]}
    d2 = {"c": [1, 2, 3], "a": 1, "b": "text"}
    assert compute_content_hash(d1) == compute_content_hash(d2)
    assert len(compute_content_hash(d1)) == 64


def test_obf_adapter_to_raw() -> None:
    adapter = OBFSourceAdapter()
    payload = {"code": "3337872412999", "product_name": "Hydraphase"}
    raw = adapter.to_raw(payload, url="https://example.com/test")

    assert raw.source == "open_beauty_facts"
    assert raw.source_id == "3337872412999"
    assert raw.payload == payload
    assert raw.url == "https://example.com/test"
    assert len(raw.content_hash) == 64


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_gzip_text(path: Path, content: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(content)


@pytest.mark.asyncio
async def test_obf_stream_jsonl(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "dump.jsonl"
    lines = [
        {"code": "111", "product_name": "Prod 1"},
        {"code": "222", "product_name": "Prod 2"},
    ]
    content = "\n".join(json.dumps(item) for item in lines) + "\n"
    _write_text(jsonl_file, content)

    adapter = OBFSourceAdapter()
    results = [record async for record in adapter.discover(dump_path=jsonl_file)]
    assert len(results) == 2
    assert results[0]["code"] == "111"
    assert results[1]["code"] == "222"


@pytest.mark.asyncio
async def test_obf_stream_jsonl_gzip(tmp_path: Path) -> None:
    gz_file = tmp_path / "dump.jsonl.gz"
    lines = [
        {"code": "333", "product_name": "Gzip Prod"},
    ]
    content = "\n".join(json.dumps(item) for item in lines) + "\n"
    _write_gzip_text(gz_file, content)

    adapter = OBFSourceAdapter()
    results = [record async for record in adapter.discover(dump_path=gz_file)]
    assert len(results) == 1
    assert results[0]["code"] == "333"


@pytest.mark.asyncio
async def test_obf_stream_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "dump.csv"
    _write_text(csv_file, "code\tproduct_name\n444\tCSV Prod\n")

    adapter = OBFSourceAdapter()
    results = [record async for record in adapter.discover(dump_path=csv_file)]
    assert len(results) == 1
    assert results[0]["code"] == "444"
    assert results[0]["product_name"] == "CSV Prod"

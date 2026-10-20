from pathlib import Path

IMPORTER = Path(__file__).resolve().parents[2] / "src/app/modules/ingestion/importer.py"


def test_importer_sets_name_normalized_on_insert_and_update() -> None:
    """name_normalized is NOT NULL and filled by a Python validator, which raw SQL skips."""
    source = IMPORTER.read_text()
    assert ":name_normalized" in source
    assert source.count("name_normalized=normalize_name(name)") == 2

from pathlib import Path

IMPORTER = Path(__file__).resolve().parents[2] / "src/app/modules/ingestion/importer.py"
SERVICE = Path(__file__).resolve().parents[2] / "src/app/modules/catalog/service.py"


def test_importer_uses_clean_service_without_raw_sql() -> None:
    """Importer never uses raw SQL strings, and service sets name_normalized on upsert."""
    importer_source = IMPORTER.read_text()
    assert "text(" not in importer_source
    assert "SELECT " not in importer_source
    assert "INSERT INTO" not in importer_source

    service_source = SERVICE.read_text()
    assert "name_normalized=normalize_name(data.name)" in service_source

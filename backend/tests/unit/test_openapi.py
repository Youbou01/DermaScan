import json
from pathlib import Path

from app.core.config import Settings
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[2]
DOCS_OPENAPI = BACKEND_DIR.parent / "docs" / "openapi.json"


def test_committed_openapi_is_not_stale() -> None:
    assert DOCS_OPENAPI.exists(), "docs/openapi.json does not exist. Run scripts/export_openapi.py."
    app = create_app(Settings())
    expected = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    committed = DOCS_OPENAPI.read_text(encoding="utf-8")
    assert committed == expected, (
        "docs/openapi.json is stale. Run: uv run python scripts/export_openapi.py"
    )

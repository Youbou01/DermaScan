"""Export the OpenAPI schema with sorted keys to docs/openapi.json and mobile/openapi.json."""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from app.core.config import Settings
from app.main import create_app


def export_openapi() -> str:
    app = create_app(Settings())
    schema = app.openapi()
    content = json.dumps(schema, indent=2, sort_keys=True) + "\n"

    docs_path = ROOT_DIR / "docs" / "openapi.json"
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(content, encoding="utf-8")

    mobile_path = ROOT_DIR / "mobile" / "openapi.json"
    if mobile_path.parent.exists():
        mobile_path.write_text(content, encoding="utf-8")

    return content


if __name__ == "__main__":
    export_openapi()
    print("OpenAPI schema exported to docs/openapi.json and mobile/openapi.json")  # noqa: T201

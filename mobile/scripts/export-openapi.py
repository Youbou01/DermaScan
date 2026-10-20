"""Export the backend's FastAPI contract for the mobile OpenAPI type generator."""

import json
from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    settings = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")
    schema = create_app(settings).openapi()
    output_path = Path(__file__).resolve().parents[1] / "openapi.json"
    output_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

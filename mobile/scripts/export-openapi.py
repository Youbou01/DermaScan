"""Export the backend's FastAPI contract for the mobile OpenAPI type generator."""

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    db_url = os.environ.get("DATABASE_URL") or "postgresql+asyncpg://user:pass@localhost/db"
    settings = Settings(database_url=db_url)
    schema = create_app(settings).openapi()
    output_path = Path(__file__).resolve().parents[1] / "openapi.json"
    output_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI schema successfully exported to {output_path}")


if __name__ == "__main__":
    main()

"""Idempotent seed loader delegating to import_cosing.load_seed_data (case-insensitive)."""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from scripts.import_cosing import load_seed_data

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory


async def main() -> None:
    engine = create_engine(Settings())
    session_factory = create_session_factory(engine)
    async with session_factory() as db:
        await load_seed_data(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

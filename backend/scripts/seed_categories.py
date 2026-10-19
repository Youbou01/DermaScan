"""Load the versioned category tree (idempotent).

uv run python scripts/seed_categories.py
"""

import asyncio

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.modules.ingestion.seed_categories import seed_categories


async def main() -> None:
    engine = create_engine(get_settings())
    async with create_session_factory(engine)() as session:
        touched = await seed_categories(session)
    await engine.dispose()
    print(f"Categories seed finished (touched={touched}).")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())

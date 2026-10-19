import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.usefixtures("migrated_database")


async def test_search_extensions_are_installed_by_the_migrations(db_session: AsyncSession) -> None:
    result = await db_session.scalars(
        text("SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'unaccent')")
    )
    assert set(result) == {"pg_trgm", "unaccent"}


async def test_trigram_index_exists_on_alias_names(db_session: AsyncSession) -> None:
    definition = await db_session.scalar(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE indexname = 'ix_ingredient_alias_normalized_alias_trgm'"
        )
    )
    assert definition is not None
    assert "gin" in definition
    assert "gin_trgm_ops" in definition

"""Fixtures for tests that need a real PostgreSQL.

Where the database comes from:
  * `TEST_DATABASE_URL` set (CI uses this): that database is used. Its name must contain
    "test" so a typo can never point the suite at your dev data.
  * not set (normal local run): a throwaway PostgreSQL container is started with
    testcontainers (needs Docker running).

The schema is built once per run by the real Alembic migrations, so migrations are
exercised by every test run. Each test runs inside a transaction that is rolled back,
so tests never see each other's data and never need cleanup.
"""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.dependencies import get_session
from app.main import create_app

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        if "test" not in (make_url(explicit).database or ""):
            pytest.exit("TEST_DATABASE_URL must point to a database whose name contains 'test'")
        yield explicit
        return

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:18", driver="asyncpg", dbname="skincare_test") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    """Runs `alembic upgrade head` once. A sync fixture on purpose: Alembic's env.py
    starts its own event loop, which is not allowed inside a running one."""
    config = Config(
        str(BACKEND_ROOT / "alembic.ini"), toml_file=str(BACKEND_ROOT / "pyproject.toml")
    )
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    return database_url


@pytest.fixture
async def db_session(migrated_database: str) -> AsyncIterator[AsyncSession]:
    """A session whose work is rolled back when the test ends. `commit()` inside the
    test only releases a savepoint, so service code that commits still works."""
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    async with engine.connect() as connection:
        outer = await connection.begin()
        session = AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
    await engine.dispose()


@pytest.fixture
async def client(
    migrated_database: str, db_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client wired to the real app, using the test's rolled-back session."""
    settings = Settings(_env_file=None, app_env="test", database_url=migrated_database)
    app = create_app(settings)

    async def use_test_session() -> AsyncIterator[AsyncSession]:
        # A real request starts with a fresh session: nothing cached in its identity map.
        # Without this, objects the test created would be reused as they are (e.g. a
        # collection in insertion order instead of the query's ORDER BY) and the endpoint
        # would be tested against a situation that never happens in production.
        db_session.expunge_all()
        yield db_session

    app.dependency_overrides[get_session] = use_test_session
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

"""Engine and session factory creation. No module-level globals: the app factory
creates them at startup and stores them on `app.state`, which keeps tests simple."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        str(settings.database_url), echo=settings.db_echo, pool_pre_ping=True
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: attributes stay readable after commit (required for async).
    return async_sessionmaker(engine, expire_on_commit=False)

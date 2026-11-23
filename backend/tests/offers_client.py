"""HTTP client for the offers API tests, with the offers router registered.

The router is registered in app/api/v1/router.py by Dev 4 (see the integration note).
Until then these tests add it themselves, and only if the app does not have it yet,
so they pass before and after that registration.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_session
from app.main import create_app
from app.modules.offers import offers_router


@asynccontextmanager
async def offers_http_client(
    database_url: str, db_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(_env_file=None, app_env="test", database_url=database_url)
    app = create_app(settings)
    if not any(getattr(route, "path", "").endswith("/offers") for route in app.routes):
        app.include_router(offers_router, prefix="/api/v1/products", tags=["products"])

    async def use_test_session() -> AsyncIterator[AsyncSession]:
        db_session.expunge_all()
        yield db_session

    app.dependency_overrides[get_session] = use_test_session
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

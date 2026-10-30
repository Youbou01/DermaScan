"""Application factory.

Run with:  uvicorn app.main:create_app --factory --reload
(a factory avoids reading settings at import time, which keeps tests clean).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import health
from app.api.error_handlers import register_error_handlers
from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.dependencies import get_session
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.modules.catalog import CatalogService, ProductDetail
from app.modules.catalog.router import get_catalog_service
from app.modules.ingestion import handle_barcode_miss_fallback


def operation_id(route: APIRoute) -> str:
    """OpenAPI operationId, e.g. `products_get_product_by_barcode`. The default is a long
    mouthful (`..._api_v1_products_by_barcode__barcode__get`) that would become the name
    of every generated client function."""
    group = str(route.tags[0]) if route.tags else "app"
    return f"{group}_{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(app.state.settings)
    app.state.session_factory = create_session_factory(engine)
    app.state.http_client = httpx.AsyncClient(timeout=5.0)
    try:
        yield
    finally:
        await app.state.http_client.aclose()
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    app = FastAPI(
        title="Skincare API",
        version="0.1.0",
        lifespan=lifespan,
        generate_unique_id_function=operation_id,
    )
    app.state.settings = settings
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_v1_router, prefix="/api/v1")

    if settings.enable_obf_fallback and settings.app_env != "test":

        async def get_catalog_service_with_fallback(
            session: Annotated[AsyncSession, Depends(get_session)],
        ) -> CatalogService:
            http_client: httpx.AsyncClient | None = getattr(app.state, "http_client", None)

            async def fallback(barcode: str, locale: str) -> ProductDetail | None:
                return await handle_barcode_miss_fallback(
                    session, barcode, locale, client=http_client
                )

            return CatalogService(session, fallback_handler=fallback)

        app.dependency_overrides[get_catalog_service] = get_catalog_service_with_fallback

    return app

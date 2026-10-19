"""Application factory.

Run with:  uvicorn app.main:create_app --factory --reload
(a factory avoids reading settings at import time, which keeps tests clean).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.api import health
from app.api.error_handlers import register_error_handlers
from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


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
    try:
        yield
    finally:
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
    return app

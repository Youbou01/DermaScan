from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.sessions import SessionMiddleware

from app.api.admin.auth import AdminAuth
from app.api.admin.routes import router as admin_router
from app.core.config import Settings
from app.modules.catalog import ProductAdmin
from app.modules.ingestion import (
    IngestionRunAdmin,
    QuarantineItemAdmin,
    RawProductAdmin,
)
from app.modules.ingredients import IngredientAdmin


def init_admin_ui(admin_app: FastAPI, engine: AsyncEngine, settings: Settings) -> Admin:
    session_secret = settings.admin_api_key or "admin-session-secret-key-12345"
    auth_backend = AdminAuth(
        secret_key=session_secret,
        user=settings.admin_ui_user or "admin",
        password=settings.admin_ui_password or "admin",
    )
    admin_ui = Admin(
        app=admin_app,
        engine=engine,
        base_url="/ui",
        title="DermaScan Admin",
        authentication_backend=auth_backend,
    )
    admin_ui.add_view(QuarantineItemAdmin)
    admin_ui.add_view(RawProductAdmin)
    admin_ui.add_view(IngestionRunAdmin)
    admin_ui.add_view(IngredientAdmin)
    admin_ui.add_view(ProductAdmin)
    admin_app.state.admin_ui = admin_ui
    return admin_ui


def create_admin_app(settings: Settings, engine: AsyncEngine | None = None) -> FastAPI:
    admin_app = FastAPI(
        title="DermaScan Admin API",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    admin_app.state.settings = settings
    admin_app.include_router(admin_router)

    session_secret = settings.admin_api_key or "admin-session-secret-key-12345"
    admin_app.add_middleware(SessionMiddleware, secret_key=session_secret)

    if engine is not None:
        init_admin_ui(admin_app, engine, settings)

    return admin_app

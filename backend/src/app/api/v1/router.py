"""Aggregates every module's router under /api/v1."""

from fastapi import APIRouter

from app.api.v1.contributions import router as contributions_router
from app.modules.catalog import catalog_router, categories_router, home_router

router = APIRouter()

router.include_router(categories_router, prefix="/categories", tags=["categories"])
router.include_router(home_router, prefix="/home", tags=["home"])
router.include_router(catalog_router, prefix="/products", tags=["products"])
router.include_router(contributions_router, prefix="/contributions", tags=["contributions"])

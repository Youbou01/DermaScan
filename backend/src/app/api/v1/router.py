"""Aggregates every module's router under /api/v1."""

from fastapi import APIRouter

from app.modules.catalog import catalog_router, categories_router

router = APIRouter()

router.include_router(categories_router, prefix="/categories", tags=["categories"])
router.include_router(catalog_router, prefix="/products", tags=["products"])

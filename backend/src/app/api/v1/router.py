"""Aggregates every module's router under /api/v1."""

from fastapi import APIRouter

router = APIRouter()

# Module routers are mounted here as they are built, e.g.:
# router.include_router(catalog_router, prefix="/products", tags=["products"])

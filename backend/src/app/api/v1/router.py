"""Aggregates every module's router under /api/v1."""

from fastapi import APIRouter

from app.api.v1.contributions import router as contributions_router
from app.modules.catalog import catalog_router, categories_router, home_router
from app.modules.dermatologists import dermatologists_router
from app.modules.enrichment import analysis_router
from app.modules.identity import auth_router, profile_router, suitability_router
from app.modules.personal_library import personal_library_router
from app.modules.routines import routines_router

router = APIRouter()

router.include_router(categories_router, prefix="/categories", tags=["categories"])
router.include_router(home_router, prefix="/home", tags=["home"])
router.include_router(catalog_router, prefix="/products", tags=["products"])
router.include_router(suitability_router, prefix="/products", tags=["products"])
router.include_router(contributions_router, prefix="/contributions", tags=["contributions"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(profile_router, prefix="/profile", tags=["profile"])
router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
router.include_router(personal_library_router, prefix="/library", tags=["library"])
router.include_router(dermatologists_router, prefix="/dermatologists", tags=["dermatologists"])
router.include_router(routines_router, prefix="/routines", tags=["routines"])

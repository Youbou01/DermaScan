"""Dermatologist module: curated credentials and informational recommendations."""

from app.modules.dermatologists.router import router as dermatologists_router
from app.modules.dermatologists.service import DermatologistsService

__all__ = ["DermatologistsService", "dermatologists_router"]

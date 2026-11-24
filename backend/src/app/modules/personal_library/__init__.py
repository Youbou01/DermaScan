"""Personal library module: saved products and recently viewed history."""

from app.modules.personal_library.router import router as personal_library_router
from app.modules.personal_library.service import PersonalLibraryService

__all__ = ["PersonalLibraryService", "personal_library_router"]

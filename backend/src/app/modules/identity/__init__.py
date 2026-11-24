"""Identity module: accounts, health profile and blacklist.

Owns tables: user_account, user_profile, user_allergy,
user_blacklist_product, user_blacklist_ingredient.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from
here, never from models or repository.
"""

from app.modules.identity.router import auth_router as auth_router
from app.modules.identity.router import profile_router as profile_router
from app.modules.identity.router import suitability_router as suitability_router
from app.modules.identity.service import IdentityService as IdentityService

__all__ = [
    "IdentityService",
    "auth_router",
    "profile_router",
    "suitability_router",
]

"""Identity module: accounts, health profile and blacklist.

Owns tables: user_account, user_profile, user_allergy,
user_blacklist_product, user_blacklist_ingredient.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from
here, never from models or repository.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.router import auth_router as auth_router
from app.modules.identity.router import profile_router as profile_router
from app.modules.identity.router import suitability_router as suitability_router
from app.modules.identity.service import IdentityService


async def get_saved_skin_type(session: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Public, minimized profile lookup for features that personalize by skin type."""
    return await IdentityService(session).get_saved_skin_type(user_id)


__all__ = [
    "auth_router",
    "get_saved_skin_type",
    "profile_router",
    "suitability_router",
]

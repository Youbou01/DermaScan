"""SQL for the identity module. Private: the outside world uses `IdentityService`."""

import uuid
from collections.abc import Collection

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.enums import SkinType
from app.modules.identity.models import (
    UserAccount,
    UserAllergy,
    UserBlacklistIngredient,
    UserBlacklistProduct,
    UserProfile,
)


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ accounts
    async def get_user_by_id(self, user_id: uuid.UUID) -> UserAccount | None:
        return await self._session.get(UserAccount, user_id)

    async def get_user_by_email(self, email: str) -> UserAccount | None:
        """Case-insensitive, like the unique index on lower(email)."""
        return await self._session.scalar(
            select(UserAccount).where(func.lower(UserAccount.email) == email.lower())
        )

    async def add_user(self, email: str, password_hash: str, display_name: str) -> UserAccount:
        """Flushes, so a duplicate email raises IntegrityError here (the service handles it)."""
        user = UserAccount(email=email, password_hash=password_hash, display_name=display_name)
        self._session.add(user)
        await self._session.flush()
        return user

    # ------------------------------------------------------------------ profile
    async def get_profile(self, user_id: uuid.UUID) -> UserProfile | None:
        return await self._session.get(UserProfile, user_id)

    async def save_profile(
        self,
        user_id: uuid.UUID,
        skin_type: SkinType | None,
        is_pregnant_or_nursing: bool,
        health_conditions: list[str],
    ) -> UserProfile:
        """Insert or update the single profile row of a user, then flush."""
        profile = await self._session.get(UserProfile, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            self._session.add(profile)
        profile.skin_type = skin_type
        profile.is_pregnant_or_nursing = is_pregnant_or_nursing
        profile.health_conditions = health_conditions
        await self._session.flush()
        return profile

    # ------------------------------------------------------------------ allergies
    async def list_allergy_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.scalars(
            select(UserAllergy.ingredient_id)
            .where(UserAllergy.user_id == user_id)
            .order_by(UserAllergy.ingredient_id)
        )
        return list(result)

    async def replace_allergies(
        self, user_id: uuid.UUID, ingredient_ids: Collection[uuid.UUID]
    ) -> None:
        """Make the user's allergy set equal to `ingredient_ids`: delete the removed rows,
        insert the new ones, leave the others untouched."""
        current = set(await self.list_allergy_ids(user_id))
        wanted = set(ingredient_ids)
        removed = current - wanted
        added = wanted - current
        if removed:
            await self._session.execute(
                delete(UserAllergy).where(
                    UserAllergy.user_id == user_id, UserAllergy.ingredient_id.in_(removed)
                )
            )
        if added:
            await self._session.execute(
                insert(UserAllergy)
                .values([{"user_id": user_id, "ingredient_id": i} for i in sorted(added)])
                .on_conflict_do_nothing()
            )

    # ------------------------------------------------------------------ blacklist: products
    async def list_blacklisted_product_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.scalars(
            select(UserBlacklistProduct.product_id)
            .where(UserBlacklistProduct.user_id == user_id)
            .order_by(UserBlacklistProduct.product_id)
        )
        return list(result)

    async def add_blacklisted_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        """Idempotent: adding the same product twice is not an error."""
        await self._session.execute(
            insert(UserBlacklistProduct)
            .values(user_id=user_id, product_id=product_id)
            .on_conflict_do_nothing()
        )

    async def remove_blacklisted_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        """Idempotent: removing a product that is not blacklisted is not an error."""
        await self._session.execute(
            delete(UserBlacklistProduct).where(
                UserBlacklistProduct.user_id == user_id,
                UserBlacklistProduct.product_id == product_id,
            )
        )

    # ------------------------------------------------------------------ blacklist: ingredients
    async def list_blacklisted_ingredient_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.scalars(
            select(UserBlacklistIngredient.ingredient_id)
            .where(UserBlacklistIngredient.user_id == user_id)
            .order_by(UserBlacklistIngredient.ingredient_id)
        )
        return list(result)

    async def add_blacklisted_ingredient(
        self, user_id: uuid.UUID, ingredient_id: uuid.UUID
    ) -> None:
        """Idempotent: adding the same ingredient twice is not an error."""
        await self._session.execute(
            insert(UserBlacklistIngredient)
            .values(user_id=user_id, ingredient_id=ingredient_id)
            .on_conflict_do_nothing()
        )

    async def remove_blacklisted_ingredient(
        self, user_id: uuid.UUID, ingredient_id: uuid.UUID
    ) -> None:
        """Idempotent: removing an ingredient that is not blacklisted is not an error."""
        await self._session.execute(
            delete(UserBlacklistIngredient).where(
                UserBlacklistIngredient.user_id == user_id,
                UserBlacklistIngredient.ingredient_id == ingredient_id,
            )
        )

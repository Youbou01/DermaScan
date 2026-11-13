"""Business logic of the identity module: accounts, tokens, health profile and blacklist.

The service commits; the repository only flushes. Other modules are used through their
public interface only.
"""

import asyncio
import uuid
from collections.abc import Collection

import structlog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.i18n import DEFAULT_LOCALE
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.catalog import CatalogService
from app.modules.identity.exceptions import (
    EmailAlreadyRegisteredError,
    IngredientNotFoundError,
    InvalidCredentialsError,
)
from app.modules.identity.models import UserAccount
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import (
    AccessTokenOut,
    AuthTokensOut,
    BlacklistOut,
    HealthCondition,
    LoginRequest,
    ProfileOut,
    ProfileUpdateIn,
    RegisterRequest,
    SuitabilityOut,
    UserOut,
)
from app.modules.identity.suitability import (
    IngredientFacts,
    ProfileFacts,
    evaluate_suitability,
)
from app.modules.ingredients import IngredientService

logger = structlog.get_logger(__name__)


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = IdentityRepository(session)
        self._catalog = CatalogService(session)
        self._ingredients = IngredientService(session)

    # ----------------------------------------------------------------------- auth

    async def register(self, payload: RegisterRequest) -> AuthTokensOut:
        if await self._repository.get_user_by_email(payload.email) is not None:
            raise EmailAlreadyRegisteredError("An account with this email already exists.")
        password_hash = await asyncio.to_thread(hash_password, payload.password)
        try:
            user = await self._repository.add_user(
                payload.email, password_hash, payload.display_name
            )
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            logger.warning("identity_register_duplicate_email", exc_info=True)
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists."
            ) from None
        return self._tokens(user)

    async def login(self, payload: LoginRequest) -> AuthTokensOut:
        user = await self._repository.get_user_by_email(payload.email)
        if user is None:
            # Same work as a real check, so the response time does not reveal the email.
            await asyncio.to_thread(hash_password, payload.password)
            raise InvalidCredentialsError("Invalid email or password.")
        is_valid = await asyncio.to_thread(verify_password, payload.password, user.password_hash)
        if not is_valid:
            raise InvalidCredentialsError("Invalid email or password.")
        return self._tokens(user)

    async def refresh(self, refresh_token: str) -> AccessTokenOut:
        user_id = decode_token(refresh_token, "refresh")
        if await self._repository.get_user_by_id(user_id) is None:
            raise UnauthorizedError("Account no longer exists.")
        return AccessTokenOut(access_token=create_access_token(user_id))

    # -------------------------------------------------------------------- profile

    async def get_profile(self, user_id: uuid.UUID) -> ProfileOut:
        return await self._build_profile(user_id)

    async def put_profile(self, user_id: uuid.UUID, payload: ProfileUpdateIn) -> ProfileOut:
        await self._require_user(user_id)
        await self._ensure_ingredients_exist(payload.allergy_ingredient_ids)
        await self._repository.save_profile(
            user_id,
            payload.skin_type,
            payload.is_pregnant_or_nursing,
            [condition.value for condition in payload.health_conditions],
        )
        await self._repository.replace_allergies(user_id, payload.allergy_ingredient_ids)
        await self._commit()
        return await self._build_profile(user_id)

    # ------------------------------------------------------------------ blacklist

    async def get_blacklist(self, user_id: uuid.UUID) -> BlacklistOut:
        return BlacklistOut(
            product_ids=await self._repository.list_blacklisted_product_ids(user_id),
            ingredient_ids=await self._repository.list_blacklisted_ingredient_ids(user_id),
        )

    async def add_blacklisted_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._require_user(user_id)
        await self._catalog.get_product_detail(product_id, DEFAULT_LOCALE)
        await self._repository.add_blacklisted_product(user_id, product_id)
        await self._commit()

    async def remove_blacklisted_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._repository.remove_blacklisted_product(user_id, product_id)
        await self._commit()

    async def add_blacklisted_ingredient(
        self, user_id: uuid.UUID, ingredient_id: uuid.UUID
    ) -> None:
        await self._require_user(user_id)
        await self._ensure_ingredients_exist([ingredient_id])
        await self._repository.add_blacklisted_ingredient(user_id, ingredient_id)
        await self._commit()

    async def remove_blacklisted_ingredient(
        self, user_id: uuid.UUID, ingredient_id: uuid.UUID
    ) -> None:
        await self._repository.remove_blacklisted_ingredient(user_id, ingredient_id)
        await self._commit()

    # ---------------------------------------------------------------- suitability

    async def get_suitability(
        self, user_id: uuid.UUID, product_id: uuid.UUID, locale: str
    ) -> SuitabilityOut:
        detail = await self._catalog.get_product_detail(product_id, locale)
        profile = await self._repository.get_profile(user_id)
        blacklisted_products = await self._repository.list_blacklisted_product_ids(user_id)
        ingredient_ids = list(
            dict.fromkeys(
                item.ingredient_id for item in detail.ingredients if item.ingredient_id is not None
            )
        )
        infos = await self._ingredients.get_many(ingredient_ids, locale) if ingredient_ids else {}
        facts = ProfileFacts(
            skin_type=profile.skin_type if profile else None,
            is_pregnant_or_nursing=profile.is_pregnant_or_nursing if profile else False,
            health_conditions=frozenset(
                HealthCondition(value) for value in (profile.health_conditions if profile else [])
            ),
            allergy_ingredient_ids=frozenset(await self._repository.list_allergy_ids(user_id)),
            blacklisted_ingredient_ids=frozenset(
                await self._repository.list_blacklisted_ingredient_ids(user_id)
            ),
            product_is_blacklisted=product_id in blacklisted_products,
        )
        items = [
            IngredientFacts(
                ingredient_id=info.id,
                name=info.inci_name,
                is_prohibited=info.is_prohibited,
                is_allergen=info.is_allergen,
            )
            for ingredient_id in ingredient_ids
            if (info := infos.get(ingredient_id)) is not None
        ]
        return evaluate_suitability(product_id, facts, items, locale)

    # -------------------------------------------------------------------- helpers

    @staticmethod
    def _tokens(user: UserAccount) -> AuthTokensOut:
        return AuthTokensOut(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            user=UserOut(id=user.id, email=user.email, display_name=user.display_name),
        )

    async def _build_profile(self, user_id: uuid.UUID) -> ProfileOut:
        profile = await self._repository.get_profile(user_id)
        return ProfileOut(
            user_id=user_id,
            skin_type=profile.skin_type if profile else None,
            is_pregnant_or_nursing=profile.is_pregnant_or_nursing if profile else False,
            health_conditions=(
                [HealthCondition(value) for value in profile.health_conditions] if profile else []
            ),
            allergy_ingredient_ids=await self._repository.list_allergy_ids(user_id),
            blacklisted_product_ids=await self._repository.list_blacklisted_product_ids(user_id),
        )

    async def _require_user(self, user_id: uuid.UUID) -> None:
        if await self._repository.get_user_by_id(user_id) is None:
            raise UnauthorizedError("Account no longer exists.")

    async def _ensure_ingredients_exist(self, ingredient_ids: Collection[uuid.UUID]) -> None:
        if not ingredient_ids:
            return
        found = await self._ingredients.get_many(ingredient_ids, DEFAULT_LOCALE)
        missing = [str(i) for i in ingredient_ids if i not in found]
        if missing:
            raise IngredientNotFoundError(f"Unknown ingredient id(s): {', '.join(missing)}.")

    async def _commit(self) -> None:
        try:
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            logger.warning("identity_commit_failed", exc_info=True)
            raise

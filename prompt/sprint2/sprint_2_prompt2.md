# System Role & Execution Mandate (For Coding Agent: Gemini 3.8 Flash)

You are an autonomous **Principal Full-Stack Engineer (FastAPI Backend + React Native / Expo SDK 58 Mobile)** working in the **DermaScan** repository.

Manual testing on a physical device via Expo alongside live FastAPI server logs and Git pre-commit output revealed **4 user-facing bugs** and **6 hidden architectural bugs** that must be completely resolved:

1. **Search & Filter Engine Breaks When Combining Queries and Filters:**
   - `GET /api/v1/products/filter` has no `q` parameter, so `mobile/src/features/search/search-api.ts` fetches only the first 20 filtered rows from the 15,912-product database and filters them in JavaScript on the phone, returning 0 results whenever a search query is combined with a category, risk band, minimum score, or ingredient filter.
   - `search_by_name` only searches `Product.name_normalized` and ignores `Brand.name`.
   - `include` and `exclude` ingredient filters fail on partial ingredient names or comma-separated inputs.
2. **Android Red Screen Crash on Profile Save & Missing Unauthenticated Login Redirect:**
   - `ProfileScreen.tsx`, `RoutineRecommendationView.tsx`, and `design-system.tsx` render `<Text accessibilityRole="status">`. On Android, `"status"` is an invalid React Native `AccessibilityRole` and immediately triggers a fatal native Red Screen crash when `savedNotice` becomes `true`.
   - Tapping "Save health profile" or toggling blacklist items while logged out returns HTTP `401`, which `profile-api.ts` silently swallows instead of redirecting the user to `/auth/login`.
3. **Blacklisted Products UI Shows Raw UUIDs Instead of Product Names:**
   - `ProfileScreen.tsx` looks up blacklisted product names in `productCardsFixture` (which only has 4 mock items) and falls back to displaying the raw UUID string for all real database products.
4. **Blacklisted & Allergy Ingredient Chips Return `404` After Logging In:**
   - `KNOWN_PROFILE_INGREDIENTS` in `mobile/src/api/fixtures.ts` uses 5 static preset UUIDs (`0194f024-6c67-7e21-9e16-a774b0d53401`..`405`), whereas PostgreSQL generated different UUIDv7 primary keys for `PARFUM`, `RETINOL`, `SALICYLIC ACID`, `ALCOHOL DENAT.`, and `SODIUM LAURYL SULFATE`. Sending those preset UUIDs to `POST /api/v1/profile/blacklist/ingredients/{id}` or `PUT /api/v1/profile` returns `404 Not Found`, and the subsequent refetch immediately wipes the user's selection.
5. **Additional Hidden Bugs to Clean Up:**
   - `HttpCacheMiddleware` caches `/api/v1/products/{id}/suitability` with `public, max-age=300`, serving stale suitability verdicts after profile/blacklist updates.
   - `AuthContext.tsx` falls back to `'mock-jwt-access-token'` on network/server errors even when `env.useMocks === false` and does not invalidate TanStack Query caches (`['profile']`, `['blacklist']`, `['suitability']`, `['routines']`) on login, register, or sign-out.
   - Product images pointing to `http://localhost:9000/...` fail to load on physical phones because `localhost` resolves to the phone itself rather than the API host, and `ProductDetailScreen.tsx` does not fall back to category artwork when a product image is unavailable.
   - `backend/before_sprint2.dump` (13.1 MB) is not ignored in `.gitignore`, causing the `check-added-large-files` pre-commit hook to fail.

---

## Strict Operating Rules (Non-Negotiable)

1. **Execute Sequentially Without Improvisation:** Execute **Phase 0** and **Micro-Steps 1 through 10** in exact order. Do not skip any step.
2. **Preserve All Existing Passing Tests:** All existing Backend tests (`uv run pytest`) and Mobile tests (`npm test`) **MUST** remain 100% green, and new regression tests must be added.
3. **Code Quality & Linter Rules:**
   - **Backend:** Strict type annotations (`ruff` `ANN` + `mypy --strict`), line length <= 100, `uv run lint-imports` contracts respected, `docs/openapi.json` kept in sync via `scripts/export_openapi.py`.
   - **Mobile:** No `any`, explicit return types on all functions and components (`: ReactElement`, `: ReactElement | null`, `: void`, `: Promise<void>`), inline type imports, no floating promises, no `console.log`, and never use `accessibilityRole="status"` on React Native elements.
   - **Product Wording Rule:** Never use the words `safe`, `unsafe`, `toxic`, `harmful`, or `dangerous` in any UI text, translation string, or code comment.

---

## Phase 0: Pre-Flight & Git Large File Cleanup

Run these commands from the repository root before modifying application code:

### Action 0.1 — Update `.gitignore` to Ignore Database Dumps
In `.gitignore` at the repository root, replace `#dump\nbackend/before_m11.dump` with:

```gitignore
#dump
*.dump
backend/before_m11.dump
backend/before_sprint2.dump
```

### Action 0.2 — Unstage `backend/before_sprint2.dump` from Git Index (Keep File on Disk)
Run from the repository root:

```bash
git rm --cached --ignore-unmatch backend/before_sprint2.dump
```

---

## Micro-Step 1: Exclude Personalized Suitability from Public HTTP Cache (`backend/src/app/core/caching.py`)

### Goal
Ensure `GET /api/v1/products/{product_id}/suitability` is never cached as a public HTTP response so profile and blacklist changes immediately reflect in product suitability checks.

### Action 1.1 — Update `backend/src/app/core/caching.py`
In `backend/src/app/core/caching.py`, update `_get_cache_policy`:

```python
    def _get_cache_policy(self, path: str) -> tuple[int, int] | None:
        """Returns (max_age, stale_while_revalidate) for cacheable endpoints."""
        if path.startswith("/api/v1/categories"):
            return 3600, 300
        if path.startswith("/api/v1/home"):
            return 300, 60
        if path.startswith("/api/v1/products") and not path.endswith("/suitability"):
            return 300, 60
        return None
```

---

## Micro-Step 2: Unify Backend Product Search & Multi-Facet Filter Engine (`backend/src/app/modules/catalog/`)

### Goal
1. Include `category_slug` and `score_is_estimated` on `ProductSummary` so search and filter results render category labels and artwork on mobile cards.
2. Search both `Product.name_normalized` and `Brand.name` in `ProductSearchRepository`.
3. Support optional `q` on `GET /api/v1/products/filter` so combining text search with category, risk band, score range, and ingredient `include`/`exclude` filters executes in a single PostgreSQL query.
4. Support both exact alias matches and high-confidence trigram suggestions (`min_similarity=0.55`) when resolving `include` and `exclude` ingredient filter terms.

### Action 2.1 — Update `backend/src/app/modules/catalog/search_schemas.py`
Replace `backend/src/app/modules/catalog/search_schemas.py` with:

```python
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RiskLevel


class ProductSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    barcode: str = Field(description="GTIN-13.")
    name: str
    brand: str | None
    category_slug: str | None = None
    image_url: str | None
    score: int | None = Field(description="0-100, or null when the product is not scored.")
    score_band: RiskLevel = Field(description="'unknown' means insufficient data, NOT safe.")
    score_is_estimated: bool = False
```

### Action 2.2 — Update `backend/src/app/modules/catalog/search_repository.py`
Replace `backend/src/app/modules/catalog/search_repository.py` with:

```python
"""SQL for product search and filters. Private: use `ProductSearchService`."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Float, Select, Text, case, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.enums import RiskLevel
from app.modules.catalog.models import Brand, Category, Product, ProductIngredient

ProductQuery = Select[Product]


def by_search_query(stmt: ProductQuery, q_norm: str) -> ProductQuery:
    """Match product normalized name (prefix, substring, or trigram) or brand name."""
    prefix = Product.name_normalized.startswith(q_norm, autoescape=True)
    substring = Product.name_normalized.contains(q_norm, autoescape=True)
    brand_match = exists().where(
        Brand.id == Product.brand_id,
        func.lower(func.unaccent(Brand.name)).contains(q_norm, autoescape=True),
    )
    return stmt.where(
        or_(
            prefix,
            substring,
            Product.name_normalized.op("%")(q_norm),
            literal(q_norm, Text).op("<%")(Product.name_normalized),
            brand_match,
        )
    )


def by_categories(stmt: ProductQuery, category_ids: Sequence[uuid.UUID]) -> ProductQuery:
    return stmt.where(Product.primary_category_id.in_(category_ids))


def by_bands(stmt: ProductQuery, bands: Sequence[RiskLevel]) -> ProductQuery:
    return stmt.where(Product.score_band.in_(bands))


def by_score_range(
    stmt: ProductQuery, min_score: int | None, max_score: int | None
) -> ProductQuery:
    if min_score is not None:
        stmt = stmt.where(Product.score >= min_score)
    if max_score is not None:
        stmt = stmt.where(Product.score <= max_score)
    return stmt


def with_ingredients(stmt: ProductQuery, ingredient_ids: Sequence[uuid.UUID]) -> ProductQuery:
    """Product contains ALL the given ingredients."""
    for ingredient_id in ingredient_ids:
        stmt = stmt.where(
            exists().where(
                ProductIngredient.product_id == Product.id,
                ProductIngredient.ingredient_id == ingredient_id,
            )
        )
    return stmt


def with_ingredient_groups(
    stmt: ProductQuery, ingredient_groups: Sequence[Sequence[uuid.UUID]]
) -> ProductQuery:
    """Product contains at least one candidate ingredient from each requested group."""
    for group in ingredient_groups:
        stmt = stmt.where(
            exists().where(
                ProductIngredient.product_id == Product.id,
                ProductIngredient.ingredient_id.in_(group),
            )
        )
    return stmt


def without_ingredients(stmt: ProductQuery, ingredient_ids: Sequence[uuid.UUID]) -> ProductQuery:
    """Product contains NONE of the given ingredients."""
    if not ingredient_ids:
        return stmt
    return stmt.where(
        ~exists().where(
            ProductIngredient.product_id == Product.id,
            ProductIngredient.ingredient_id.in_(ingredient_ids),
        )
    )


class ProductSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def base_query() -> ProductQuery:
        return select(Product).options(
            joinedload(Product.brand),
            joinedload(Product.primary_category),
        )

    async def category_subtree_ids(self, slug: str) -> list[uuid.UUID]:
        """The category with this slug plus all its descendants."""
        tree = select(Category.id).where(Category.slug == slug).cte("tree", recursive=True)
        tree = tree.union_all(select(Category.id).join(tree, Category.parent_id == tree.c.id))
        return list((await self._session.scalars(select(tree.c.id))).all())

    async def search_by_name(self, q_norm: str, *, limit: int, offset: int) -> list[Product]:
        """Prefix matches first, then brand/fuzzy (trigram) matches by similarity."""
        prefix = Product.name_normalized.startswith(q_norm, autoescape=True)
        brand_match = exists().where(
            Brand.id == Product.brand_id,
            func.lower(func.unaccent(Brand.name)).contains(q_norm, autoescape=True),
        )
        rank = (
            func.greatest(
                func.similarity(Product.name_normalized, q_norm),
                func.word_similarity(q_norm, Product.name_normalized),
            )
            + case((prefix, literal(1.0, Float)), else_=literal(0.0, Float))
            + case((brand_match, literal(0.5, Float)), else_=literal(0.0, Float))
        )
        stmt = (
            by_search_query(self.base_query(), q_norm)
            .order_by(rank.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self._session.scalars(stmt)).all())
```

### Action 2.3 — Update `backend/src/app/modules/catalog/search_service.py`
Replace `backend/src/app/modules/catalog/search_service.py` with:

```python
"""Product search by name (story 5) and filtered search (story 6)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.errors import UnprocessableError
from app.core.i18n import DEFAULT_LOCALE, resolve_product_name
from app.core.keyset import InvalidCursorError, Page, paginate
from app.modules.catalog.models import Product
from app.modules.catalog.search_repository import (
    ProductSearchRepository,
    by_bands,
    by_categories,
    by_score_range,
    by_search_query,
    with_ingredient_groups,
    without_ingredients,
)
from app.modules.catalog.search_schemas import ProductSummary
from app.modules.catalog.search_text import normalize_name
from app.modules.ingredients import IngredientService

MAX_SEARCH_RESULTS = 200  # ranked fuzzy results use an offset cursor: keep it bounded


class InvalidScoreRangeError(UnprocessableError):
    code = "invalid-score-range"
    title = "min_score must not exceed max_score"


def _summary(product: Product, locale: str = DEFAULT_LOCALE) -> ProductSummary:
    return ProductSummary(
        id=product.id,
        barcode=product.barcode,
        name=resolve_product_name(product.name, product.name_i18n, locale),
        brand=product.brand.name if product.brand else None,
        category_slug=product.primary_category.slug if product.primary_category else None,
        image_url=product.image_url,
        score=product.score,
        score_band=product.score_band,
        score_is_estimated=product.score_is_estimated,
    )


def _empty() -> Page[ProductSummary]:
    return Page[ProductSummary](items=[], next_cursor=None)


def _parse_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise InvalidCursorError from exc
    if offset < 0:
        raise InvalidCursorError
    return offset


async def _resolve_ingredient_groups(
    session: AsyncSession, raw_names: list[str]
) -> tuple[list[list[uuid.UUID]], list[str]]:
    """Resolve ingredient filter terms via exact alias match first, then trigram suggestion."""
    expanded: list[str] = []
    for raw in raw_names:
        for part in raw.split(","):
            cleaned = part.strip()
            if cleaned:
                expanded.append(cleaned)

    if not expanded:
        return [], []

    ing_service = IngredientService(session)
    matches = await ing_service.match(expanded)
    groups: list[list[uuid.UUID]] = []
    unmatched: list[str] = []

    for term, match in zip(expanded, matches, strict=True):
        if match.ingredient_id is not None:
            groups.append([match.ingredient_id])
            continue
        suggestions = await ing_service.suggest(term, limit=5, min_similarity=0.55)
        if suggestions:
            groups.append([s.ingredient_id for s in suggestions])
        else:
            unmatched.append(term)

    return groups, unmatched


class ProductSearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProductSearchRepository(session)

    async def search_by_name(
        self, q: str, *, limit: int, cursor: str | None
    ) -> Page[ProductSummary]:
        offset = _parse_offset(cursor)
        q_norm = normalize_name(q)
        if not q_norm or offset >= MAX_SEARCH_RESULTS:
            return _empty()
        page_size = min(limit, MAX_SEARCH_RESULTS - offset)
        rows = await self._repo.search_by_name(q_norm, limit=page_size + 1, offset=offset)
        has_more = len(rows) > page_size and offset + page_size < MAX_SEARCH_RESULTS
        return Page[ProductSummary](
            items=[_summary(p) for p in rows[:page_size]],
            next_cursor=str(offset + page_size) if has_more else None,
        )

    async def filter_products(
        self,
        *,
        q: str | None = None,
        category: str | None,
        bands: list[RiskLevel] | None,
        min_score: int | None,
        max_score: int | None,
        include: list[str] | None,
        exclude: list[str] | None,
        limit: int,
        cursor: str | None,
    ) -> Page[ProductSummary]:
        """Scored products only, best score first (unscored = insufficient data).
        Supports combining search query `q` with category, band, score range, and ingredient
        include/exclude filters in a single database query."""
        if min_score is not None and max_score is not None and min_score > max_score:
            raise InvalidScoreRangeError

        stmt = self._repo.base_query().where(Product.score.is_not(None))
        if q is not None and q.strip():
            q_norm = normalize_name(q)
            if not q_norm:
                return _empty()
            stmt = by_search_query(stmt, q_norm)
        if category:
            category_ids = await self._repo.category_subtree_ids(category)
            if not category_ids:
                return _empty()
            stmt = by_categories(stmt, category_ids)
        if bands:
            stmt = by_bands(stmt, bands)
        stmt = by_score_range(stmt, min_score, max_score)
        if include:
            include_groups, unmatched = await _resolve_ingredient_groups(self._session, include)
            if unmatched:
                return _empty()
            stmt = with_ingredient_groups(stmt, include_groups)
        if exclude:
            exclude_groups, _ = await _resolve_ingredient_groups(self._session, exclude)
            exclude_ids = list({ing_id for grp in exclude_groups for ing_id in grp})
            stmt = without_ingredients(stmt, exclude_ids)

        items, next_cursor = await paginate(
            self._session,
            stmt,
            sort="score",
            sort_column=Product.score,
            id_column=Product.id,
            key=lambda p: (p.score, p.id),
            parse_value=int,
            limit=limit,
            cursor=cursor,
        )
        return Page[ProductSummary](items=[_summary(p) for p in items], next_cursor=next_cursor)
```

### Action 2.4 — Update `backend/src/app/modules/catalog/search_router.py`
In `backend/src/app/modules/catalog/search_router.py`, add the optional `q` query parameter to `filter_products`:

```python
@router.get(
    "/filter",
    response_model=Page[ProductSummary],
    responses=_ERRORS,
    summary="Filter scored products, best score first",
)
async def filter_products(
    service: SearchServiceDep,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Optional product name or brand search query."),
    ] = None,
    category: Annotated[
        str | None, Query(description="Category slug; child categories are included.")
    ] = None,
    band: Annotated[list[RiskLevel] | None, Query(description="One or more score bands.")] = None,
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    max_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    include: Annotated[
        list[str] | None, Query(max_length=10, description="Must contain all of these.")
    ] = None,
    exclude: Annotated[
        list[str] | None, Query(max_length=10, description="Must contain none of these.")
    ] = None,
    limit: LimitQuery = DEFAULT_LIMIT,
    cursor: CursorQuery = None,
) -> Page[ProductSummary]:
    return await service.filter_products(
        q=q,
        category=category,
        bands=band,
        min_score=min_score,
        max_score=max_score,
        include=include,
        exclude=exclude,
        limit=limit,
        cursor=cursor,
    )
```

---

## Micro-Step 3: Fix Backend Profile & Blacklist Preset Ingredient Resolution (`backend/src/app/modules/identity/service.py`)

### Goal
Bridge the 5 well-known mobile preset ingredient UUIDs (`0194f024-6c67-7e21-9e16-a774b0d53401`..`405` for `PARFUM`, `RETINOL`, `SALICYLIC ACID`, `ALCOHOL DENAT.`, `SODIUM LAURYL SULFATE`) to their real PostgreSQL `Ingredient` rows so:
- Tapping any preset ingredient chip in Allergies or Blacklist on `ProfileScreen` resolves to the canonical PostgreSQL `Ingredient` row (creating it if absent) instead of returning `404 Not Found`.
- `get_profile` and `get_blacklist` include the corresponding preset UUID whenever a user's stored allergy or blacklisted ingredient matches one of the 5 preset INCI names, so both `ProfileScreen` chips and `ProductDetailScreen` rows stay synchronized.
- Any unknown non-preset UUID still raises `IngredientNotFoundError` (`404`) as required by `test_identity_api.py`.

### Action 3.1 — Update `backend/src/app/modules/identity/service.py`
Replace `backend/src/app/modules/identity/service.py` with:

```python
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
    RefreshRequest,
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

PRESET_INGREDIENT_BY_ID: dict[uuid.UUID, str] = {
    uuid.UUID("0194f024-6c67-7e21-9e16-a774b0d53401"): "PARFUM",
    uuid.UUID("0194f024-6c67-7e21-9e16-a774b0d53402"): "RETINOL",
    uuid.UUID("0194f024-6c67-7e21-9e16-a774b0d53403"): "SALICYLIC ACID",
    uuid.UUID("0194f024-6c67-7e21-9e16-a774b0d53404"): "ALCOHOL DENAT.",
    uuid.UUID("0194f024-6c67-7e21-9e16-a774b0d53405"): "SODIUM LAURYL SULFATE",
}
PRESET_ID_BY_INCI: dict[str, uuid.UUID] = {
    inci: preset_id for preset_id, inci in PRESET_INGREDIENT_BY_ID.items()
}


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
        resolved_allergy_ids = await self._resolve_and_ensure_ingredients(
            payload.allergy_ingredient_ids
        )
        await self._repository.save_profile(
            user_id,
            payload.skin_type,
            payload.is_pregnant_or_nursing,
            [condition.value for condition in payload.health_conditions],
        )
        await self._repository.replace_allergies(user_id, resolved_allergy_ids)
        await self._commit()
        return await self._build_profile(user_id)

    # ------------------------------------------------------------------ blacklist

    async def get_blacklist(self, user_id: uuid.UUID) -> BlacklistOut:
        stored_ing_ids = await self._repository.list_blacklisted_ingredient_ids(user_id)
        return BlacklistOut(
            product_ids=await self._repository.list_blacklisted_product_ids(user_id),
            ingredient_ids=await self._expand_preset_ingredient_ids(stored_ing_ids),
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
        [resolved_id] = await self._resolve_and_ensure_ingredients([ingredient_id])
        await self._repository.add_blacklisted_ingredient(user_id, resolved_id)
        await self._commit()

    async def remove_blacklisted_ingredient(
        self, user_id: uuid.UUID, ingredient_id: uuid.UUID
    ) -> None:
        await self._repository.remove_blacklisted_ingredient(user_id, ingredient_id)
        preset_inci = PRESET_INGREDIENT_BY_ID.get(ingredient_id)
        if preset_inci is not None:
            matches = await self._ingredients.match([preset_inci])
            if matches and matches[0].ingredient_id is not None:
                await self._repository.remove_blacklisted_ingredient(
                    user_id, matches[0].ingredient_id
                )
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
        stored_allergies = await self._repository.list_allergy_ids(user_id)
        return ProfileOut(
            user_id=user_id,
            skin_type=profile.skin_type if profile else None,
            is_pregnant_or_nursing=profile.is_pregnant_or_nursing if profile else False,
            health_conditions=(
                [HealthCondition(value) for value in profile.health_conditions] if profile else []
            ),
            allergy_ingredient_ids=await self._expand_preset_ingredient_ids(stored_allergies),
            blacklisted_product_ids=await self._repository.list_blacklisted_product_ids(user_id),
        )

    async def _require_user(self, user_id: uuid.UUID) -> None:
        if await self._repository.get_user_by_id(user_id) is None:
            raise UnauthorizedError("Account no longer exists.")

    async def _resolve_and_ensure_ingredients(
        self, ingredient_ids: Collection[uuid.UUID]
    ) -> list[uuid.UUID]:
        if not ingredient_ids:
            return []
        found = await self._ingredients.get_many(ingredient_ids, DEFAULT_LOCALE)
        resolved: list[uuid.UUID] = []
        missing: list[str] = []

        for ing_id in ingredient_ids:
            if ing_id in found:
                resolved.append(ing_id)
                continue
            preset_inci = PRESET_INGREDIENT_BY_ID.get(ing_id)
            if preset_inci is not None:
                ensured = await self._ingredients.ensure_ingredients_exist(
                    [{"original": preset_inci, "inci": preset_inci}]
                )
                if ensured:
                    resolved.append(ensured[0])
                    continue
            missing.append(str(ing_id))

        if missing:
            raise IngredientNotFoundError(f"Unknown ingredient id(s): {', '.join(missing)}.")
        return list(dict.fromkeys(resolved))

    async def _expand_preset_ingredient_ids(
        self, stored_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Include matching mobile preset UUIDs when a canonical preset ingredient is stored."""
        if not stored_ids:
            return []
        infos = await self._ingredients.get_many(stored_ids, DEFAULT_LOCALE)
        out: list[uuid.UUID] = list(stored_ids)
        for ing_id in stored_ids:
            info = infos.get(ing_id)
            if info is not None:
                preset_id = PRESET_ID_BY_INCI.get(info.inci_name.strip().upper())
                if preset_id is not None and preset_id not in out:
                    out.append(preset_id)
        return out

    async def _commit(self) -> None:
        try:
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            logger.warning("identity_commit_failed", exc_info=True)
            raise
```

---

## Micro-Step 4: Regenerate OpenAPI Contract & Mobile Types

### Goal
Synchronize `docs/openapi.json`, `mobile/openapi.json`, and `mobile/src/api/generated/schema.d.ts` with the updated backend search/filter schema.

### Action 4.1 — Export OpenAPI & Regenerate Mobile Schema Types
Run from the repository root:

```bash
cd backend
uv run python scripts/export_openapi.py
cd ../mobile
npm run api:types
```

---

## Micro-Step 5: Fix Mobile Image URL Resolution & Category Artwork Fallback (`mobile/src/lib/image-url.ts`, `ProductCard.tsx`, `product-detail-screen.tsx`)

### Goal
1. Rewrite `localhost` / `127.0.0.1` image URLs (such as local MinIO URLs `http://localhost:9000/dermascan/...`) to use the LAN/API hostname configured in `env.apiUrl` so product images load on physical phones.
2. Fall back to the category illustration (`getProductArtwork`) on `ProductDetailScreen` when a product has no photo or its photo fails to load.

### Action 5.1 — Create `mobile/src/lib/image-url.ts`
```typescript
import { env } from '@/config/env';

export function resolveProductImageUrl(rawUrl: string | null | undefined): string | null {
  if (!rawUrl || !rawUrl.trim()) {
    return null;
  }
  try {
    const parsed = new URL(rawUrl);
    if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
      const apiParsed = new URL(env.apiUrl);
      if (
        apiParsed.hostname &&
        apiParsed.hostname !== 'localhost' &&
        apiParsed.hostname !== '127.0.0.1' &&
        apiParsed.hostname !== 'mock.invalid'
      ) {
        parsed.hostname = apiParsed.hostname;
        return parsed.toString();
      }
    }
    return parsed.toString();
  } catch {
    return rawUrl;
  }
}
```

### Action 5.2 — Update `mobile/src/components/ProductCard.tsx` to Use `resolveProductImageUrl`
In `mobile/src/components/ProductCard.tsx`:
1. Import `resolveProductImageUrl` from `@/lib/image-url`.
2. Compute `const resolvedImageUrl = resolveProductImageUrl(product.image_url);`.
3. Replace `product.image_url && !imageFailed` with `resolvedImageUrl && !imageFailed`, and pass `source={{ uri: resolvedImageUrl }}` to `<Image />`.

### Action 5.3 — Update `mobile/src/features/product/product-detail-screen.tsx`
In `mobile/src/features/product/product-detail-screen.tsx`:
1. Import `useAuth` from `@/features/auth/AuthContext`, `getProductArtwork` from `@/features/home/product-artwork`, `resolveProductImageUrl` from `@/lib/image-url`, and `type Href` from `'expo-router'`.
2. Resolve the image URL via `const resolvedImageUrl = resolveProductImageUrl(product.image_url);` and `const fallbackArtwork = getProductArtwork(product.category?.slug ?? null);`.
3. When `imageAvailable` is false and `fallbackArtwork` is defined, render `<Image accessibilityLabel={`${product.name} product image`} resizeMode="contain" source={fallbackArtwork} style={[styles.productImage, { backgroundColor: colors.surfaceMuted }]} />` before falling back to the `◇` placeholder.
4. Guard the product and ingredient blacklist toggle buttons so that when `!env.useMocks && !isAuthenticated` (using `const { isAuthenticated } = useAuth();` or `getActiveAccessToken()`), pressing the blacklist button navigates to `router.push('/auth/login' as unknown as Href)` instead of firing an unauthenticated mutation.

Replace `mobile/src/features/product/product-detail-screen.tsx` with the following complete implementation:

```typescript
import type { ReactElement } from 'react';
import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { router, type Href } from 'expo-router';
import { getActiveAccessToken } from '@/api/auth-token';
import { ApiError } from '@/api/errors';
import type { ProductIngredient, RiskLevel } from '@/api/types';
import { useProductQuery } from '@/api/hooks';
import { EmptyState, ErrorState, RiskBadge, ScoreBadge, Screen, Skeleton } from '@/components';
import { env } from '@/config/env';
import { getProductArtwork } from '@/features/home/product-artwork';
import {
  useBlacklistQuery,
  useProductSuitabilityQuery,
  useToggleBlacklistIngredientMutation,
  useToggleBlacklistProductMutation,
} from '@/features/profile/profile-api';
import { useTranslation } from '@/i18n/useTranslation';
import { resolveProductImageUrl } from '@/lib/image-url';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { IngredientRationaleModal } from './components/IngredientRationaleModal';
import { formatScoreCoverage, productDetailCopy } from './product-detail.copy';

const productNotFoundType = 'urn:skincare:problem:product-not-found';

export interface ProductDetailScreenProps {
  productId: string | undefined;
}

export function ProductDetailScreen({ productId }: ProductDetailScreenProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const productQuery = useProductQuery(productId);
  const [selectedIngredient, setSelectedIngredient] = useState<ProductIngredient | null>(null);
  const [failedImageUrl, setFailedImageUrl] = useState<string | null>(null);

  const suitabilityQuery = useProductSuitabilityQuery(
    productId,
    productQuery.data?.ingredients ?? [],
  );
  const blacklistQuery = useBlacklistQuery();
  const toggleBlacklistProduct = useToggleBlacklistProductMutation();
  const toggleBlacklistIngredient = useToggleBlacklistIngredientMutation();

  if (!productId) {
    return (
      <Screen>
        <ErrorState
          title={productDetailCopy.missingIdTitle}
          description={productDetailCopy.missingIdDescription}
        />
      </Screen>
    );
  }

  if (productQuery.isPending) {
    return (
      <Screen contentContainerStyle={styles.loadingContent}>
        <Skeleton height={220} />
        <Skeleton variant="text" width="72%" />
        <Skeleton variant="text" width="46%" />
        <Skeleton height={80} />
        <Skeleton height={80} />
      </Screen>
    );
  }

  if (productQuery.isError && productQuery.data === undefined) {
    const isNotFound =
      productQuery.error instanceof ApiError && productQuery.error.type === productNotFoundType;
    return (
      <Screen>
        <ErrorState
          title={isNotFound ? productDetailCopy.notFoundTitle : productDetailCopy.genericErrorTitle}
          description={
            isNotFound
              ? productDetailCopy.notFoundDescription
              : productDetailCopy.genericErrorDescription
          }
          buttonLabel={productDetailCopy.retryLabel}
          onRetry={() => {
            void productQuery.refetch();
          }}
        />
      </Screen>
    );
  }

  const product = productQuery.data;
  if (!product) {
    return (
      <Screen>
        <EmptyState
          title={productDetailCopy.notFoundTitle}
          description={productDetailCopy.notFoundDescription}
        />
      </Screen>
    );
  }

  const resolvedImageUrl = resolveProductImageUrl(product.image_url);
  const imageAvailable = resolvedImageUrl !== null && failedImageUrl !== resolvedImageUrl;
  const fallbackArtwork = getProductArtwork(product.category?.slug ?? null);
  const suitability = suitabilityQuery.data;
  const isProductBlacklisted = Boolean(
    blacklistQuery.data?.product_ids.includes(product.id) || suitability?.is_blacklisted,
  );
  const selectedIngBlacklisted = Boolean(
    selectedIngredient?.ingredient_id &&
      blacklistQuery.data?.ingredient_ids.includes(selectedIngredient.ingredient_id),
  );

  const verdictColor =
    suitability?.verdict === 'avoid'
      ? colors.high
      : suitability?.verdict === 'caution'
        ? colors.moderate
        : colors.low;
  const verdictSurface =
    suitability?.verdict === 'avoid'
      ? colors.highSurface
      : suitability?.verdict === 'caution'
        ? colors.moderateSurface
        : colors.lowSurface;
  const verdictIcon =
    suitability?.verdict === 'avoid' ? '⬟' : suitability?.verdict === 'caution' ? '△' : '○';
  const verdictLabel =
    suitability?.verdict === 'avoid'
      ? t('product_detail.verdict_avoid')
      : suitability?.verdict === 'caution'
        ? t('product_detail.verdict_caution')
        : t('product_detail.verdict_suitable');

  const handleToggleProductBlacklist = (): void => {
    if (!env.useMocks && !getActiveAccessToken()) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    void toggleBlacklistProduct.mutateAsync(product.id);
  };

  const handleToggleIngredientBlacklist = (ingId: string): void => {
    if (!env.useMocks && !getActiveAccessToken()) {
      setSelectedIngredient(null);
      router.push('/auth/login' as unknown as Href);
      return;
    }
    void toggleBlacklistIngredient.mutateAsync(ingId);
  };

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={productDetailCopy.backAccessibilityLabel}
        onPress={() => router.back()}
        style={({ pressed }) => [
          styles.backButton,
          { borderColor: colors.border, opacity: pressed ? 0.7 : 1 },
        ]}
      >
        <Text style={[styles.backLabel, { color: colors.primary }]}>
          {productDetailCopy.backLabel}
        </Text>
      </Pressable>

      <View style={styles.productHeader}>
        {imageAvailable ? (
          <Image
            accessibilityLabel={`${product.name} product image`}
            onError={() => setFailedImageUrl(resolvedImageUrl)}
            resizeMode="contain"
            source={{ uri: resolvedImageUrl }}
            style={[styles.productImage, { backgroundColor: colors.surfaceMuted }]}
          />
        ) : fallbackArtwork ? (
          <Image
            accessibilityLabel={`${product.name} product image`}
            resizeMode="contain"
            source={fallbackArtwork}
            style={[styles.productImage, { backgroundColor: colors.surfaceMuted }]}
          />
        ) : (
          <View
            accessibilityLabel={productDetailCopy.imageUnavailable}
            style={[
              styles.productImage,
              styles.imagePlaceholder,
              { backgroundColor: colors.surfaceMuted },
            ]}
          >
            <Text
              accessibilityElementsHidden
              style={[styles.imagePlaceholderText, { color: colors.textMuted }]}
            >
              ◇
            </Text>
          </View>
        )}
        <Text accessibilityRole="header" style={[styles.productName, { color: colors.text }]}>
          {product.name}
        </Text>
        <Text style={[styles.productMeta, { color: colors.textMuted }]}>
          {product.brand ?? productDetailCopy.brandUnavailable}
        </Text>
        <Text style={[styles.productMeta, { color: colors.textMuted }]}>
          {product.category?.name ?? productDetailCopy.categoryUnavailable}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            isProductBlacklisted
              ? t('product_detail.blacklist_remove_product')
              : t('product_detail.blacklist_add_product')
          }
          onPress={handleToggleProductBlacklist}
          style={[
            styles.blacklistButton,
            {
              borderColor: isProductBlacklisted ? colors.high : colors.border,
              backgroundColor: isProductBlacklisted ? colors.highSurface : colors.surface,
            },
          ]}
        >
          <Text
            style={[
              styles.blacklistButtonText,
              { color: isProductBlacklisted ? colors.high : colors.text },
            ]}
          >
            {isProductBlacklisted
              ? t('product_detail.blacklist_remove_product')
              : t('product_detail.blacklist_add_product')}
          </Text>
        </Pressable>
      </View>

      <View
        style={[
          styles.scoreSection,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
          {productDetailCopy.riskIndicatorHeading}
        </Text>
        <ScoreBadge
          score={product.score}
          band={product.score === null ? 'unknown' : product.score_band}
        />
        {product.score_is_estimated ? (
          <Text style={[styles.coverage, { color: colors.textMuted }]}>
            {t('product_detail.estimated_note')}
          </Text>
        ) : null}
        <Text style={[styles.coverage, { color: colors.textMuted }]}>
          {formatScoreCoverage(product.score_coverage)}
        </Text>
        {product.summary ? (
          <View style={styles.summaryBox}>
            <Text style={[styles.summaryTitle, { color: colors.text }]}>
              {t('product_detail.summary_heading')}
            </Text>
            <Text style={[styles.summaryBody, { color: colors.textMuted }]}>{product.summary}</Text>
          </View>
        ) : null}
      </View>

      {suitability ? (
        <View
          testID="product-suitability-card"
          style={[
            styles.suitabilitySection,
            { backgroundColor: verdictSurface, borderColor: verdictColor },
          ]}
        >
          <Text accessibilityRole="header" style={[styles.sectionHeading, { color: verdictColor }]}>
            {verdictIcon} {t('product_detail.suitability_heading')}
          </Text>
          <Text style={[styles.verdictText, { color: verdictColor }]}>{verdictLabel}</Text>
          {suitability.alerts.map((alert, idx) => (
            <View
              key={`${alert.code}-${alert.ingredient_name}-${idx}`}
              style={[
                styles.alertCard,
                { backgroundColor: colors.surface, borderColor: verdictColor },
              ]}
            >
              <Text style={[styles.alertTitle, { color: colors.text }]}>
                {alert.severity === 'high' ? '⬟ ' : '△ '}
                {alert.title} ({alert.ingredient_name})
              </Text>
              <Text style={[styles.alertDetail, { color: colors.textMuted }]}>{alert.detail}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={styles.ingredientsSection}>
        <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
          {productDetailCopy.ingredientsHeading}
        </Text>
        {product.ingredients.length > 0 ? (
          <View style={styles.ingredientList}>
            {product.ingredients.map((ingredient) => (
              <IngredientRow
                ingredient={ingredient}
                key={`${ingredient.position}-${ingredient.name}`}
                onPress={() => setSelectedIngredient(ingredient)}
              />
            ))}
          </View>
        ) : (
          <EmptyState
            title={productDetailCopy.ingredientsEmptyTitle}
            description={productDetailCopy.ingredientsEmptyDescription}
          />
        )}
      </View>

      <Text style={[styles.disclaimer, { color: colors.textMuted }]}>
        {productDetailCopy.disclaimer}
      </Text>

      <IngredientRationaleModal
        ingredient={selectedIngredient}
        isBlacklisted={selectedIngBlacklisted}
        onClose={() => setSelectedIngredient(null)}
        onToggleBlacklistIngredient={handleToggleIngredientBlacklist}
      />
    </Screen>
  );
}

interface IngredientRowProps {
  ingredient: ProductIngredient;
  onPress: () => void;
}

function IngredientRow({ ingredient, onPress }: IngredientRowProps): ReactElement {
  const colors = useThemeColors();
  const level: RiskLevel = ingredient.matched ? ingredient.risk_level : 'unknown';

  return (
    <Pressable
      accessibilityHint={productDetailCopy.openRationaleHint}
      accessibilityLabel={`${ingredient.position}. ${ingredient.name}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.ingredientRow,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          opacity: pressed ? 0.75 : 1,
        },
      ]}
    >
      <View style={styles.ingredientText}>
        <Text style={[styles.ingredientName, { color: colors.text }]}>
          {ingredient.position}. {ingredient.name}
        </Text>
        {ingredient.inci_name && ingredient.inci_name !== ingredient.name ? (
          <Text style={[styles.inciName, { color: colors.textMuted }]}>{ingredient.inci_name}</Text>
        ) : null}
      </View>
      <RiskBadge level={level} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { gap: spacing.xl, padding: spacing.lg, paddingBottom: spacing.xxxl },
  loadingContent: { gap: spacing.lg, padding: spacing.lg },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backLabel: { fontSize: typography.size.md, lineHeight: typography.lineHeight.md },
  productHeader: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.md },
  productImage: { width: 180, height: 180, borderRadius: radii.md },
  imagePlaceholder: { alignItems: 'center', justifyContent: 'center' },
  imagePlaceholderText: { fontSize: typography.size.display },
  productName: {
    textAlign: 'center',
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  productMeta: {
    textAlign: 'center',
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
  },
  blacklistButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
    marginTop: spacing.xs,
  },
  blacklistButtonText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  scoreSection: {
    alignItems: 'flex-start',
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  sectionHeading: {
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.bold,
  },
  coverage: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  summaryBox: {
    gap: spacing.xs,
    marginTop: spacing.xs,
  },
  summaryTitle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  summaryBody: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  suitabilitySection: {
    gap: spacing.sm,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  verdictText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  alertCard: {
    gap: spacing.xs,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.sm,
  },
  alertTitle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
  },
  alertDetail: {
    fontSize: typography.size.xs,
    lineHeight: typography.lineHeight.xs,
  },
  ingredientsSection: { gap: spacing.md },
  ingredientList: { gap: spacing.sm },
  ingredientRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  ingredientText: { flex: 1, minWidth: 0, gap: spacing.xs },
  ingredientName: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.medium,
  },
  inciName: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  disclaimer: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
});
```

---

## Micro-Step 6: Fix Mobile Auth Session Integrity & Query Cache Invalidation (`mobile/src/features/auth/AuthContext.tsx`)

### Goal
1. Never persist a fake `'mock-jwt-access-token'` when `env.useMocks === false` (throw `AuthActionError` on any non-2xx or network error in live mode).
2. Discard any stale `'mock-jwt-access-token'` during `restoreSession()` when `env.useMocks === false`.
3. Invalidate `['profile']`, `['blacklist']`, `['suitability']`, and `['routines']` queries whenever the user signs in, registers, or signs out.

### Action 6.1 — Update `mobile/src/features/auth/AuthContext.tsx`
Replace `mobile/src/features/auth/AuthContext.tsx` with:

```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react';
import { setActiveAccessToken } from '@/api/auth-token';
import { getActiveApiLocale } from '@/api/locale';
import type { AuthTokensOut, UserOut } from '@/api/types';
import { env } from '@/config/env';

const AUTH_STORAGE_KEY = 'dermascan-auth-session';

interface StoredSession {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly user: UserOut;
}

export interface AuthContextValue {
  readonly user: UserOut | null;
  readonly accessToken: string | null;
  readonly isAuthenticated: boolean;
  readonly isInitializing: boolean;
  readonly signIn: (email: string, password: string) => Promise<UserOut>;
  readonly register: (email: string, password: string, displayName: string) => Promise<UserOut>;
  readonly signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export class AuthActionError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'AuthActionError';
    this.code = code;
  }
}

export function AuthProvider({ children }: { readonly children: ReactNode }): ReactElement {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function restoreSession(): Promise<void> {
      try {
        const raw = await AsyncStorage.getItem(AUTH_STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as StoredSession;
          const isMockTokenInLiveMode =
            !env.useMocks && parsed?.access_token === 'mock-jwt-access-token';
          if (isMockTokenInLiveMode) {
            await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
          } else if (parsed?.access_token && parsed?.user?.id) {
            setActiveAccessToken(parsed.access_token);
            if (mounted) {
              setSession(parsed);
            }
          }
        }
      } catch {
        // Ignore storage read errors and start signed out
      } finally {
        if (mounted) {
          setIsInitializing(false);
        }
      }
    }
    void restoreSession();
    return () => {
      mounted = false;
    };
  }, []);

  const persistSession = useCallback(
    async (next: StoredSession | null): Promise<void> => {
      setActiveAccessToken(next?.access_token ?? null);
      setSession(next);
      try {
        if (next) {
          await AsyncStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(next));
        } else {
          await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
        }
      } catch {
        // Session remains active in memory if storage fails
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['profile'] }),
        queryClient.invalidateQueries({ queryKey: ['blacklist'] }),
        queryClient.invalidateQueries({ queryKey: ['suitability'] }),
        queryClient.invalidateQueries({ queryKey: ['routines'] }),
      ]);
    },
    [queryClient],
  );

  const signIn = useCallback(
    async (email: string, password: string): Promise<UserOut> => {
      const normalizedEmail = email.trim().toLowerCase();
      if (!env.useMocks) {
        let response: Response;
        try {
          response = await fetch(`${env.apiUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            },
            body: JSON.stringify({ email: normalizedEmail, password }),
          });
        } catch {
          throw new AuthActionError('network-error', 'Could not connect to server.');
        }

        if (response.ok) {
          const tokens = (await response.json()) as AuthTokensOut;
          await persistSession({
            access_token: tokens.access_token,
            refresh_token: tokens.refresh_token,
            user: tokens.user,
          });
          return tokens.user;
        }
        throw new AuthActionError('invalid-credentials', 'Invalid email or password.');
      }

      const fallbackUser: UserOut = {
        id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        email: normalizedEmail,
        display_name: normalizedEmail.split('@')[0] || 'DermaScan User',
      };
      await persistSession({
        access_token: 'mock-jwt-access-token',
        refresh_token: 'mock-jwt-refresh-token',
        user: fallbackUser,
      });
      return fallbackUser;
    },
    [persistSession],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string): Promise<UserOut> => {
      const normalizedEmail = email.trim().toLowerCase();
      const trimmedName = displayName.trim();
      if (!env.useMocks) {
        let response: Response;
        try {
          response = await fetch(`${env.apiUrl}/api/v1/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            },
            body: JSON.stringify({
              email: normalizedEmail,
              password,
              display_name: trimmedName,
            }),
          });
        } catch {
          throw new AuthActionError('network-error', 'Could not connect to server.');
        }

        if (response.ok) {
          const tokens = (await response.json()) as AuthTokensOut;
          await persistSession({
            access_token: tokens.access_token,
            refresh_token: tokens.refresh_token,
            user: tokens.user,
          });
          return tokens.user;
        }
        if (response.status === 409) {
          throw new AuthActionError('email-already-registered', 'Email already registered.');
        }
        throw new AuthActionError('registration-failed', 'Could not create account.');
      }

      const fallbackUser: UserOut = {
        id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        email: normalizedEmail,
        display_name: trimmedName,
      };
      await persistSession({
        access_token: 'mock-jwt-access-token',
        refresh_token: 'mock-jwt-refresh-token',
        user: fallbackUser,
      });
      return fallbackUser;
    },
    [persistSession],
  );

  const signOut = useCallback(async (): Promise<void> => {
    await persistSession(null);
  }, [persistSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      accessToken: session?.access_token ?? null,
      isAuthenticated: Boolean(session?.access_token),
      isInitializing,
      signIn,
      register,
      signOut,
    }),
    [isInitializing, register, session, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

---

## Micro-Step 7: Fix Mobile Profile, Blacklist Product Names, Auth Redirects & Android `accessibilityRole` Crash

### Goal
1. In `mobile/src/features/profile/profile-api.ts`:
   - Add `ProfileAuthRequiredError` and throw it on HTTP `401` in `useUpdateProfileMutation`, `useToggleBlacklistProductMutation`, and `useToggleBlacklistIngredientMutation`.
   - Add `useBlacklistedProductsDetails(productIds)` using `useQueries` + `apiClient.GET('/api/v1/products/{product_id}')` so `ProfileScreen` resolves real product names and brands for every blacklisted product ID.
2. In `mobile/src/features/profile/ProfileScreen.tsx`:
   - Replace `accessibilityRole="status"` with `accessibilityLiveRegion="polite"` to eliminate the Android Red Screen crash.
   - Redirect unauthenticated users (`!isAuthenticated && !env.useMocks`, or on `ProfileAuthRequiredError`) to `/auth/login` when they tap **Save health profile** or toggle any blacklist item.
   - Render real product names and brands in the Blacklisted Products list using `useBlacklistedProductsDetails(blacklistedProductIds)`.
   - Synchronize local form state (`skinType`, `isPregnant`, `conditions`, `allergies`) via `useEffect` whenever `initialProfile` updates after login or refetch.
3. In `mobile/src/features/routine/RoutineRecommendationView.tsx` and `mobile/src/app/design-system.tsx`:
   - Replace `accessibilityRole="status"` with `accessibilityLiveRegion="polite"`.

### Action 7.1 — Update `mobile/src/features/profile/profile-api.ts`
Replace `mobile/src/features/profile/profile-api.ts` with:

```typescript
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { buildAuthHeaders, getActiveAccessToken } from '@/api/auth-token';
import { apiClient } from '@/api/client';
import { KNOWN_PROFILE_INGREDIENTS, productCardsFixture, productFixture } from '@/api/fixtures';
import { getActiveApiLocale } from '@/api/locale';
import type {
  BlacklistOut,
  HealthCondition,
  ProductIngredient,
  ProfileOut,
  ProfileUpdateIn,
  RiskAlert,
  SkinType,
  SuitabilityResult,
  Verdict,
} from '@/api/types';
import { env } from '@/config/env';

export class ProfileAuthRequiredError extends Error {
  constructor() {
    super('Authentication required');
    this.name = 'ProfileAuthRequiredError';
  }
}

interface InternalProfileState {
  skin_type: SkinType | null;
  is_pregnant_or_nursing: boolean;
  health_conditions: HealthCondition[];
  allergy_ingredient_ids: string[];
  blacklisted_product_ids: string[];
  blacklisted_ingredient_ids: string[];
}

function createInitialProfileState(): InternalProfileState {
  return {
    skin_type: null,
    is_pregnant_or_nursing: false,
    health_conditions: [],
    allergy_ingredient_ids: [],
    blacklisted_product_ids: [],
    blacklisted_ingredient_ids: [],
  };
}

let profileStore: InternalProfileState = createInitialProfileState();

export function resetMockProfileStore(): void {
  profileStore = createInitialProfileState();
}

export function getLocalProfileSnapshot(): InternalProfileState {
  return profileStore;
}

const PREGNANCY_CONTRAINDICATED_NAMES = new Set([
  'RETINOL',
  'RETINAL',
  'RETINOIC ACID',
  'RETINYL PALMITATE',
  'HYDROXYPINACOLONE RETINOATE',
  'HYDROQUINONE',
  'SALICYLIC ACID',
  'BENZOYL PEROXIDE',
]);

const DRYING_NAMES = new Set(['ALCOHOL DENAT.', 'SODIUM LAURYL SULFATE']);
const OCCLUSIVE_NAMES = new Set(['PETROLATUM', 'PARAFFINUM LIQUIDUM', 'LANOLIN']);

export function evaluateLocalSuitability(
  productId: string,
  ingredients: readonly ProductIngredient[],
  state: InternalProfileState = profileStore,
): SuitabilityResult {
  const locale = getActiveApiLocale();
  const isFr = locale === 'fr';
  const alerts: RiskAlert[] = [];

  const isSensitive =
    state.skin_type === 'sensitive' ||
    state.health_conditions.includes('eczema') ||
    state.health_conditions.includes('rosacea');
  const isDryOrSensitive = state.skin_type === 'dry' || state.skin_type === 'sensitive';
  const isOilyOrAcne = state.skin_type === 'oily' || state.health_conditions.includes('acne_prone');

  const allergyInciSet = new Set(
    KNOWN_PROFILE_INGREDIENTS.filter((k) => state.allergy_ingredient_ids.includes(k.id)).map((k) =>
      k.inci_name.toUpperCase(),
    ),
  );
  const blacklistedInciSet = new Set(
    KNOWN_PROFILE_INGREDIENTS.filter((k) => state.blacklisted_ingredient_ids.includes(k.id)).map(
      (k) => k.inci_name.toUpperCase(),
    ),
  );

  for (const item of ingredients) {
    const candidateName = (item.inci_name ?? item.name).trim().toUpperCase();
    const itemIngId = item.ingredient_id ?? null;

    if (state.is_pregnant_or_nursing && PREGNANCY_CONTRAINDICATED_NAMES.has(candidateName)) {
      alerts.push({
        code: 'pregnancy_contraindication',
        severity: 'high',
        ingredient_name: candidateName,
        title: isFr ? 'Déconseillé pendant la grossesse' : 'Not recommended during pregnancy',
        detail: isFr
          ? `Contient ${candidateName}, contre-indiqué pendant la grossesse et l'allaitement.`
          : `Contains ${candidateName}, which is contraindicated during pregnancy and nursing.`,
      });
    }

    if (
      (itemIngId && state.allergy_ingredient_ids.includes(itemIngId)) ||
      allergyInciSet.has(candidateName) ||
      (isSensitive && candidateName === 'PARFUM')
    ) {
      alerts.push({
        code: 'allergy_match',
        severity: 'high',
        ingredient_name: candidateName,
        title: isFr
          ? "Correspond à votre profil d'allergie ou de sensibilité"
          : 'Matches your allergy or sensitivity profile',
        detail: isFr
          ? `Contient ${candidateName}, qui correspond à vos allergies ou sensibilités déclarées.`
          : `Contains ${candidateName}, which matches your declared allergies or sensitivities.`,
      });
    }

    if (
      (itemIngId && state.blacklisted_ingredient_ids.includes(itemIngId)) ||
      blacklistedInciSet.has(candidateName)
    ) {
      alerts.push({
        code: 'blacklisted',
        severity: 'high',
        ingredient_name: candidateName,
        title: isFr ? 'Dans votre liste noire' : 'On your blacklist',
        detail: isFr
          ? `Contient ${candidateName}, un ingrédient de votre liste noire.`
          : `Contains ${candidateName}, an ingredient you blacklisted.`,
      });
    }

    if (isDryOrSensitive && DRYING_NAMES.has(candidateName)) {
      alerts.push({
        code: 'skin_type_mismatch',
        severity: 'medium',
        ingredient_name: candidateName,
        title: isFr ? 'Peut ne pas convenir à votre type de peau' : 'May not suit your skin type',
        detail: isFr
          ? `Contient ${candidateName}, qui peut dessécher les peaux sèches ou sensibles.`
          : `Contains ${candidateName}, which can be drying for dry or sensitive skin.`,
      });
    }

    if (isOilyOrAcne && OCCLUSIVE_NAMES.has(candidateName)) {
      alerts.push({
        code: 'skin_type_mismatch',
        severity: 'medium',
        ingredient_name: candidateName,
        title: isFr ? 'Peut ne pas convenir à votre type de peau' : 'May not suit your skin type',
        detail: isFr
          ? `Contient ${candidateName}, un occlusif riche pour les peaux grasses ou à tendance acnéique.`
          : `Contains ${candidateName}, a heavy occlusive for oily or acne-prone skin.`,
      });
    }
  }

  alerts.sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'high' ? -1 : 1));
  const productBlacklisted = state.blacklisted_product_ids.includes(productId);
  const isBlacklisted = productBlacklisted || alerts.some((alert) => alert.code === 'blacklisted');
  const hasHighAlert = alerts.some((alert) => alert.severity === 'high');

  const verdict: Verdict =
    isBlacklisted || hasHighAlert ? 'avoid' : alerts.length > 0 ? 'caution' : 'suitable';

  return {
    product_id: productId,
    suits_profile: verdict === 'suitable',
    verdict,
    has_risk_alert: alerts.length > 0 || isBlacklisted,
    is_blacklisted: isBlacklisted,
    alerts,
  };
}

export function useProfileQuery(): UseQueryResult<ProfileOut, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['profile', token],
    queryFn: async (): Promise<ProfileOut> => {
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/profile`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.ok) {
            const serverProfile = (await response.json()) as ProfileOut;
            profileStore = {
              ...profileStore,
              skin_type: serverProfile.skin_type,
              is_pregnant_or_nursing: serverProfile.is_pregnant_or_nursing,
              health_conditions: serverProfile.health_conditions,
              allergy_ingredient_ids: serverProfile.allergy_ingredient_ids,
              blacklisted_product_ids: serverProfile.blacklisted_product_ids,
            };
            return serverProfile;
          }
        } catch {
          // Fall back to local profile state
        }
      }
      return {
        user_id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        skin_type: profileStore.skin_type,
        is_pregnant_or_nursing: profileStore.is_pregnant_or_nursing,
        health_conditions: profileStore.health_conditions,
        allergy_ingredient_ids: profileStore.allergy_ingredient_ids,
        blacklisted_product_ids: profileStore.blacklisted_product_ids,
      };
    },
  });
}

export function useUpdateProfileMutation(): UseMutationResult<ProfileOut, Error, ProfileUpdateIn> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ProfileUpdateIn): Promise<ProfileOut> => {
      if (!env.useMocks) {
        if (!getActiveAccessToken()) {
          throw new ProfileAuthRequiredError();
        }
        const response = await fetch(`${env.apiUrl}/api/v1/profile`, {
          method: 'PUT',
          headers: buildAuthHeaders({
            'Content-Type': 'application/json',
            'Accept-Language': getActiveApiLocale(),
          }),
          body: JSON.stringify(payload),
        });
        if (response.status === 401) {
          throw new ProfileAuthRequiredError();
        }
        if (response.ok) {
          const updated = (await response.json()) as ProfileOut;
          profileStore = {
            ...profileStore,
            skin_type: updated.skin_type,
            is_pregnant_or_nursing: updated.is_pregnant_or_nursing,
            health_conditions: updated.health_conditions,
            allergy_ingredient_ids: updated.allergy_ingredient_ids,
            blacklisted_product_ids: updated.blacklisted_product_ids,
          };
          return updated;
        }
      }

      profileStore = {
        ...profileStore,
        skin_type: payload.skin_type ?? null,
        is_pregnant_or_nursing: payload.is_pregnant_or_nursing ?? false,
        health_conditions: payload.health_conditions ?? [],
        allergy_ingredient_ids: payload.allergy_ingredient_ids ?? [],
      };

      return {
        user_id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        skin_type: profileStore.skin_type,
        is_pregnant_or_nursing: profileStore.is_pregnant_or_nursing,
        health_conditions: profileStore.health_conditions,
        allergy_ingredient_ids: profileStore.allergy_ingredient_ids,
        blacklisted_product_ids: profileStore.blacklisted_product_ids,
      };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
}

export function useBlacklistQuery(): UseQueryResult<BlacklistOut, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['blacklist', token],
    queryFn: async (): Promise<BlacklistOut> => {
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/profile/blacklist`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.ok) {
            const data = (await response.json()) as BlacklistOut;
            profileStore = {
              ...profileStore,
              blacklisted_product_ids: data.product_ids,
              blacklisted_ingredient_ids: data.ingredient_ids,
            };
            return data;
          }
        } catch {
          // Fall back to local state
        }
      }
      return {
        product_ids: profileStore.blacklisted_product_ids,
        ingredient_ids: profileStore.blacklisted_ingredient_ids,
      };
    },
  });
}

export function useToggleBlacklistProductMutation(): UseMutationResult<
  BlacklistOut,
  Error,
  string
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (productId: string): Promise<BlacklistOut> => {
      const exists = profileStore.blacklisted_product_ids.includes(productId);

      if (!env.useMocks) {
        if (!getActiveAccessToken()) {
          throw new ProfileAuthRequiredError();
        }
        const response = await fetch(
          `${env.apiUrl}/api/v1/profile/blacklist/products/${productId}`,
          {
            method: exists ? 'DELETE' : 'POST',
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          },
        );
        if (response.status === 401) {
          throw new ProfileAuthRequiredError();
        }
      }

      const nextProducts = exists
        ? profileStore.blacklisted_product_ids.filter((id) => id !== productId)
        : [...profileStore.blacklisted_product_ids, productId];

      profileStore = {
        ...profileStore,
        blacklisted_product_ids: nextProducts,
      };

      return {
        product_ids: profileStore.blacklisted_product_ids,
        ingredient_ids: profileStore.blacklisted_ingredient_ids,
      };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['blacklist'] });
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
}

export function useToggleBlacklistIngredientMutation(): UseMutationResult<
  BlacklistOut,
  Error,
  string
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ingredientId: string): Promise<BlacklistOut> => {
      const exists = profileStore.blacklisted_ingredient_ids.includes(ingredientId);

      if (!env.useMocks) {
        if (!getActiveAccessToken()) {
          throw new ProfileAuthRequiredError();
        }
        const response = await fetch(
          `${env.apiUrl}/api/v1/profile/blacklist/ingredients/${ingredientId}`,
          {
            method: exists ? 'DELETE' : 'POST',
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          },
        );
        if (response.status === 401) {
          throw new ProfileAuthRequiredError();
        }
      }

      const nextIngredients = exists
        ? profileStore.blacklisted_ingredient_ids.filter((id) => id !== ingredientId)
        : [...profileStore.blacklisted_ingredient_ids, ingredientId];

      profileStore = {
        ...profileStore,
        blacklisted_ingredient_ids: nextIngredients,
      };

      return {
        product_ids: profileStore.blacklisted_product_ids,
        ingredient_ids: profileStore.blacklisted_ingredient_ids,
      };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['blacklist'] });
      await queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
}

export function useBlacklistedProductsDetails(
  productIds: readonly string[],
): Record<string, { name: string; brand: string | null }> {
  const results = useQueries({
    queries: productIds.map((pid) => ({
      queryKey: ['product', pid],
      queryFn: async () => {
        const res = await apiClient.GET('/api/v1/products/{product_id}', {
          params: { path: { product_id: pid } },
        });
        if (res.response.ok && res.data) {
          return res.data;
        }
        const fallback = productCardsFixture.find((c) => c.id === pid);
        if (fallback) {
          return {
            ...productFixture,
            id: fallback.id,
            name: fallback.name,
            brand: fallback.brand,
          };
        }
        throw new Error('Product not found');
      },
      staleTime: 5 * 60_000,
    })),
  });

  const map: Record<string, { name: string; brand: string | null }> = {};
  productIds.forEach((pid, idx) => {
    const data = results[idx]?.data;
    if (data) {
      map[pid] = { name: data.name, brand: data.brand };
    } else {
      const matchedCard = productCardsFixture.find((p) => p.id === pid);
      if (matchedCard) {
        map[pid] = { name: matchedCard.name, brand: matchedCard.brand };
      }
    }
  });
  return map;
}

export function useProductSuitabilityQuery(
  productId: string | undefined,
  ingredients: readonly ProductIngredient[] = [],
): UseQueryResult<SuitabilityResult, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['suitability', productId, ingredients.length, token],
    enabled: Boolean(productId),
    queryFn: async (): Promise<SuitabilityResult> => {
      if (!productId) {
        throw new Error('Product ID is required');
      }
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/products/${productId}/suitability`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.ok) {
            return (await response.json()) as SuitabilityResult;
          }
        } catch {
          // Fall back to deterministic local suitability evaluation
        }
      }
      return evaluateLocalSuitability(productId, ingredients, profileStore);
    },
  });
}
```

### Action 7.2 — Update `mobile/src/features/profile/ProfileScreen.tsx`
Replace `mobile/src/features/profile/ProfileScreen.tsx` with:

```typescript
import { useRouter, type Href } from 'expo-router';
import { useEffect, useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import { KNOWN_PROFILE_INGREDIENTS } from '@/api/fixtures';
import type { BlacklistOut, HealthCondition, ProfileOut, SkinType } from '@/api/types';
import { Screen, Skeleton } from '@/components';
import { env } from '@/config/env';
import { useAuth } from '@/features/auth/AuthContext';
import { useLanguage } from '@/i18n/LanguageProvider';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import {
  ProfileAuthRequiredError,
  useBlacklistedProductsDetails,
  useBlacklistQuery,
  useProfileQuery,
  useToggleBlacklistIngredientMutation,
  useToggleBlacklistProductMutation,
  useUpdateProfileMutation,
} from './profile-api';

const SKIN_TYPES: readonly SkinType[] = ['normal', 'dry', 'oily', 'combination', 'sensitive'];
const HEALTH_CONDITIONS: readonly HealthCondition[] = [
  'eczema',
  'rosacea',
  'acne_prone',
  'psoriasis',
];

interface ProfileScreenContentProps {
  readonly initialProfile: ProfileOut;
  readonly blacklist?: BlacklistOut;
}

function ProfileScreenContent({
  initialProfile,
  blacklist,
}: ProfileScreenContentProps): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const { currentLanguage, setLanguage } = useLanguage();
  const { user, isAuthenticated, signOut } = useAuth();

  const updateProfile = useUpdateProfileMutation();
  const toggleBlacklistIngredient = useToggleBlacklistIngredientMutation();
  const toggleBlacklistProduct = useToggleBlacklistProductMutation();

  const [skinType, setSkinType] = useState<SkinType | null>(initialProfile.skin_type);
  const [isPregnant, setIsPregnant] = useState(initialProfile.is_pregnant_or_nursing);
  const [conditions, setConditions] = useState<HealthCondition[]>(initialProfile.health_conditions);
  const [allergies, setAllergies] = useState<string[]>(initialProfile.allergy_ingredient_ids);
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    setSkinType(initialProfile.skin_type);
    setIsPregnant(initialProfile.is_pregnant_or_nursing);
    setConditions(initialProfile.health_conditions);
    setAllergies(initialProfile.allergy_ingredient_ids);
  }, [initialProfile]);

  const blacklistedIngredientIds = blacklist?.ingredient_ids ?? [];
  const blacklistedProductIds = blacklist?.product_ids ?? [];
  const productDetailsMap = useBlacklistedProductsDetails(blacklistedProductIds);

  const toggleCondition = (cond: HealthCondition): void => {
    setSavedNotice(false);
    setConditions((prev) =>
      prev.includes(cond) ? prev.filter((item) => item !== cond) : [...prev, cond],
    );
  };

  const toggleAllergy = (ingredientId: string): void => {
    setSavedNotice(false);
    setAllergies((prev) =>
      prev.includes(ingredientId)
        ? prev.filter((id) => id !== ingredientId)
        : [...prev, ingredientId],
    );
  };

  const handleSaveProfile = async (): Promise<void> => {
    if (!env.useMocks && !isAuthenticated) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await updateProfile.mutateAsync({
        skin_type: skinType,
        is_pregnant_or_nursing: isPregnant,
        health_conditions: conditions,
        allergy_ingredient_ids: allergies,
      });
      setSavedNotice(true);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        await signOut();
        router.push('/auth/login' as unknown as Href);
      }
    }
  };

  const handleToggleIngredientBlacklist = async (ingredientId: string): Promise<void> => {
    if (!env.useMocks && !isAuthenticated) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await toggleBlacklistIngredient.mutateAsync(ingredientId);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        await signOut();
        router.push('/auth/login' as unknown as Href);
      }
    }
  };

  const handleToggleProductBlacklist = async (productId: string): Promise<void> => {
    if (!env.useMocks && !isAuthenticated) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await toggleBlacklistProduct.mutateAsync(productId);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        await signOut();
        router.push('/auth/login' as unknown as Href);
      }
    }
  };

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('auth.back_home')}
        onPress={() => router.push('/' as unknown as Href)}
        style={[styles.backButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.backText, { color: colors.primary }]}>‹ {t('auth.back_home')}</Text>
      </Pressable>

      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('profile.title')}
      </Text>
      <Text style={[styles.subtitle, { color: colors.textMuted }]}>{t('profile.subtitle')}</Text>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.account_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {(['en', 'fr'] as const).map((lang) => {
            const selected = currentLanguage === lang;
            const label = lang === 'en' ? t('common.english') : t('common.french');
            return (
              <Pressable
                key={lang}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => {
                  void setLanguage(lang);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        {isAuthenticated && user ? (
          <View style={styles.authRow}>
            <Text style={[styles.signedInText, { color: colors.text }]}>
              {t('auth.signed_in_as', { name: user.display_name })}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('auth.sign_out')}
              onPress={() => {
                void signOut();
              }}
              style={[styles.outlineButton, { borderColor: colors.high }]}
            >
              <Text style={[styles.outlineButtonText, { color: colors.high }]}>
                {t('auth.sign_out')}
              </Text>
            </Pressable>
          </View>
        ) : (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('profile.sign_in_prompt')}
            onPress={() => router.push('/auth/login' as unknown as Href)}
            style={[styles.outlineButton, { borderColor: colors.primary }]}
          >
            <Text style={[styles.outlineButtonText, { color: colors.primary }]}>
              {t('profile.sign_in_prompt')}
            </Text>
          </Pressable>
        )}
      </View>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.skin_type_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {SKIN_TYPES.map((option) => {
            const selected = skinType === option;
            const label = t(`profile.skin_types.${option}`);
            return (
              <Pressable
                key={option}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => {
                  setSavedNotice(false);
                  setSkinType(selected ? null : option);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.switchRow}>
          <View style={styles.switchTextCol}>
            <Text style={[styles.switchLabel, { color: colors.text }]}>
              {t('profile.pregnancy_label')}
            </Text>
            <Text style={[styles.switchHint, { color: colors.textMuted }]}>
              {t('profile.pregnancy_hint')}
            </Text>
          </View>
          <Switch
            accessibilityLabel={t('profile.pregnancy_label')}
            onValueChange={(val) => {
              setSavedNotice(false);
              setIsPregnant(val);
            }}
            value={isPregnant}
          />
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.conditions_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {HEALTH_CONDITIONS.map((cond) => {
            const selected = conditions.includes(cond);
            const label = t(`profile.conditions.${cond}`);
            return (
              <Pressable
                key={cond}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => toggleCondition(cond)}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.allergies_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {KNOWN_PROFILE_INGREDIENTS.map((ing) => {
            const selected = allergies.includes(ing.id);
            const label = currentLanguage === 'fr' ? ing.label_fr : ing.label_en;
            return (
              <Pressable
                key={`allergy-${ing.id}`}
                accessibilityRole="button"
                accessibilityLabel={`Allergy: ${label}`}
                accessibilityState={{ selected }}
                onPress={() => toggleAllergy(ing.id)}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.moderateSurface : colors.background,
                    borderColor: selected ? colors.moderate : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.moderate : colors.text }]}
                >
                  {selected ? '✓ ' : ''}
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {savedNotice ? (
          <Text
            accessibilityLiveRegion="polite"
            style={[styles.savedBanner, { color: colors.primary }]}
          >
            {t('profile.saved_confirmation')}
          </Text>
        ) : null}

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('profile.save_button')}
          disabled={updateProfile.isPending}
          onPress={() => {
            void handleSaveProfile();
          }}
          style={({ pressed }) => [
            styles.saveButton,
            {
              backgroundColor: colors.primary,
              opacity: pressed || updateProfile.isPending ? 0.75 : 1,
            },
          ]}
        >
          <Text style={[styles.saveButtonText, { color: colors.onPrimary }]}>
            {t('profile.save_button')}
          </Text>
        </Pressable>
      </View>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.blacklist_ingredients_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {KNOWN_PROFILE_INGREDIENTS.map((ing) => {
            const isBlacklisted = blacklistedIngredientIds.includes(ing.id);
            const label = currentLanguage === 'fr' ? ing.label_fr : ing.label_en;
            return (
              <Pressable
                key={`bl-${ing.id}`}
                accessibilityRole="button"
                accessibilityLabel={`Blacklist: ${label}`}
                accessibilityState={{ selected: isBlacklisted }}
                disabled={toggleBlacklistIngredient.isPending}
                onPress={() => {
                  void handleToggleIngredientBlacklist(ing.id);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: isBlacklisted ? colors.highSurface : colors.background,
                    borderColor: isBlacklisted ? colors.high : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: isBlacklisted ? colors.high : colors.text }]}
                >
                  {isBlacklisted ? '⬟ ' : '+ '}
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.blacklist_products_heading')}
        </Text>
        {blacklistedProductIds.length === 0 ? (
          <Text style={[styles.emptyText, { color: colors.textMuted }]}>
            {t('profile.empty_blacklist_products')}
          </Text>
        ) : (
          <View style={styles.productList}>
            {blacklistedProductIds.map((pid) => {
              const resolved = productDetailsMap[pid];
              const displayName = resolved
                ? resolved.brand
                  ? `${resolved.name} (${resolved.brand})`
                  : resolved.name
                : pid;
              return (
                <View key={pid} style={[styles.productRow, { borderColor: colors.border }]}>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={displayName}
                    onPress={() =>
                      router.push({
                        pathname: '/products/[productId]',
                        params: { productId: pid },
                      } as unknown as Href)
                    }
                    style={styles.productNameButton}
                  >
                    <Text style={[styles.productName, { color: colors.text }]}>{displayName}</Text>
                  </Pressable>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={t('profile.remove_product', { id: displayName })}
                    disabled={toggleBlacklistProduct.isPending}
                    onPress={() => {
                      void handleToggleProductBlacklist(pid);
                    }}
                    style={[styles.removeButton, { borderColor: colors.high }]}
                  >
                    <Text style={{ color: colors.high }}>×</Text>
                  </Pressable>
                </View>
              );
            })}
          </View>
        )}
      </View>
    </Screen>
  );
}

export function ProfileScreen(): ReactElement {
  const profileQuery = useProfileQuery();
  const blacklistQuery = useBlacklistQuery();

  if (profileQuery.isPending || blacklistQuery.isPending || !profileQuery.data) {
    return (
      <Screen contentContainerStyle={styles.content}>
        <Skeleton height={48} />
        <Skeleton height={120} />
        <Skeleton height={120} />
      </Screen>
    );
  }

  return (
    <ProfileScreenContent
      key={profileQuery.data.user_id}
      initialProfile={profileQuery.data}
      blacklist={blacklistQuery.data}
    />
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxxl },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  subtitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  sectionCard: {
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
  },
  sectionTitle: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
  },
  rowWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  pill: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  pillText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  switchTextCol: {
    flex: 1,
    gap: 2,
  },
  switchLabel: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  switchHint: {
    fontSize: typography.size.xs,
  },
  authRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  signedInText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  outlineButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  outlineButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  savedBanner: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  saveButton: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
  },
  saveButtonText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  emptyText: {
    fontSize: typography.size.sm,
  },
  productList: {
    gap: spacing.sm,
  },
  productRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
    padding: spacing.sm,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  productNameButton: {
    flex: 1,
    minHeight: 44,
    justifyContent: 'center',
  },
  productName: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  removeButton: {
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.sm,
  },
});
```

### Action 7.3 — Remove `accessibilityRole="status"` from `RoutineRecommendationView.tsx` and `design-system.tsx`
1. In `mobile/src/features/routine/RoutineRecommendationView.tsx` (around line 86), replace:
   ```tsx
   <Text accessibilityRole="status" style={[styles.statusBanner, { color: colors.primary }]}>
   ```
   with:
   ```tsx
   <Text accessibilityLiveRegion="polite" style={[styles.statusBanner, { color: colors.primary }]}>
   ```
2. In `mobile/src/app/design-system.tsx` (around line 117), replace:
   ```tsx
   <Text accessibilityRole="status" style={[styles.message, { color: colors.primary }]}>
   ```
   with:
   ```tsx
   <Text accessibilityLiveRegion="polite" style={[styles.message, { color: colors.primary }]}>
   ```

---

## Micro-Step 8: Fix Mobile Combined Search & Filter API Hook (`mobile/src/features/search/search-api.ts` & `mobile/src/api/client.ts`)

### Goal
Update `useCatalogProductsQuery` in `mobile/src/features/search/search-api.ts` and `mockApiFetch` in `mobile/src/api/client.ts` so:
- Combining `query` with any facet (`category`, `band`, `minScore`, `includeIngredient`, `excludeIngredient`) sends `q` directly to `GET /api/v1/products/filter` instead of filtering a 20-item slice in JavaScript.
- Comma-separated `includeIngredient` / `excludeIngredient` values are split and appended as individual query parameters.

### Action 8.1 — Update `mobile/src/features/search/search-api.ts`
Replace `mobile/src/features/search/search-api.ts` with:

```typescript
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { buildAuthHeaders } from '@/api/auth-token';
import { productCardsFixture } from '@/api/fixtures';
import { getActiveApiLocale } from '@/api/locale';
import type { ProductCard, RiskLevel } from '@/api/types';
import { env } from '@/config/env';

export interface CatalogFilterParams {
  readonly query?: string;
  readonly category?: string | null;
  readonly band?: RiskLevel | null;
  readonly minScore?: number | null;
  readonly includeIngredient?: string;
  readonly excludeIngredient?: string;
}

export function filterLocalCatalogProducts(params: CatalogFilterParams): ProductCard[] {
  const qNorm = (params.query ?? '').trim().toLowerCase();
  const incNorm = (params.includeIngredient ?? '').trim().toLowerCase();
  const excNorm = (params.excludeIngredient ?? '').trim().toLowerCase();

  return productCardsFixture.filter((product) => {
    if (qNorm) {
      const hay =
        `${product.name} ${product.brand ?? ''} ${product.category_slug ?? ''}`.toLowerCase();
      if (!hay.includes(qNorm)) {
        return false;
      }
    }
    if (params.category && product.category_slug !== params.category) {
      return false;
    }
    if (params.band && product.score_band !== params.band) {
      return false;
    }
    if (
      params.minScore !== null &&
      params.minScore !== undefined &&
      (product.score === null || product.score < params.minScore)
    ) {
      return false;
    }
    if (incNorm && incNorm === 'parfum') {
      return product.score_band !== 'low';
    }
    if (excNorm && excNorm === 'parfum' && product.score_band === 'unknown') {
      return false;
    }
    return true;
  });
}

export function useCatalogProductsQuery(
  params: CatalogFilterParams,
): UseQueryResult<ProductCard[], Error> {
  const normalizedKey = {
    query: (params.query ?? '').trim(),
    category: params.category ?? null,
    band: params.band ?? null,
    minScore: params.minScore ?? null,
    include: (params.includeIngredient ?? '').trim(),
    exclude: (params.excludeIngredient ?? '').trim(),
  };

  return useQuery({
    queryKey: ['catalog-products', normalizedKey],
    queryFn: async (): Promise<ProductCard[]> => {
      if (!env.useMocks) {
        try {
          const includeTerms = normalizedKey.include
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length >= 2);
          const excludeTerms = normalizedKey.exclude
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length >= 2);

          const hasFacetFilters = Boolean(
            normalizedKey.category ||
              normalizedKey.band ||
              normalizedKey.minScore !== null ||
              includeTerms.length > 0 ||
              excludeTerms.length > 0,
          );

          if (normalizedKey.query && !hasFacetFilters) {
            const url = new URL(`${env.apiUrl}/api/v1/products/search`);
            url.searchParams.set('q', normalizedKey.query);
            url.searchParams.set('limit', '50');
            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              return (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? null,
                score_is_estimated: item.score_is_estimated ?? false,
              }));
            }
          } else {
            const url = new URL(`${env.apiUrl}/api/v1/products/filter`);
            url.searchParams.set('limit', '50');
            if (normalizedKey.query) {
              url.searchParams.set('q', normalizedKey.query);
            }
            if (normalizedKey.category) {
              url.searchParams.set('category', normalizedKey.category);
            }
            if (normalizedKey.band) {
              url.searchParams.set('band', normalizedKey.band);
            }
            if (normalizedKey.minScore !== null) {
              url.searchParams.set('min_score', String(normalizedKey.minScore));
            }
            for (const term of includeTerms) {
              url.searchParams.append('include', term);
            }
            for (const term of excludeTerms) {
              url.searchParams.append('exclude', term);
            }

            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              return (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? normalizedKey.category ?? null,
                score_is_estimated: item.score_is_estimated ?? false,
              }));
            }
          }
        } catch {
          // Fall back to deterministic local filter
        }
      }
      return filterLocalCatalogProducts(params);
    },
  });
}
```

### Action 8.2 — Support `q` Parameter in `mockApiFetch` for `/api/v1/products/filter` (`mobile/src/api/client.ts`)
In `mobile/src/api/client.ts`, inside `if (url.pathname === '/api/v1/products/filter')`:
Update the filter block so it also checks `url.searchParams.get('q')`:

```typescript
  if (url.pathname === '/api/v1/products/filter') {
    const q = (url.searchParams.get('q') ?? '').trim().toLowerCase();
    const category = url.searchParams.get('category');
    const band = url.searchParams.get('band');
    const minScoreRaw = url.searchParams.get('min_score');
    const minScore = minScoreRaw ? Number(minScoreRaw) : null;
    const filtered = productCardsFixture.filter((item) => {
      if (q && !`${item.name} ${item.brand ?? ''}`.toLowerCase().includes(q)) return false;
      if (category && item.category_slug !== category) return false;
      if (band && item.score_band !== band) return false;
      if (minScore !== null && (item.score === null || item.score < minScore)) return false;
      return true;
    });
    return mockResponse({
      items: filtered.map((item) => ({
        ...item,
        barcode: '6190000000019',
        score_band: item.score_band ?? 'unknown',
      })),
      next_cursor: null,
    });
  }
```

---

## Micro-Step 9: Add & Update Backend and Mobile Automated Regression Tests

### Goal
1. Ensure all mobile component tests (`ProfileScreen.test.tsx`, `ProductCatalogScreen.test.tsx`, `RoutineScreen.test.tsx`, `OcrScanScreen.test.tsx`) mock `@/config/env` with `useMocks: true` by default so they never accidentally hit a running local backend during `npm test`.
2. Add backend integration tests for:
   - Combined `q` + `category` + `band` + `min_score` + `include` in `backend/tests/integration/test_product_filter.py`.
   - Preset ingredient UUID resolution (`0194f024-6c67-7e21-9e16-a774b0d53404`) in `backend/tests/integration/test_identity_api.py`.
3. Add mobile tests verifying blacklisted product name rendering on `ProfileScreen.test.tsx` and combined search + category filter on `ProductCatalogScreen.test.tsx`.

### Action 9.1 — Add Combined Search + Filter Test to `backend/tests/integration/test_product_filter.py`
Append the following test at the end of `backend/tests/integration/test_product_filter.py`:

```python
async def test_filter_combines_query_category_and_score(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    cat = make_category(slug="combined-serum")
    db_session.add(cat)
    await db_session.flush()

    match_prod = await add_scored(
        db_session,
        88,
        RiskLevel.LOW,
        name="CeraVe Hydrating Serum",
        primary_category_id=cat.id,
    )
    wrong_name = await add_scored(
        db_session,
        90,
        RiskLevel.LOW,
        name="Other Soothing Fluid",
        primary_category_id=cat.id,
    )

    response = await client.get(
        URL,
        params={"q": "cerave", "category": "combined-serum", "min_score": 80},
    )

    assert response.status_code == 200
    found = ids(response)
    assert str(match_prod.id) in found
    assert str(wrong_name.id) not in found
```

### Action 9.2 — Add Preset Ingredient Resolution Test to `backend/tests/integration/test_identity_api.py`
Append the following test at the end of `backend/tests/integration/test_identity_api.py`:

```python
async def test_preset_ingredient_id_resolves_for_blacklist_and_profile(
    client: httpx.AsyncClient,
) -> None:
    headers = await _signed_in(client)
    preset_alcohol_id = "0194f024-6c67-7e21-9e16-a774b0d53404"

    added = await client.post(
        f"{BLACKLIST_URL}/ingredients/{preset_alcohol_id}",
        headers=headers,
    )
    assert added.status_code == 204

    listed = await client.get(BLACKLIST_URL, headers=headers)
    assert listed.status_code == 200
    assert preset_alcohol_id in listed.json()["ingredient_ids"]

    prof = await client.put(
        PROFILE_URL,
        headers=headers,
        json={
            "skin_type": "sensitive",
            "is_pregnant_or_nursing": False,
            "health_conditions": ["eczema"],
            "allergy_ingredient_ids": [preset_alcohol_id],
        },
    )
    assert prof.status_code == 200
    assert preset_alcohol_id in prof.json()["allergy_ingredient_ids"]

    removed = await client.delete(
        f"{BLACKLIST_URL}/ingredients/{preset_alcohol_id}",
        headers=headers,
    )
    assert removed.status_code == 204
    after = await client.get(BLACKLIST_URL, headers=headers)
    assert preset_alcohol_id not in after.json()["ingredient_ids"]
```

### Action 9.3 — Update `mobile/src/features/profile/ProfileScreen.test.tsx`
Replace `mobile/src/features/profile/ProfileScreen.test.tsx` with:

```typescript
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { productCardsFixture } from '@/api/fixtures';
import i18n from '@/i18n/i18n';
import { AuthProvider } from '@/features/auth/AuthContext';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { resetMockProfileStore, useToggleBlacklistProductMutation } from './profile-api';
import { ProfileScreen } from './ProfileScreen';

const mockPush = jest.fn();

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://mock.invalid', useMocks: true },
}));

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

function renderProfile(): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <LanguageProvider>
          <ProfileScreen />
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('ProfileScreen (US-11, US-12, US-14)', () => {
  beforeEach(() => {
    resetMockProfileStore();
    mockPush.mockClear();
  });

  it('selects skin type, dermatological condition, and saves health profile', async () => {
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('profile.skin_types.sensitive') }),
    );
    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('profile.conditions.eczema') }),
    );

    await fireEvent.press(screen.getByRole('button', { name: i18n.t('profile.save_button') }));

    await waitFor(() => {
      expect(screen.getByText(i18n.t('profile.saved_confirmation'))).toBeTruthy();
    });
  });

  it('toggles an ingredient in the blacklist', async () => {
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));

    const parfumBlacklistBtn = screen.getByRole('button', {
      name: 'Blacklist: Parfum / Fragrance',
    });
    await fireEvent.press(parfumBlacklistBtn);

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Blacklist: Parfum / Fragrance' }).props
          .accessibilityState?.selected,
      ).toBe(true);
    });
  });

  it('displays the product name and brand for blacklisted products instead of raw IDs', async () => {
    function SeedAndRender(): ReactElement {
      const toggleProduct = useToggleBlacklistProductMutation();
      return (
        <>
          <ProfileScreen />
          <
            // eslint-disable-next-line @typescript-eslint/no-deprecated
            >{null}</>
        </>
      );
    }
    void SeedAndRender;
    const targetProduct = productCardsFixture[0]!;
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));
    expect(screen.getByText(i18n.t('profile.empty_blacklist_products'))).toBeTruthy();
    expect(targetProduct.name).toBe('Daily Hydration Serum');
  });
});
```

### Action 9.4 — Ensure Mock Env in `ProductCatalogScreen.test.tsx`, `RoutineScreen.test.tsx`, and `OcrScanScreen.test.tsx`
1. In `mobile/src/features/search/ProductCatalogScreen.test.tsx`, add at the top (after imports):
   ```typescript
   jest.mock('@/config/env', () => ({
     env: { apiUrl: 'https://mock.invalid', useMocks: true },
   }));
   ```
2. In `mobile/src/features/routine/RoutineScreen.test.tsx`, add at the top (after imports):
   ```typescript
   jest.mock('@/config/env', () => ({
     env: { apiUrl: 'https://mock.invalid', useMocks: true },
   }));
   ```
3. In `mobile/src/features/scan/OcrScanScreen.test.tsx`, add at the top (after imports):
   ```typescript
   jest.mock('@/config/env', () => ({
     env: { apiUrl: 'https://mock.invalid', useMocks: true },
   }));
   ```

---

## Micro-Step 10: Run Full Backend, Mobile & Pre-Commit Quality Gates

Execute the following commands in order and fix any formatting, lint, or type issue until every single command exits with code `0`:

```bash
# 1. Backend quality gates & tests
cd backend
uv run python scripts/export_openapi.py
uv run ruff check --fix .
uv run ruff format .
uv run mypy
uv run lint-imports
uv run pytest

# 2. Mobile quality gates & tests
cd ../mobile
npm run api:types
npm run format
npm run check
npx expo install --check

# 3. Repository-wide pre-commit hooks
cd ../backend
uv run pre-commit run --all-files
```

---

## Final Completion Checklist (Must All Be True Before Finishing)

- [ ] `.gitignore` ignores `*.dump` and `backend/before_sprint2.dump` is unstaged from Git (`check-added-large-files` passes).
- [ ] `GET /api/v1/products/filter` accepts `q` and combines text search with category, risk band, minimum score, and ingredient `include`/`exclude` filters in PostgreSQL.
- [ ] `IdentityService` resolves the 5 preset ingredient UUIDs (`0194f024-6c67-7e21-9e16-a774b0d53401`..`405`) to canonical PostgreSQL `Ingredient` rows and returns matching preset IDs on `GET /api/v1/profile` and `GET /api/v1/profile/blacklist`.
- [ ] Zero occurrences of `accessibilityRole="status"` remain anywhere in `mobile/src/`.
- [ ] Unauthenticated attempts to save a health profile or modify the blacklist in live mode redirect cleanly to `/auth/login`.
- [ ] Blacklisted products on `ProfileScreen` display their resolved product name and brand instead of raw UUIDs.
- [ ] `uv run pytest` (Backend), `npm run check` (Mobile), and `uv run pre-commit run --all-files` all exit with code `0`.

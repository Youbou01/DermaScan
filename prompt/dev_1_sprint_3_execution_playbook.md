# DermaScan — Sprint 3 Developer 1 Atomic Execution Playbook

> **Target Agent:** `agy gemini 3.8 flash`
> **Scope:** Sprint 3 — Developer 1 (Reviews, Ratings & Catalog Discovery: **US-21, US-24, US-25, US-26, US-28, US-31, US-33**)
> **Mode:** Execute every step **in exact order**. Do not improvise architecture, do not skip verification checkpoints, and do not bypass any linter, type checker, or test.

---

## 0. Hard Project Rules (NEVER Violate)

1. **Backend package manager:** Use `uv` exclusively (`uv sync`, `uv run ...`). NEVER run `pip install`.
2. **Modular monolith boundaries (`uv run lint-imports`):**
   - `app.modules.reviews` MUST NOT import from `app.modules.catalog.models`, `app.modules.catalog.repository`, `app.modules.identity.models`, or `app.modules.identity.repository`.
   - Cross-module calls MUST go through each module's public `__init__.py` (`CatalogService`, `IdentityService`, public DTOs).
   - `app.modules.catalog` MUST NOT import from `app.modules.reviews`.
   - Every new module with `models.py` / `repository.py` MUST have a `protected` contract in `backend/pyproject.toml` and be imported in `backend/migrations/env.py`.
3. **Database & Alembic conventions:**
   - Primary keys are `UUIDPrimaryKeyMixin` (UUIDv7).
   - Enums are stored as `VARCHAR(32)` using `enum_type(MyEnum)` paired with `enum_check("col", MyEnum)` in `__table_args__`. NEVER use native PostgreSQL enums.
   - All `relationship()` calls MUST use `lazy="raise"`. No cross-module `relationship()`.
   - NEVER edit an existing migration in `backend/migrations/versions/`. Create only one new additive migration whose `down_revision = "20261111_0013"`.
4. **Python typing & lint (`ruff` + `mypy --strict`):**
   - Every function and method in `backend/src/` and `backend/tests/` MUST have complete parameter and return type annotations (including `-> None`).
   - Always use timezone-aware UTC datetimes: `datetime.now(UTC)`. NEVER use `datetime.utcnow()`.
   - NEVER use `print()` in `backend/src/`; use `structlog.get_logger(__name__)`.
   - Raise subclasses of `AppError` (`app/core/errors.py`) in services; NEVER raise raw `HTTPException` in services.
5. **OpenAPI contract sync (`test_openapi.py`):**
   - After modifying any FastAPI router or response schema, you MUST run `uv run python scripts/export_openapi.py` in `backend/` AND `npm run api:generate` in `mobile/`.
6. **Mobile conventions (`npm run check`):**
   - App routes live in `mobile/app/`, reusable UI in `mobile/components/`, API client/hooks/types in `mobile/lib/api/`.
   - Use `heroui-native`, `lucide-react-native`, and `colors` from `@/lib/theme`.
   - NEVER use `.toSorted()` (`compat/no-to-sorted`).
   - Every React Native `<Image>` MUST have explicit `style={{ width, height }}` and `resizeMode`.
   - NEVER define React components inside another component's render body (`react/no-unstable-nested-components`).
   - Always run `npm run format` before `npm run check`.

---

## 1. Phase 0 — Environment Setup & Baseline Verification

Execute these commands from the repository root to verify your environment before editing any files.

### Step 0.1 — check feature branch
```bash
git status
```

### Step 0.2 — Set up backend environment & PostgreSQL
```bash
cd backend
uv sync
```
- Check if `backend/.env` exists. If it does **not** exist, copy `backend/.env.example` to `backend/.env` and replace both occurrences of `CHANGE_ME` with `devpassword`.
- Start PostgreSQL via Docker:
```bash
docker compose up -d db
```
- Wait until PostgreSQL is healthy, then verify baseline migrations and checks:
```bash
uv run alembic upgrade head
uv run alembic check
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run pytest tests/unit
```
All commands above MUST exit with code `0`.

### Step 0.3 — Verify mobile baseline
```bash
cd ../mobile
npm install
npm run check
```
`npm run check` MUST exit with code `0`. Return to the repository root before starting Phase 1.

---

## 2. Phase 1 — Database Models & Additive Alembic Migration (M14)

### Step 1.1 — Add `avg_rating` and `review_count` to `Product`
Edit `backend/src/app/modules/catalog/models.py`:

1. In `Product.__table_args__`, add these two `CheckConstraint`s and one `Index` right after the existing `coverage_range` constraint and `ix_product_score_dirty_partial` index:
   ```python
   CheckConstraint(
       "avg_rating IS NULL OR (avg_rating >= 1.0 AND avg_rating <= 5.0)",
       name="avg_rating_range",
   ),
   CheckConstraint("review_count >= 0", name="review_count_non_negative"),
   Index(
       "ix_product_avg_rating_id",
       "avg_rating",
       "id",
       postgresql_where=text("avg_rating IS NOT NULL"),
   ),
   ```
2. In `Product` class body (right after `score_dirty`), add these two mapped columns:
   ```python
   avg_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
   review_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
   ```
   *(Verify `Decimal`, `Integer`, `Numeric` are already imported at the top of `models.py` — they are.)*

### Step 1.2 — Create `backend/src/app/modules/reviews/enums.py`
Create directory `backend/src/app/modules/reviews/` and create `enums.py`:

```python
"""Enums owned by the reviews module."""

from enum import StrEnum


class ReviewSource(StrEnum):
    """Origin of a product review."""

    APP = "app"
    REDDIT = "reddit"


class ReviewCacheStatus(StrEnum):
    """Freshness state of cached external review fetches."""

    FRESH = "fresh"
    STALE = "stale"
    FAILED = "failed"
```

### Step 1.3 — Create `backend/src/app/modules/reviews/models.py`
Create `backend/src/app/modules/reviews/models.py`:

```python
"""Persistence models owned by the reviews module."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.orm import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_check, enum_type
from app.modules.reviews.enums import ReviewCacheStatus, ReviewSource


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review"
    __table_args__ = (
        enum_check("source", ReviewSource),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint(
            "source <> 'app' OR (user_id IS NOT NULL AND rating IS NOT NULL)",
            name="app_review_requires_user_and_rating",
        ),
        Index(
            "uq_review_app_user_product",
            "product_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL AND source = 'app'"),
        ),
        Index(
            "uq_review_external_source_id",
            "product_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "ix_review_product_created_at_id",
            "product_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_review_user_created_at_id",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[ReviewSource] = mapped_column(
        enum_type(ReviewSource),
        default=ReviewSource.APP,
        server_default=ReviewSource.APP.value,
    )
    author_name: Mapped[str] = mapped_column(String(120))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    body: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(128))
    external_url: Mapped[str | None] = mapped_column(Text)


class ReviewSourceCache(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "review_source_cache"
    __table_args__ = (
        enum_check("source", ReviewSource),
        enum_check("status", ReviewCacheStatus),
        UniqueConstraint("product_id", "source", name="uq_review_source_cache_product_source"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[ReviewSource] = mapped_column(enum_type(ReviewSource))
    status: Mapped[ReviewCacheStatus] = mapped_column(
        enum_type(ReviewCacheStatus),
        default=ReviewCacheStatus.FRESH,
        server_default=ReviewCacheStatus.FRESH.value,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
```

### Step 1.4 — Register `reviews` models in Alembic & Import-Linter
1. Edit `backend/migrations/env.py`:
   - Add `import app.modules.reviews.models` alongside the other module model imports.
   - Add `app.modules.reviews.models` to `_REGISTERED_MODELS`.
2. Edit `backend/pyproject.toml`:
   - Append this contract at the end of `[tool.importlinter]` contracts:
     ```toml
     [[tool.importlinter.contracts]]
     name = "reviews internals are private"
     type = "protected"
     protected_modules = ["app.modules.reviews.models", "app.modules.reviews.repository"]
     allowed_importers = ["app.modules.reviews"]
     ```

### Step 1.5 — Create Alembic Migration M14
Create `backend/migrations/versions/20261124_0014_m14_reviews_and_product_ratings.py`:

```python
"""M14: product reviews, external review source cache, and product rating aggregates.

Revision ID: 20261124_0014
Revises: 20261111_0013
Create Date: 2026-11-24 00:14:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261124_0014"
down_revision: str | Sequence[str] | None = "20261111_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product", sa.Column("avg_rating", sa.Numeric(precision=3, scale=2), nullable=True)
    )
    op.add_column(
        "product", sa.Column("review_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_check_constraint(
        "avg_rating_range",
        "product",
        "avg_rating IS NULL OR (avg_rating >= 1.0 AND avg_rating <= 5.0)",
    )
    op.create_check_constraint(
        "review_count_non_negative",
        "product",
        "review_count >= 0",
    )
    op.create_index(
        "ix_product_avg_rating_id",
        "product",
        ["avg_rating", "id"],
        unique=False,
        postgresql_where=sa.text("avg_rating IS NOT NULL"),
    )

    op.create_table(
        "review",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("app", "reddit", name="reviewsource", native_enum=False, length=32),
            server_default="app",
            nullable=False,
        ),
        sa.Column("author_name", sa.String(length=120), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("source IN ('app', 'reddit')", name=op.f("ck_review_source")),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5", name=op.f("ck_review_rating_range")
        ),
        sa.CheckConstraint(
            "source <> 'app' OR (user_id IS NOT NULL AND rating IS NOT NULL)",
            name=op.f("ck_review_app_review_requires_user_and_rating"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_review_product_id_product"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_review_user_id_user_account"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review")),
    )
    op.create_index(op.f("ix_review_product_id"), "review", ["product_id"], unique=False)
    op.create_index(op.f("ix_review_user_id"), "review", ["user_id"], unique=False)
    op.create_index(
        "uq_review_app_user_product",
        "review",
        ["product_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL AND source = 'app'"),
    )
    op.create_index(
        "uq_review_external_source_id",
        "review",
        ["product_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index(
        "ix_review_product_created_at_id",
        "review",
        ["product_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_review_user_created_at_id",
        "review",
        ["user_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "review_source_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("app", "reddit", name="reviewsource", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "fresh", "stale", "failed", name="reviewcachestatus", native_enum=False, length=32
            ),
            server_default="fresh",
            nullable=False,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('app', 'reddit')", name=op.f("ck_review_source_cache_source")
        ),
        sa.CheckConstraint(
            "status IN ('fresh', 'stale', 'failed')", name=op.f("ck_review_source_cache_status")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_review_source_cache_product_id_product"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_source_cache")),
        sa.UniqueConstraint(
            "product_id", "source", name="uq_review_source_cache_product_source"
        ),
    )
    op.create_index(
        op.f("ix_review_source_cache_product_id"),
        "review_source_cache",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_source_cache_product_id"), table_name="review_source_cache")
    op.drop_table("review_source_cache")

    op.drop_index(
        "ix_review_user_created_at_id",
        table_name="review",
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.drop_index("ix_review_product_created_at_id", table_name="review")
    op.drop_index(
        "uq_review_external_source_id",
        table_name="review",
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_review_app_user_product",
        table_name="review",
        postgresql_where=sa.text("user_id IS NOT NULL AND source = 'app'"),
    )
    op.drop_index(op.f("ix_review_user_id"), table_name="review")
    op.drop_index(op.f("ix_review_product_id"), table_name="review")
    op.drop_table("review")

    op.drop_index(
        "ix_product_avg_rating_id",
        table_name="product",
        postgresql_where=sa.text("avg_rating IS NOT NULL"),
    )
    op.drop_constraint("ck_product_review_count_non_negative", "product", type_="check")
    op.drop_constraint("ck_product_avg_rating_range", "product", type_="check")
    op.drop_column("product", "review_count")
    op.drop_column("product", "avg_rating")
```

### Step 1.6 — Checkpoint: Verify Migration Sync & Rollback
Create a temporary empty `backend/src/app/modules/reviews/__init__.py` (so Python recognizes the package), then run:
```bash
cd backend
uv run alembic upgrade head
uv run alembic check
uv run alembic downgrade -1
uv run alembic upgrade head
```
- `uv run alembic check` MUST print `No new upgrade operations detected.` and exit `0`.
- If `alembic check` reports any diff (e.g., index column expressions), adjust the migration or model until `alembic check` exits `0`.

---

## 3. Phase 2 — Public Service Extensions (`identity`, `catalog`, `caching`)

### Step 2.1 — Expose `get_user_display_name` on `IdentityService`
1. Edit `backend/src/app/modules/identity/service.py`:
   Add this public method to `IdentityService`:
   ```python
   async def get_user_display_name(self, user_id: uuid.UUID) -> str:
       """Return the public display name for a user account."""
       user = await self._repository.get_user_by_id(user_id)
       if user is None:
           raise UnauthorizedError("Account no longer exists.")
       return user.display_name
   ```
2. Edit `backend/src/app/modules/identity/__init__.py`:
   Export `IdentityService`:
   ```python
   from app.modules.identity.service import IdentityService as IdentityService
   ```
   and add `"IdentityService"` to `__all__`.

### Step 2.2 — Exclude `/reviews` from 300s HTTP public cache
Edit `backend/src/app/core/caching.py`:
In `HttpCacheMiddleware._get_cache_policy`, change:
```python
if path.startswith("/api/v1/products") and not path.endswith("/suitability"):
    return 300, 60
```
to:
```python
if (
    path.startswith("/api/v1/products")
    and not path.endswith("/suitability")
    and not path.endswith("/reviews")
):
    return 300, 60
```

### Step 2.3 — Expose `avg_rating` and `review_count` in Catalog DTOs & Service
1. Edit `backend/src/app/modules/catalog/schemas.py`:
   - In `ProductDetail`, add:
     ```python
     avg_rating: float | None = Field(
         default=None, description="Average community rating (1.0-5.0), or null when unrated."
     )
     review_count: int = Field(default=0, description="Total number of community reviews.")
     ```
   - In `ProductCardOut`, add:
     ```python
     avg_rating: float | None = Field(
         default=None, description="Average community rating (1.0-5.0), or null when unrated."
     )
     review_count: int = Field(default=0, description="Total number of community reviews.")
     ```
2. Edit `backend/src/app/modules/catalog/search_schemas.py`:
   - In `ProductSummary`, add:
     ```python
     avg_rating: float | None = Field(
         default=None, description="Average community rating (1.0-5.0), or null when unrated."
     )
     review_count: int = Field(default=0, description="Total number of community reviews.")
     ```
3. Edit `backend/src/app/modules/catalog/home_repository.py`:
   - Add `avg_rating: float | None = None` and `review_count: int = 0` to `ProductCardRow`.
   - In both `list_top_rated` and `list_recently_added`, pass:
     ```python
     avg_rating=float(product.avg_rating) if product.avg_rating is not None else None,
     review_count=product.review_count,
     ```
4. Edit `backend/src/app/modules/catalog/home_service.py`:
   - In `_card(row, locale)`, pass `avg_rating=row.avg_rating, review_count=row.review_count`.
5. Edit `backend/src/app/modules/catalog/service.py`:
   - In `_to_detail`, pass:
     ```python
     avg_rating=float(product.avg_rating) if product.avg_rating is not None else None,
     review_count=product.review_count,
     ```
   - In `_routine_product_card`, pass:
     ```python
     avg_rating=float(product.avg_rating) if product.avg_rating is not None else None,
     review_count=product.review_count,
     ```
   - Add two public methods to `CatalogService` for `reviews` to consume via the public boundary:
     ```python
     async def update_product_rating_stats(
         self,
         product_id: uuid.UUID,
         avg_rating: Decimal | None,
         review_count: int,
     ) -> None:
         """Update denormalized rating aggregates transactionally (caller commits)."""
         await self._session.execute(
             update(Product)
             .where(Product.id == product_id)
             .values(avg_rating=avg_rating, review_count=review_count)
         )
         await self._session.flush()

     async def get_product_cards_by_ids(
         self, product_ids: Collection[uuid.UUID], locale: str
     ) -> dict[uuid.UUID, ProductCardOut]:
         """Return lightweight product cards for a set of product IDs."""
         products = await self._products.get_by_ids(product_ids)
         return {product.id: _routine_product_card(product, locale) for product in products}
     ```
   - In `backend/src/app/modules/catalog/search_service.py`, update `_summary(product, locale)` to pass:
     ```python
     avg_rating=float(product.avg_rating) if product.avg_rating is not None else None,
     review_count=product.review_count,
     ```

### Step 2.4 — Implement `sort=score|rating` & `direction=desc|asc` with NULL-Last Cursor Pagination (US-31)
1. Edit `backend/src/app/modules/catalog/search_service.py`:
   - Import `Decimal` from `decimal`, `Literal` from `typing`, `and_`, `case`, `literal`, `or_`, `tuple_` from `sqlalchemy`, and `decode_cursor as decode_raw_cursor`, `encode_cursor as encode_raw_cursor` from `app.core.pagination`.
   - Define type aliases:
     ```python
     SortField = Literal["score", "rating"]
     SortDirection = Literal["desc", "asc"]
     ```
   - Add a dedicated NULL-last keyset helper function `_paginate_by_rating`:
     ```python
     async def _paginate_by_rating(
         session: AsyncSession,
         stmt: Select[Product],
         *,
         direction: SortDirection,
         limit: int,
         cursor: str | None,
     ) -> tuple[list[Product], str | None]:
         """Keyset paginate by Product.avg_rating with NULLS ALWAYS LAST in both directions."""
         sort_tag = f"rating:{direction}"
         descending = direction == "desc"

         if cursor is not None:
             try:
                 data = decode_raw_cursor(cursor)
                 if data.get("s") != sort_tag:
                     raise ValueError("mismatched sort cursor")
                 is_null = int(data["n"])
                 row_id = uuid.UUID(str(data["id"]))
                 if is_null not in (0, 1):
                     raise ValueError("invalid null bucket")
                 rating_val = Decimal(str(data["v"])) if is_null == 0 else None
             except (ValueError, KeyError, TypeError) as exc:
                 raise InvalidCursorError from exc

             if is_null == 0:
                 assert rating_val is not None
                 rated_row = tuple_(Product.avg_rating, Product.id)
                 rated_bound = tuple_(
                     literal(rating_val, Product.avg_rating.type),
                     literal(row_id, Product.id.type),
                 )
                 rated_cmp = rated_row < rated_bound if descending else rated_row > rated_bound
                 stmt = stmt.where(
                     or_(
                         and_(Product.avg_rating.is_not(None), rated_cmp),
                         Product.avg_rating.is_(None),
                     )
                 )
             else:
                 id_cmp = (
                     Product.id < literal(row_id, Product.id.type)
                     if descending
                     else Product.id > literal(row_id, Product.id.type)
                 )
                 stmt = stmt.where(and_(Product.avg_rating.is_(None), id_cmp))

         null_rank = case((Product.avg_rating.is_(None), 1), else_=0)
         if descending:
             stmt = stmt.order_by(
                 null_rank.asc(),
                 Product.avg_rating.desc().nulls_last(),
                 Product.id.desc(),
             )
         else:
             stmt = stmt.order_by(
                 null_rank.asc(),
                 Product.avg_rating.asc().nulls_last(),
                 Product.id.asc(),
             )

         rows = list((await session.scalars(stmt.limit(limit + 1))).all())
         next_cursor: str | None = None
         if len(rows) > limit:
             rows = rows[:limit]
             last = rows[-1]
             if last.avg_rating is None:
                 next_cursor = encode_raw_cursor({"s": sort_tag, "n": 1, "id": str(last.id)})
             else:
                 next_cursor = encode_raw_cursor(
                     {"s": sort_tag, "n": 0, "v": str(last.avg_rating), "id": str(last.id)}
                 )
         return rows, next_cursor
     ```
     *(Note: Do NOT use `assert rating_val is not None` in `src/` because Ruff `S101` forbids `assert` in `src/`. Use `if is_null == 0 and rating_val is not None:` instead!)*
   - Update `ProductSearchService.filter_products` signature to add:
     ```python
     sort: SortField = "score",
     direction: SortDirection = "desc",
     ```
   - At the end of `filter_products`:
     ```python
     if sort == "rating":
         items, next_cursor = await _paginate_by_rating(
             self._session,
             stmt,
             direction=direction,
             limit=limit,
             cursor=cursor,
         )
     else:
         items, next_cursor = await paginate(
             self._session,
             stmt,
             sort=f"score:{direction}",
             sort_column=Product.score,
             id_column=Product.id,
             key=lambda p: (p.score, p.id),
             parse_value=int,
             limit=limit,
             cursor=cursor,
             descending=(direction == "desc"),
         )
     return Page[ProductSummary](
         items=[_summary(p, locale) for p in items], next_cursor=next_cursor
     )
     ```
2. Edit `backend/src/app/modules/catalog/search_router.py`:
   - Add `Literal` to typing imports.
   - Update `filter_products` endpoint parameters to add:
     ```python
     sort: Annotated[
         Literal["score", "rating"],
         Query(description="Sort criterion: 'score' (default) or 'rating'."),
     ] = "score",
     direction: Annotated[
         Literal["desc", "asc"],
         Query(description="Sort direction: 'desc' (default) or 'asc'."),
     ] = "desc",
     ```
   - Forward `sort=sort, direction=direction` to `service.filter_products(...)`.

---

## 4. Phase 3 — New `reviews` Module

Create all files inside `backend/src/app/modules/reviews/`.

### Step 3.1 — Create `backend/src/app/modules/reviews/exceptions.py`
```python
"""Domain errors for the reviews module."""

from app.core.errors import ConflictError


class DuplicateReviewError(ConflictError):
    code = "duplicate-review"
    title = "You have already reviewed this product"
```

### Step 3.2 — Create `backend/src/app/modules/reviews/schemas.py`
```python
"""Public DTOs and request/response schemas for the reviews module."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.reviews.enums import ReviewSource

ExternalReviewStatus = Literal["fresh", "stale", "unavailable", "refreshing"]


class CreateReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=1, le=5, description="Star rating from 1 to 5.")
    body: str = Field(min_length=1, max_length=2000, description="Review comment text.")

    @field_validator("body", mode="before")
    @classmethod
    def _strip_body(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ReviewOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    product_id: uuid.UUID
    source: ReviewSource
    author_name: str
    rating: int | None
    body: str
    external_url: str | None = None
    created_at: datetime


class ProductReviewsPageOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: uuid.UUID
    avg_rating: float | None = Field(
        description="Average rating (1.0-5.0), or null when no rated reviews exist."
    )
    review_count: int = Field(description="Total number of reviews for this product.")
    external_source_status: ExternalReviewStatus = Field(
        description="Status of external Reddit reviews cache."
    )
    items: list[ReviewOut]
    next_cursor: str | None = Field(
        description="Opaque cursor for next page, or null on the last page."
    )


class UserReviewHistoryItemOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_brand: str | None
    product_image_url: str | None
    rating: int | None
    body: str
    source: ReviewSource
    created_at: datetime


class UserReviewsPageOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[UserReviewHistoryItemOut]
    next_cursor: str | None = Field(
        description="Opaque cursor for next page, or null on the last page."
    )
```

### Step 3.3 — Create `backend/src/app/modules/reviews/repository.py`
```python
"""SQL persistence for reviews and external source caches. Private to the reviews module."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.keyset import paginate
from app.modules.reviews.enums import ReviewCacheStatus, ReviewSource
from app.modules.reviews.models import Review, ReviewSourceCache


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_app_review(
        self,
        *,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        author_name: str,
        rating: int,
        body: str,
    ) -> Review:
        review = Review(
            product_id=product_id,
            user_id=user_id,
            source=ReviewSource.APP,
            author_name=author_name,
            rating=rating,
            body=body,
        )
        self._session.add(review)
        await self._session.flush()
        return review

    async def upsert_external_reviews(
        self,
        *,
        product_id: uuid.UUID,
        source: ReviewSource,
        items: list[dict[str, Any]],
    ) -> int:
        """Idempotently insert external reviews keyed by (product_id, source, external_id)."""
        if not items:
            return 0
        inserted = 0
        for item in items:
            ext_id = str(item["external_id"]).strip()
            if not ext_id:
                continue
            stmt = (
                insert(Review)
                .values(
                    id=uuid.uuid7(),
                    product_id=product_id,
                    user_id=None,
                    source=source,
                    author_name=str(item.get("author_name") or "Reddit user")[:120],
                    rating=item.get("rating"),
                    body=str(item["body"]),
                    external_id=ext_id[:128],
                    external_url=item.get("external_url"),
                    created_at=item.get("created_at") or func.now(),
                    updated_at=func.now(),
                )
                .on_conflict_do_nothing(
                    index_elements=[Review.product_id, Review.source, Review.external_id],
                    index_where=Review.external_id.is_not(None),
                )
                .returning(Review.id)
            )
            res = await self._session.execute(stmt)
            if res.scalar_one_or_none() is not None:
                inserted += 1
        await self._session.flush()
        return inserted

    async def compute_product_stats(self, product_id: uuid.UUID) -> tuple[Decimal | None, int]:
        """Compute (avg_rating rounded to 2 decimals, total review_count) for a product."""
        stmt = select(
            func.round(func.avg(Review.rating), 2),
            func.count(Review.id),
        ).where(Review.product_id == product_id)
        row = (await self._session.execute(stmt)).one()
        avg_val = Decimal(str(row[0])) if row[0] is not None else None
        count_val = int(row[1] or 0)
        return avg_val, count_val

    async def list_for_product(
        self,
        product_id: uuid.UUID,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Review], str | None]:
        stmt = select(Review).where(Review.product_id == product_id)
        return await paginate(
            self._session,
            stmt,
            sort="review_created_at",
            sort_column=Review.created_at,
            id_column=Review.id,
            key=lambda r: (r.created_at, r.id),
            parse_value=datetime.fromisoformat,
            limit=limit,
            cursor=cursor,
            descending=True,
        )

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Review], str | None]:
        stmt = select(Review).where(Review.user_id == user_id)
        return await paginate(
            self._session,
            stmt,
            sort="user_review_created_at",
            sort_column=Review.created_at,
            id_column=Review.id,
            key=lambda r: (r.created_at, r.id),
            parse_value=datetime.fromisoformat,
            limit=limit,
            cursor=cursor,
            descending=True,
        )

    async def get_source_cache(
        self, product_id: uuid.UUID, source: ReviewSource
    ) -> ReviewSourceCache | None:
        stmt = select(ReviewSourceCache).where(
            ReviewSourceCache.product_id == product_id,
            ReviewSourceCache.source == source,
        )
        return await self._session.scalar(stmt)

    async def upsert_source_cache(
        self,
        *,
        product_id: uuid.UUID,
        source: ReviewSource,
        status: ReviewCacheStatus,
        fetched_at: datetime,
        expires_at: datetime,
        error_message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        stmt = (
            insert(ReviewSourceCache)
            .values(
                id=uuid.uuid7(),
                product_id=product_id,
                source=source,
                status=status,
                fetched_at=fetched_at,
                expires_at=expires_at,
                error_message=error_message,
                payload=payload or {},
            )
            .on_conflict_do_update(
                constraint="uq_review_source_cache_product_source",
                set_={
                    "status": status,
                    "fetched_at": fetched_at,
                    "expires_at": expires_at,
                    "error_message": error_message,
                    "payload": payload or {},
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
```

### Step 3.4 — Create `backend/src/app/modules/reviews/reddit_adapter.py`
```python
"""Asynchronous Reddit public search adapter for external product reviews."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus

import httpx
import structlog

logger = structlog.get_logger(__name__)

REDDIT_SEARCH_URL = (
    "https://www.reddit.com/r/SkincareAddiction/search.json"
    "?q={query}&restrict_sr=1&sort=relevance&limit={limit}"
)
REDDIT_USER_AGENT = "DermaScan/1.0 (academic skincare analysis platform)"


@dataclass(frozen=True, slots=True)
class ExternalReviewRecord:
    external_id: str
    author_name: str
    body: str
    external_url: str | None
    created_at: datetime
    rating: int | None = None


def normalize_reddit_posts(payload: dict[str, Any]) -> list[ExternalReviewRecord]:
    """Pure parser turning Reddit listing JSON into normalized review records."""
    children = payload.get("data", {}).get("children", [])
    if not isinstance(children, list):
        return []

    records: list[ExternalReviewRecord] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        post = child.get("data")
        if not isinstance(post, dict):
            continue
        post_id = str(post.get("id") or "").strip()
        title = str(post.get("title") or "").strip()
        selftext = str(post.get("selftext") or "").strip()
        text = f"{title}\n{selftext}".strip() if selftext else title
        if not post_id or len(text) < 10:
            continue
        author = str(post.get("author") or "reddit_user").strip()
        permalink = str(post.get("permalink") or "").strip()
        url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else None
        created_utc = post.get("created_utc")
        created_at = (
            datetime.fromtimestamp(float(created_utc), tz=UTC)
            if isinstance(created_utc, (int, float))
            else datetime.now(UTC)
        )
        records.append(
            ExternalReviewRecord(
                external_id=post_id[:128],
                author_name=f"u/{author}"[:120],
                body=text[:2000],
                external_url=url,
                created_at=created_at,
                rating=None,
            )
        )
    return records


class RedditReviewsAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 5.0) -> None:
        self._client = client
        self._timeout = timeout

    async def fetch_reviews(
        self, query: str, *, limit: int = 5
    ) -> tuple[list[ExternalReviewRecord], dict[str, Any]]:
        clean_query = query.strip()
        if not clean_query:
            return [], {}
        url = REDDIT_SEARCH_URL.format(query=quote_plus(clean_query), limit=limit)
        headers = {"User-Agent": REDDIT_USER_AGENT, "Accept": "application/json"}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            payload: dict[str, Any] = resp.json()
            return normalize_reddit_posts(payload), payload
        finally:
            if owns_client:
                await client.aclose()
```

### Step 3.5 — Create `backend/src/app/modules/reviews/service.py`
```python
"""Business logic for product reviews, rating aggregation, and async Reddit refresh."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import DEFAULT_LOCALE
from app.core.jobs import enqueue_job
from app.modules.catalog import CatalogService
from app.modules.identity import IdentityService
from app.modules.reviews.enums import ReviewCacheStatus, ReviewSource
from app.modules.reviews.exceptions import DuplicateReviewError
from app.modules.reviews.models import Review
from app.modules.reviews.reddit_adapter import RedditReviewsAdapter
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.schemas import (
    CreateReviewIn,
    ExternalReviewStatus,
    ProductReviewsPageOut,
    ReviewOut,
    UserReviewHistoryItemOut,
    UserReviewsPageOut,
)

logger = structlog.get_logger(__name__)

REDDIT_CACHE_TTL = timedelta(hours=24)
REDDIT_FAILURE_TTL = timedelta(hours=1)


def _to_review_out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        product_id=review.product_id,
        source=review.source,
        author_name=review.author_name,
        rating=review.rating,
        body=review.body,
        external_url=review.external_url,
        created_at=review.created_at,
    )


class ReviewService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        reddit_adapter: RedditReviewsAdapter | None = None,
    ) -> None:
        self._session = session
        self._repo = ReviewRepository(session)
        self._catalog = CatalogService(session)
        self._identity = IdentityService(session)
        self._reddit = reddit_adapter or RedditReviewsAdapter()

    async def list_product_reviews(
        self,
        product_id: uuid.UUID,
        *,
        limit: int,
        cursor: str | None,
        locale: str = DEFAULT_LOCALE,
        enqueue_refresh: bool = True,
    ) -> ProductReviewsPageOut:
        product = await self._catalog.get_product_detail(product_id, locale)
        reviews, next_cursor = await self._repo.list_for_product(
            product_id, limit=limit, cursor=cursor
        )

        now = datetime.now(UTC)
        cache = await self._repo.get_source_cache(product_id, ReviewSource.REDDIT)
        external_status: ExternalReviewStatus

        if cache is None:
            external_status = "refreshing"
            if enqueue_refresh:
                await enqueue_job(
                    self._session,
                    task_name="refresh_reddit_reviews",
                    payload={"product_id": str(product_id)},
                    queue="default",
                )
                await self._session.commit()
        elif cache.status == ReviewCacheStatus.FAILED:
            external_status = "unavailable"
            if enqueue_refresh and cache.expires_at <= now:
                await enqueue_job(
                    self._session,
                    task_name="refresh_reddit_reviews",
                    payload={"product_id": str(product_id)},
                    queue="default",
                )
                await self._session.commit()
        elif cache.expires_at <= now or cache.status == ReviewCacheStatus.STALE:
            external_status = "stale"
            if enqueue_refresh:
                await enqueue_job(
                    self._session,
                    task_name="refresh_reddit_reviews",
                    payload={"product_id": str(product_id)},
                    queue="default",
                )
                await self._session.commit()
        else:
            external_status = "fresh"

        return ProductReviewsPageOut(
            product_id=product_id,
            avg_rating=product.avg_rating,
            review_count=product.review_count,
            external_source_status=external_status,
            items=[_to_review_out(r) for r in reviews],
            next_cursor=next_cursor,
        )

    async def create_review(
        self,
        *,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateReviewIn,
    ) -> ReviewOut:
        # Verify product exists and resolve user display name through public services.
        await self._catalog.get_product_detail(product_id, DEFAULT_LOCALE)
        author_name = await self._identity.get_user_display_name(user_id)

        try:
            review = await self._repo.add_app_review(
                product_id=product_id,
                user_id=user_id,
                author_name=author_name,
                rating=payload.rating,
                body=payload.body,
            )
        except IntegrityError:
            await self._session.rollback()
            raise DuplicateReviewError("You have already reviewed this product.") from None

        avg_rating, review_count = await self._repo.compute_product_stats(product_id)
        await self._catalog.update_product_rating_stats(product_id, avg_rating, review_count)
        await self._session.commit()
        return _to_review_out(review)

    async def list_user_reviews(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        cursor: str | None,
        locale: str = DEFAULT_LOCALE,
    ) -> UserReviewsPageOut:
        reviews, next_cursor = await self._repo.list_for_user(user_id, limit=limit, cursor=cursor)
        product_ids = list(dict.fromkeys(r.product_id for r in reviews))
        cards = await self._catalog.get_product_cards_by_ids(product_ids, locale)

        items: list[UserReviewHistoryItemOut] = []
        for review in reviews:
            card = cards.get(review.product_id)
            items.append(
                UserReviewHistoryItemOut(
                    id=review.id,
                    product_id=review.product_id,
                    product_name=card.name if card else "Unknown product",
                    product_brand=card.brand if card else None,
                    product_image_url=card.image_url if card else None,
                    rating=review.rating,
                    body=review.body,
                    source=review.source,
                    created_at=review.created_at,
                )
            )
        return UserReviewsPageOut(items=items, next_cursor=next_cursor)

    async def refresh_reddit_reviews(self, product_id: uuid.UUID) -> int:
        """Fetch and cache Reddit reviews for one product (called from background worker)."""
        product = await self._catalog.get_product_detail(product_id, DEFAULT_LOCALE)
        query = f"{product.brand} {product.name}".strip() if product.brand else product.name
        now = datetime.now(UTC)

        try:
            records, raw_payload = await self._reddit.fetch_reviews(query, limit=5)
        except Exception as exc:
            logger.warning(
                "reddit_reviews_fetch_failed", product_id=str(product_id), error=str(exc)
            )
            await self._repo.upsert_source_cache(
                product_id=product_id,
                source=ReviewSource.REDDIT,
                status=ReviewCacheStatus.FAILED,
                fetched_at=now,
                expires_at=now + REDDIT_FAILURE_TTL,
                error_message=str(exc)[:500],
                payload={},
            )
            await self._session.flush()
            return 0

        items_payload: list[dict[str, Any]] = [
            {
                "external_id": rec.external_id,
                "author_name": rec.author_name,
                "rating": rec.rating,
                "body": rec.body,
                "external_url": rec.external_url,
                "created_at": rec.created_at,
            }
            for rec in records
        ]
        inserted = await self._repo.upsert_external_reviews(
            product_id=product_id,
            source=ReviewSource.REDDIT,
            items=items_payload,
        )
        await self._repo.upsert_source_cache(
            product_id=product_id,
            source=ReviewSource.REDDIT,
            status=ReviewCacheStatus.FRESH,
            fetched_at=now,
            expires_at=now + REDDIT_CACHE_TTL,
            error_message=None,
            payload={"count": len(records), "raw_children_count": len(raw_payload.get("data", {}).get("children", []))},
        )
        avg_rating, review_count = await self._repo.compute_product_stats(product_id)
        await self._catalog.update_product_rating_stats(product_id, avg_rating, review_count)
        await self._session.flush()
        return inserted
```

### Step 3.6 — Create `backend/src/app/modules/reviews/tasks.py`
```python
"""Background tasks owned by the reviews module."""

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.jobs import register_task
from app.modules.reviews.service import ReviewService

logger = structlog.get_logger(__name__)


@register_task("refresh_reddit_reviews")
async def refresh_reddit_reviews_task(payload: dict[str, Any], session: AsyncSession) -> None:
    raw_id = payload.get("product_id")
    if not raw_id:
        logger.warning("refresh_reddit_reviews_missing_product_id")
        return
    if get_settings().app_env == "test":
        logger.debug("refresh_reddit_reviews_skipped_in_test", product_id=str(raw_id))
        return
    product_id = uuid.UUID(str(raw_id))
    service = ReviewService(session)
    inserted = await service.refresh_reddit_reviews(product_id)
    logger.info("refresh_reddit_reviews_finished", product_id=str(product_id), inserted=inserted)
```

### Step 3.7 — Create `backend/src/app/modules/reviews/router.py`
```python
"""HTTP endpoints for product reviews and personal review history."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.keyset import DEFAULT_LIMIT, CursorQuery, LimitQuery
from app.core.security import CurrentUserIdDep
from app.modules.reviews.schemas import (
    CreateReviewIn,
    ProductReviewsPageOut,
    ReviewOut,
    UserReviewsPageOut,
)
from app.modules.reviews.service import ReviewService

product_reviews_router = APIRouter()
user_reviews_router = APIRouter()

_LIST_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetails, "description": "Product not found."},
    422: {"model": ProblemDetails, "description": "Invalid identifier or cursor."},
}
_CREATE_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Authentication required."},
    404: {"model": ProblemDetails, "description": "Product not found."},
    409: {"model": ProblemDetails, "description": "Duplicate review for this product."},
    422: {"model": ProblemDetails, "description": "Invalid rating or review body."},
}
_USER_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Authentication required."},
    422: {"model": ProblemDetails, "description": "Invalid cursor."},
}


def get_review_service(session: SessionDep) -> ReviewService:
    return ReviewService(session)


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]


@product_reviews_router.get(
    "/{product_id}/reviews",
    response_model=ProductReviewsPageOut,
    responses=_LIST_ERRORS,
    summary="List product reviews from app and external sources",
)
async def list_product_reviews(
    product_id: uuid.UUID,
    service: ReviewServiceDep,
    locale: LocaleDep,
    limit: LimitQuery = DEFAULT_LIMIT,
    cursor: CursorQuery = None,
) -> ProductReviewsPageOut:
    return await service.list_product_reviews(
        product_id, limit=limit, cursor=cursor, locale=locale
    )


@product_reviews_router.post(
    "/{product_id}/reviews",
    status_code=status.HTTP_201_CREATED,
    response_model=ReviewOut,
    responses=_CREATE_ERRORS,
    summary="Post a product review",
)
async def create_product_review(
    product_id: uuid.UUID,
    payload: CreateReviewIn,
    user_id: CurrentUserIdDep,
    service: ReviewServiceDep,
) -> ReviewOut:
    return await service.create_review(product_id=product_id, user_id=user_id, payload=payload)


@user_reviews_router.get(
    "/reviews",
    response_model=UserReviewsPageOut,
    responses=_USER_ERRORS,
    summary="List the signed-in user's reviewed products history",
)
async def list_my_reviews(
    user_id: CurrentUserIdDep,
    service: ReviewServiceDep,
    locale: LocaleDep,
    limit: LimitQuery = DEFAULT_LIMIT,
    cursor: CursorQuery = None,
) -> UserReviewsPageOut:
    return await service.list_user_reviews(user_id, limit=limit, cursor=cursor, locale=locale)
```

### Step 3.8 — Create `backend/src/app/modules/reviews/__init__.py`
```python
"""Reviews module public interface."""

from app.modules.reviews.enums import ReviewCacheStatus, ReviewSource
from app.modules.reviews.exceptions import DuplicateReviewError
from app.modules.reviews.router import product_reviews_router, user_reviews_router
from app.modules.reviews.schemas import (
    CreateReviewIn,
    ProductReviewsPageOut,
    ReviewOut,
    UserReviewHistoryItemOut,
    UserReviewsPageOut,
)
from app.modules.reviews.service import ReviewService

__all__ = [
    "CreateReviewIn",
    "DuplicateReviewError",
    "ProductReviewsPageOut",
    "ReviewCacheStatus",
    "ReviewOut",
    "ReviewService",
    "ReviewSource",
    "UserReviewHistoryItemOut",
    "UserReviewsPageOut",
    "product_reviews_router",
    "user_reviews_router",
]
```

### Step 3.9 — Mount Routers & Register Worker Task
1. Edit `backend/src/app/api/v1/router.py`:
   - Import `product_reviews_router, user_reviews_router` from `app.modules.reviews`.
   - Mount them:
     ```python
     router.include_router(product_reviews_router, prefix="/products", tags=["reviews"])
     router.include_router(user_reviews_router, prefix="/users/me", tags=["reviews"])
     ```
2. Edit `backend/src/app/worker.py`:
   - Add `import app.modules.reviews.tasks  # noqa: F401` next to the other task handler imports.

---

## 5. Phase 4 — Backend Tests & Quality Gate

### Step 4.1 — Update Existing Strict Contract Assertions
1. Edit `backend/tests/integration/test_products_api.py`:
   - Add `"avg_rating"` and `"review_count"` to `PRODUCT_KEYS`.
2. Edit `backend/tests/integration/test_home_api.py`:
   - In `test_product_card_shape`, add `"avg_rating"` and `"review_count"` to the expected `set(card)` dictionary keys.

### Step 4.2 — Add Unit Tests (`backend/tests/unit/test_reviews_unit.py`)
Create `backend/tests/unit/test_reviews_unit.py` testing:
1. `CreateReviewIn` accepts ratings `1..5` and strips whitespace on `body`.
2. `CreateReviewIn` rejects rating `0`, rating `6`, and whitespace-only `body` with `ValidationError`.
3. `normalize_reddit_posts()` parses valid Reddit JSON into `ExternalReviewRecord` items with `u/<author>`, non-empty `body`, `external_url`, and skips malformed/short entries.

### Step 4.3 — Add Reviews Integration Tests (`backend/tests/integration/test_reviews_api.py`)
Create `backend/tests/integration/test_reviews_api.py` covering ALL Dev 1 review acceptance criteria:
1. `GET /api/v1/products/{id}/reviews` on a product with 0 reviews returns `avg_rating=None`, `review_count=0`, `items=[]`, `external_source_status="refreshing"`, and enqueues `refresh_reddit_reviews` job.
2. `POST /api/v1/products/{id}/reviews` without auth returns `401`.
3. `POST /api/v1/products/{id}/reviews` with invalid rating (`0` or `6`) or empty body returns `422`.
4. `POST /api/v1/products/{id}/reviews` on unknown product returns `404`.
5. `POST /api/v1/products/{id}/reviews` creates a review (`201`), sets `source="app"`, updates `Product.avg_rating` and `Product.review_count` immediately in `GET /api/v1/products/{id}`, and recalculates average when a second user posts a review (e.g., 5 and 4 -> `4.5`, count `2`).
6. Duplicate `POST /api/v1/products/{id}/reviews` by the same user on the same product returns `409` with `type="urn:skincare:problem:duplicate-review"`.
7. Mixed sources (app + Reddit): calling `ReviewService.refresh_reddit_reviews(product_id)` with a mocked `RedditReviewsAdapter` persists Reddit reviews idempotently (running twice creates no duplicates), sets `external_source_status="fresh"`, and `GET /api/v1/products/{id}/reviews` returns both `app` and `reddit` reviews with explicit `source` labels.
8. Reddit API failure: when `RedditReviewsAdapter.fetch_reviews` raises `httpx.HTTPError`, `ReviewService.refresh_reddit_reviews` marks cache `failed`, and `GET /api/v1/products/{id}/reviews` still returns `200` with existing app reviews and `external_source_status="unavailable"`.
9. `GET /api/v1/users/me/reviews` requires auth (`401` when logged out), returns only the authenticated user's reviews ordered most recent first with `product_name`, `product_brand`, `rating`, `body`, `created_at`, and supports keyset pagination without overlap.

### Step 4.4 — Add Rating Sort & Filter Regression Tests (`backend/tests/integration/test_product_sort_rating.py`)
Create `backend/tests/integration/test_product_sort_rating.py` covering US-31 & US-33:
1. Default `GET /api/v1/products/filter` (no `sort` param) still sorts by `score DESC`.
2. `sort=score&direction=asc` sorts lowest score first.
3. `sort=rating&direction=desc` orders rated products from highest `avg_rating` to lowest, and places products with `avg_rating IS NULL` **at the end**.
4. `sort=rating&direction=asc` orders rated products from lowest `avg_rating` to highest, and STILL places products with `avg_rating IS NULL` **at the end**.
5. Keyset cursor pagination with `limit=2` across a dataset of 3 rated + 2 unrated products (5 total) walks through all 3 pages in BOTH `desc` and `asc` directions with zero duplicates, zero missing rows, and exact rated-before-unrated ordering across the boundary.
6. Passing a `sort=score:desc` cursor to `sort=rating&direction=desc` returns `422` (`invalid-cursor`).
7. Combining `q`, `category`, `band`, `min_score`, `max_score`, `include`, `exclude` with `sort=rating&direction=desc` works together in one query.

### Step 4.5 — Export OpenAPI & Run Full Backend Gate
```bash
cd backend
uv run python scripts/export_openapi.py
uv run ruff check --fix .
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run alembic check
uv run pytest
```
ALL commands MUST pass with `0` errors and `0` failures before proceeding to Phase 5!

---

## 6. Phase 5 — Mobile Client Implementation

### Step 5.1 — Regenerate Mobile OpenAPI Types
```bash
cd mobile
npm run api:generate
```
Verify `mobile/openapi.json` and `mobile/lib/api/generated/schema.d.ts` now include `/api/v1/products/{product_id}/reviews`, `/api/v1/users/me/reviews`, and the `sort`/`direction` query parameters on `/api/v1/products/filter`.

### Step 5.2 — Update `mobile/lib/api/types.ts`
1. Add optional `avg_rating?: number | null;` and `review_count?: number;` to `Product`.
2. Update `Filters` to include:
   ```ts
   sort?: 'score' | 'rating';
   direction?: 'desc' | 'asc';
   ```
3. Append these types to `mobile/lib/api/types.ts`:
   ```ts
   export type ReviewSource = 'app' | 'reddit';
   export type ExternalReviewStatus = 'fresh' | 'stale' | 'unavailable' | 'refreshing';
   export type Review = {
     id: string;
     product_id: string;
     source: ReviewSource;
     author_name: string;
     rating: number | null;
     body: string;
     external_url: string | null;
     created_at: string;
   };
   export type ProductReviewsPage = {
     product_id: string;
     avg_rating: number | null;
     review_count: number;
     external_source_status: ExternalReviewStatus;
     items: Review[];
     next_cursor: string | null;
   };
   export type CreateReviewInput = {
     rating: number;
     body: string;
   };
   export type UserReviewHistoryItem = {
     id: string;
     product_id: string;
     product_name: string;
     product_brand: string | null;
     product_image_url: string | null;
     rating: number | null;
     body: string;
     source: ReviewSource;
     created_at: string;
   };
   export type UserReviewsPage = {
     items: UserReviewHistoryItem[];
     next_cursor: string | null;
   };
   ```

### Step 5.3 — Update `mobile/lib/api/queries.ts`
1. Import `ProductReviewsPage` and `UserReviewsPage` from `./types`.
2. In `useProducts(filters, enabled)`, include `filters.sort !== undefined || filters.direction !== undefined` inside `hasFilters` so any sort request calls `/products/filter` with `sort` and `direction`.
3. Add two hooks at the bottom of `mobile/lib/api/queries.ts`:
   ```ts
   export function useProductReviews(productId: string, enabled = true) {
     return useInfiniteQuery({
       queryKey: ['product-reviews', productId],
       enabled: !!productId && enabled,
       initialPageParam: null as string | null,
       queryFn: ({ pageParam, signal }) =>
         request<ProductReviewsPage>(
           `/products/${encodeURIComponent(productId)}/reviews` +
             queryString({ limit: 20, cursor: pageParam }),
           { signal },
         ),
       getNextPageParam: (page) => page.next_cursor ?? undefined,
     });
   }

   export function useMyReviews() {
     const uid = useUserId();
     return useInfiniteQuery({
       queryKey: privateKey('my-reviews', uid),
       enabled: !!uid,
       initialPageParam: null as string | null,
       queryFn: ({ pageParam, signal }) =>
         request<UserReviewsPage>(
           '/users/me/reviews' + queryString({ limit: 20, cursor: pageParam }),
           { auth: true, signal },
         ),
       getNextPageParam: (page) => page.next_cursor ?? undefined,
     });
   }
   ```

### Step 5.4 — Create Pure Review Validation Helper (`mobile/lib/reviews.ts`)
Create `mobile/lib/reviews.ts`:
```ts
export function validateReviewInput(rating: number, body: string): string | null {
  if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
    return 'Select a rating between 1 and 5 stars.';
  }
  const trimmed = body.trim();
  if (!trimmed) {
    return 'Write a short comment about your experience.';
  }
  if (trimmed.length > 2000) {
    return 'Review must be 2000 characters or fewer.';
  }
  return null;
}

export function formatReviewDate(isoDate: string): string {
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
```

### Step 5.5 — Create `mobile/components/RatingSummary.tsx` (US-21)
Create `mobile/components/RatingSummary.tsx`:
- Accepts `{ avgRating: number | null; reviewCount: number }`.
- When `reviewCount === 0 || avgRating === null`: renders `"No reviews yet"` in `colors.muted`.
- Otherwise: renders `avgRating.toFixed(1)` + `"/ 5"`, 5 `Star` icons from `lucide-react-native` (filled with `colors.amber` up to `Math.round(avgRating)`), and `(${reviewCount} ${reviewCount === 1 ? 'review' : 'reviews'})`.

### Step 5.6 — Create `mobile/components/ReviewCard.tsx` (US-24, US-25)
Create `mobile/components/ReviewCard.tsx`:
- Accepts `{ review: Review }`.
- Renders:
  - Header row: `review.author_name`, formatted date via `formatReviewDate(review.created_at)`, and a source badge on the right:
    - If `review.source === 'app'`: square badge with `"A"` and sub-label `"App"` (`colors.greenSoft` background, `colors.green` text).
    - If `review.source === 'reddit'`: rounded badge with `"R"` and sub-label `"Reddit"` (`colors.orangeSoft` background, `colors.orange` text).
  - Star row (if `review.rating !== null`): 5 `Star` icons filled up to `review.rating`.
  - Review text (`review.body`).

### Step 5.7 — Update `mobile/components/ProductCard.tsx`
- Inside the bottom badge row of `ProductCard`, next to `<ScoreBadge />`, if `product.avg_rating != null && (product.review_count ?? 0) > 0`, render a compact rating badge showing a small `Star` icon (`size={11}`) and `{product.avg_rating.toFixed(1)}`.

### Step 5.8 — Update Product Detail Screen (`mobile/app/product/[id].tsx`)
1. Import `RatingSummary` from `@/components/RatingSummary`, `ReviewCard` from `@/components/ReviewCard`, and `useProductReviews` from `@/lib/api/queries`.
2. Right below the product name/category/barcode block (above `<AnalysisScore />`), render:
   ```tsx
   <RatingSummary
     avgRating={product.data.avg_rating ?? null}
     reviewCount={product.data.review_count ?? 0}
   />
   ```
3. Add a third tab `"reviews"` in `<Tabs>`:
   - `<Tabs.Trigger value="reviews" className="flex-1"><Tabs.Label numberOfLines={1}>Reviews</Tabs.Label></Tabs.Trigger>`
   - Call `const reviews = useProductReviews(id, tab === 'reviews');`
   - Inside `<Tabs.Content value="reviews">`:
     - Show `<LoadingState />` when `reviews.isPending`, `<DataState />` on error.
     - Read `externalStatus = reviews.data?.pages[0]?.external_source_status`.
     - If `externalStatus === 'unavailable'`, display a subtle info banner: `"External Reddit reviews are temporarily unavailable. Showing app reviews only."`
     - Flatten `const reviewItems = reviews.data?.pages.flatMap((p) => p.items) ?? [];`.
     - If empty: show `<AppText style={{ color: colors.muted }}>No reviews yet.</AppText>`.
     - Else: map `reviewItems` to `<ReviewCard key={item.id} review={item} />`.
     - If `reviews.hasNextPage`, render a `"Load more reviews"` secondary `<Button />`.
     - Render a `"Post a review"` primary `<Button />`:
       - If signed in (`uid`), navigate to `router.push({ pathname: '/review/new', params: { productId: id, productName: product.data.name } })`.
       - If logged out, navigate to `router.push('/account')`.

### Step 5.9 — Create Post Review Screen (`mobile/app/review/new.tsx`) (US-26)
Create `mobile/app/review/new.tsx`:
- Reads `{ productId, productName }` via `useLocalSearchParams<{ productId?: string; productName?: string }>()`.
- If `!uid`, render `<SignInGate message="Sign in to post a review." />`.
- State: `rating` (`number`, default `0`), `body` (`string`, default `''`), `validationError` (`string`, default `''`).
- Interactive 1–5 star row: 5 `Button`s (`isIconOnly`, `variant="tertiary"`, `accessibilityLabel={`Rate ${n} out of 5 stars`}`), rendering `Star` filled with `colors.amber` when `n <= rating`.
- `<TextArea />` for review comment (`maxLength={2000}`, `placeholder="Write your review here..."`).
- Mutation: `POST /products/${productId}/reviews` with `{ rating, body: body.trim() }`.
  - Before calling `mutation.mutate()`, run `validateReviewInput(rating, body)`. If it returns an error string, set `validationError` and do NOT submit.
  - On `ApiError` with status `409`, display `"You have already reviewed this product."`.
  - On success:
    - `notifySuccess()`
    - Invalidate `['product', productId]`, `['product-reviews', productId]`, `privateKey('my-reviews', uid)`, and `['products']`.
    - Call `router.back()`.
- Bottom buttons:
  - `Cancel` (`variant="secondary"`, calls `router.back()` without saving).
  - `Submit review` (`isDisabled={mutation.isPending}`, calls submit handler).

### Step 5.10 — Create My Reviews History Screen (`mobile/app/my-reviews.tsx`) (US-28)
Create `mobile/app/my-reviews.tsx`:
- Uses `ScreenList` with `title="My reviews"` and `useMyReviews()`.
- If `!uid`, render `<SignInGate message="Sign in to view your reviewed products." />`.
- Each item renders a card with:
  - Product name (`item.product_name`), brand (`item.product_brand`), star rating (`item.rating`), review text (`item.body`), and `"Reviewed on " + formatReviewDate(item.created_at)`.
  - Tapping the card navigates to `router.push({ pathname: '/product/[id]', params: { id: item.product_id } })`.
- Empty state: `<DataState message="You have not reviewed any products yet." action="Explore products" onAction={() => router.push('/')} />`.
- Supports pull-to-refresh and `onEndReached` pagination.

### Step 5.11 — Register Routes & Add Account Navigation Link
1. Edit `mobile/app/_layout.tsx`:
   Add two `<Stack.Screen>` entries inside `<Stack>`:
   ```tsx
   <Stack.Screen name="review/new" options={{ title: 'Submit your review' }} />
   <Stack.Screen name="my-reviews" options={{ title: 'My reviews' }} />
   ```
2. Edit `mobile/app/account.tsx`:
   When `session` is present, add a secondary button next to `Your routines` / `Recommendations`:
   ```tsx
   <Button variant="secondary" onPress={() => router.push('/my-reviews')}>
     <Button.Label>My reviews</Button.Label>
   </Button>
   ```

### Step 5.12 — Add Sort Selector & Min/Max Score Filters on Home (`mobile/app/(tabs)/index.tsx`) (US-31, US-33)
Edit `mobile/app/(tabs)/index.tsx`:
1. Add state:
   ```ts
   const [sort, setSort] = useState<'score' | 'rating'>('score');
   const [direction, setDirection] = useState<'desc' | 'asc'>('desc');
   const [minScore, setMinScore] = useState<number | undefined>();
   const [maxScore, setMaxScore] = useState<number | undefined>();
   ```
2. Update `filtering` boolean so it is `true` when any filter OR non-default sort is active:
   ```ts
   const filtering = !!(
     debounced ||
     category ||
     band ||
     minScore !== undefined ||
     maxScore !== undefined ||
     applied.include?.length ||
     applied.exclude?.length ||
     sort !== 'score' ||
     direction !== 'desc'
   );
   ```
3. Pass `min_score: minScore, max_score: maxScore, sort, direction` into `useProducts(...)`.
4. Update `clear()` to also reset `setSort('score')`, `setDirection('desc')`, `setMinScore(undefined)`, `setMaxScore(undefined)`.
5. Render a clean **"Sort by"** bar right above the product grid (visible in both default and filtered views):
   - Two criteria buttons: `Score` (`sort === 'score'` -> `variant="primary"`, else `variant="secondary"`) and `Rating` (`sort === 'rating'` -> `variant="primary"`, else `variant="secondary"`).
   - Direction toggle button: `direction === 'desc' ? 'Best first' : 'Lowest first'`.
6. Inside `showFilters`, add **"Minimum score"** chips (`Any`, `50+`, `75+`) setting `minScore` (`undefined`, `50`, `75`) so visitors can combine category + concern band + minimum score + include/exclude ingredients + sort seamlessly.

### Step 5.13 — Add Mobile Unit Tests (`mobile/lib/__tests__/reviews.test.ts`)
Create `mobile/lib/__tests__/reviews.test.ts` testing:
1. `validateReviewInput` accepts `(5, 'Great serum!')` -> returns `null`.
2. `validateReviewInput` rejects rating `0`, rating `6`, non-integer `3.5`, and empty/whitespace body.
3. `queryString({ sort: 'rating', direction: 'desc', min_score: 75 })` produces `'?sort=rating&direction=desc&min_score=75'`.
4. `formatReviewDate('2026-11-20T12:00:00Z')` returns a non-empty formatted string and `formatReviewDate('invalid')` returns `''`.

### Step 5.14 — Run Mobile Quality Gate
```bash
cd mobile
npm run format
npm run check
```
`npm run check` (`typecheck`, `lint`, `format:check`, `test`) MUST exit with code `0`.

---

## 7. Phase 6 — Final Full-Stack Verification Checklist

Run every check one final time from the repository root and confirm **zero errors**:

```bash
# 1. Backend checks
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run alembic check
uv run alembic downgrade base
uv run alembic upgrade head
uv run pytest

# 2. Mobile checks
cd ../mobile
npm run check
```

### Final Acceptance Sign-Off (Dev 1)
- [ ] **US-21:** `ProductDetail`, `ProductCardOut`, and `ProductSummary` return `avg_rating` and `review_count`; mobile shows rating summary and `"No reviews yet"` when empty.
- [ ] **US-24:** Every review carries `source` (`app` | `reddit`) and displays an `"A"` (App) or `"R"` (Reddit) badge; unavailable Reddit cache shows app reviews + fallback notice.
- [ ] **US-25:** `GET /api/v1/products/{id}/reviews` returns combined app + cached Reddit reviews; Reddit refresh runs asynchronously via PostgreSQL job queue (`refresh_reddit_reviews`).
- [ ] **US-26:** `POST /api/v1/products/{id}/reviews` validates `1..5` + non-empty body, rejects duplicates (`409`), updates `Product.avg_rating` and `Product.review_count` transactionally; mobile form supports submit & cancel.
- [ ] **US-28:** `GET /api/v1/users/me/reviews` returns paginated user review history (newest first) with product details; mobile `/my-reviews` screen renders history and empty state.
- [ ] **US-31:** `GET /api/v1/products/filter?sort=rating|score&direction=desc|asc` sorts accurately, keeps unrated products last in both directions, and preserves stable cursor pagination across the rated/unrated boundary.
- [ ] **US-33:** Existing `q`, `category`, `band`, `min_score`, `max_score`, `include`, `exclude` filters remain backward-compatible and fully wired in the mobile UI.

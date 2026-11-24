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

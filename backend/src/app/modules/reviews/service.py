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
            payload={
                "count": len(records),
                "raw_children_count": len(raw_payload.get("data", {}).get("children", [])),
            },
        )
        avg_rating, review_count = await self._repo.compute_product_stats(product_id)
        await self._catalog.update_product_rating_stats(product_id, avg_rating, review_count)
        await self._session.flush()
        return inserted

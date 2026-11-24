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

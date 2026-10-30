from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import register_task
from app.modules.catalog.service import CatalogService

logger = structlog.get_logger(__name__)


@register_task("recompute_dirty_scores")
async def recompute_dirty_scores_task(payload: dict[str, Any], session: AsyncSession) -> None:
    batch_size = int(payload.get("batch_size") or 100)
    service = CatalogService(session)
    count = await service.recompute_dirty_scores(batch_size=batch_size)
    logger.info("recompute_dirty_scores_finished", rescored_count=count)


@register_task("rematch_unmatched")
async def rematch_unmatched_task(payload: dict[str, Any], session: AsyncSession) -> None:
    service = CatalogService(session)
    count = await service.rematch_unmatched()
    logger.info("rematch_unmatched_finished", rematched_count=count)

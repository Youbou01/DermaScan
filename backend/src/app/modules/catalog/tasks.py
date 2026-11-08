from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import enqueue_singleton_job, register_task
from app.modules.catalog.service import CatalogService

logger = structlog.get_logger(__name__)


@register_task("recompute_dirty_scores")
async def recompute_dirty_scores_task(payload: dict[str, Any], session: AsyncSession) -> None:
    batch_size = int(payload.get("batch_size") or 500)
    service = CatalogService(session)
    await service.rematch_unmatched(batch_size=batch_size)

    total_rescored = 0
    for _ in range(5):
        count = await service.recompute_dirty_scores(batch_size=batch_size)
        await session.flush()
        total_rescored += count
        if count < batch_size:
            break

    if await service.has_dirty_or_stale_products():
        await enqueue_singleton_job(
            session,
            task_name="recompute_dirty_scores",
            payload={"batch_size": batch_size},
            queue="default",
        )
    logger.info("recompute_dirty_scores_finished", rescored_count=total_rescored)


@register_task("rematch_unmatched")
async def rematch_unmatched_task(payload: dict[str, Any], session: AsyncSession) -> None:
    service = CatalogService(session)
    count = await service.rematch_unmatched()
    logger.info("rematch_unmatched_finished", rematched_count=count)

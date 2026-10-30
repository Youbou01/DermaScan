import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import register_task
from app.modules.enrichment.service import EnrichmentService

logger = structlog.get_logger(__name__)


@register_task("rate_ingredients")
async def rate_ingredients_task(payload: dict[str, Any], session: AsyncSession) -> None:
    raw_ids = payload.get("ingredient_ids") or []
    ingredient_ids = [uuid.UUID(str(i)) for i in raw_ids]
    if not ingredient_ids:
        logger.info("rate_ingredients_task_empty")
        return

    service = EnrichmentService(session)
    count = await service.rate_ingredients(ingredient_ids)
    logger.info("rate_ingredients_task_finished", rated_count=count)

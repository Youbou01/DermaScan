import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.auth import verify_admin_key
from app.api.admin.schemas import (
    ObfRunInput,
    ScrapeSitemapInput,
    ScrapeUrlsInput,
    SetCuratedRatingInput,
)
from app.core.dependencies import get_session
from app.core.jobs import count_jobs_by_status, enqueue_job
from app.modules.catalog import CatalogService
from app.modules.ingestion import (
    IngestionRunOut,
    IngestionService,
    QuarantineItemOut,
    QuarantineStatus,
    parse_sitemap_xml,
)
from app.modules.ingredients import IngredientService, RatingSource

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/review/quarantine", response_model=list[QuarantineItemOut])
async def list_quarantine_items(
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: QuarantineStatus | None = QuarantineStatus.PENDING,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[QuarantineItemOut]:
    service = IngestionService(session)
    return await service.list_quarantine(status=status_filter, limit=limit, offset=offset)


@router.post("/review/{item_id}/approve")
async def approve_quarantine_item(
    item_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    service = IngestionService(session)
    ok = await service.approve_quarantine(item_id, reviewed_by="admin")
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarantine item not found",
        )
    return {"status": "approved", "id": str(item_id)}


@router.post("/review/{item_id}/reject")
async def reject_quarantine_item(
    item_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    service = IngestionService(session)
    ok = await service.reject_quarantine(item_id, reviewed_by="admin")
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarantine item not found",
        )
    return {"status": "rejected", "id": str(item_id)}


@router.post("/ingredients/{ingredient_id}/rating")
async def set_curated_rating(
    ingredient_id: uuid.UUID,
    data: SetCuratedRatingInput,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    service = IngredientService(session)
    summary_i18n = {"en": data.summary} if data.summary else None
    concern_i18n = {"en": data.concern_note} if data.concern_note else None
    ok = await service.set_rating(
        ingredient_id=ingredient_id,
        rating=data.rating,
        confidence=1.0,
        source=RatingSource.CURATED,
        source_ref="admin-curated",
        summary_i18n=summary_i18n,
        concern_note_i18n=concern_i18n,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found or update rejected",
        )

    catalog_service = CatalogService(session)
    dirty_count = await catalog_service.mark_products_dirty_for_ingredients([ingredient_id])

    await enqueue_job(
        session,
        queue="default",
        task_name="recompute_dirty_scores",
        payload={"batch_size": 100},
    )

    return {
        "status": "updated",
        "ingredient_id": str(ingredient_id),
        "rating": float(data.rating),
        "rating_source": RatingSource.CURATED.value,
        "affected_products": dirty_count,
    }


@router.get("/ingestion/runs", response_model=list[IngestionRunOut])
async def list_ingestion_runs(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[IngestionRunOut]:
    service = IngestionService(session)
    return await service.list_runs(limit=limit, offset=offset)


@router.post("/ingestion/urls")
async def trigger_urls_scrape(
    data: ScrapeUrlsInput,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    service = IngestionService(session)
    run = await service.create_run(source="scrape")
    enqueued = 0
    for url in data.urls:
        await enqueue_job(
            session,
            queue="default",
            task_name="scrape_url",
            payload={
                "url": url,
                "site_config": data.site_config,
                "run_id": str(run.id),
            },
        )
        enqueued += 1

    return {"run_id": str(run.id), "enqueued": enqueued}


@router.post("/ingestion/sitemap")
async def trigger_sitemap_scrape(
    data: ScrapeSitemapInput,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(data.sitemap_url, follow_redirects=True)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch sitemap: HTTP {res.status_code}",
                )
            xml_text = res.text
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sitemap fetch error: {exc}",
        ) from exc

    urls = parse_sitemap_xml(xml_text, pattern=data.url_pattern, limit=data.limit)
    if not urls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No URLs found matching pattern in sitemap",
        )

    service = IngestionService(session)
    run = await service.create_run(source=f"sitemap:{data.sitemap_url}")
    for url in urls:
        await enqueue_job(
            session,
            queue="default",
            task_name="scrape_url",
            payload={
                "url": url,
                "site_config": data.site_config,
                "run_id": str(run.id),
            },
        )

    return {"run_id": str(run.id), "found_urls": len(urls), "enqueued": len(urls)}


@router.post("/ingestion/obf/run")
async def trigger_obf_run(
    data: ObfRunInput,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    service = IngestionService(session)
    run = await service.create_run(source="open_beauty_facts")
    count = 0
    if data.barcodes:
        for barcode in data.barcodes[: data.limit]:
            await enqueue_job(
                session,
                queue="default",
                task_name="import_obf_barcode",
                payload={"barcode": barcode, "run_id": str(run.id)},
            )
            count += 1

    return {"run_id": str(run.id), "status": "started", "count": count}


@router.get("/metrics/summary")
async def get_metrics_summary(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    jobs_summary = await count_jobs_by_status(session)
    ingestion_service = IngestionService(session)
    quarantine_summary = await ingestion_service.get_quarantine_counts()
    return {
        "jobs": jobs_summary,
        "quarantine": quarantine_summary,
    }

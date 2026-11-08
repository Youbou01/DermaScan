"""Integration tests for M11 invariants, quarantine dedup, atomic run counters,
and singleton jobs.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import Job, JobStatus, enqueue_singleton_job
from app.modules.ingestion import (
    IngestionService,
    RawProductSource,
    RawRecord,
    compute_content_hash,
    store_raw_product,
)
from app.modules.ingestion.models import QuarantineItem
from app.modules.ingredients.models import Ingredient


@pytest.mark.asyncio
async def test_case_insensitive_ingredient_uniqueness(db_session: AsyncSession) -> None:
    ing1 = Ingredient(inci_name="GLYCERIN_TEST_UQ")
    db_session.add(ing1)
    await db_session.flush()

    ing2 = Ingredient(inci_name="glycerin_test_uq")
    db_session.add(ing2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_quarantine_deduplication_on_same_raw_product(
    db_session: AsyncSession,
) -> None:
    payload = {"code": "6190000099999", "name": "Test Dedup Quarantine"}
    raw_id = await store_raw_product(
        db_session,
        RawRecord(
            source=RawProductSource.SCRAPE.value,
            source_id="6190000099999",
            content_hash=compute_content_hash(payload),
            payload=payload,
        ),
    )
    svc = IngestionService(db_session)
    q1 = await svc.quarantine(
        raw_product_id=raw_id,
        stage="enrichment",
        reason="low_confidence",
        payload={"attempt": 1},
    )
    q2 = await svc.quarantine(
        raw_product_id=raw_id,
        stage="enrichment",
        reason="parser_llm_disagree",
        payload={"attempt": 2},
    )
    assert q1.id == q2.id
    count = await db_session.scalar(
        select(func.count(QuarantineItem.id)).where(QuarantineItem.raw_product_id == raw_id)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_atomic_ingestion_run_counters(db_session: AsyncSession) -> None:
    svc = IngestionService(db_session)
    run = await svc.create_run(source="scrape:pharma_shop")
    await svc.increment_run_counter(run.id, "enqueued", 2)
    await svc.increment_run_counter(run.id, "fetched", 2)
    await svc.increment_run_counter(run.id, "published", 1)
    await svc.increment_run_counter(run.id, "quarantined", 1)
    await db_session.flush()

    runs = await svc.list_runs(limit=5)
    updated = next(r for r in runs if r.id == run.id)
    assert updated.counters["enqueued"] == 2
    assert updated.counters["published"] == 1
    assert updated.counters["quarantined"] == 1
    assert updated.finished_at is not None


@pytest.mark.asyncio
async def test_enqueue_singleton_job_deduplicates_pending(
    db_session: AsyncSession,
) -> None:
    await enqueue_singleton_job(
        db_session, task_name="recompute_dirty_scores", payload={"batch_size": 500}
    )
    await enqueue_singleton_job(
        db_session, task_name="recompute_dirty_scores", payload={"batch_size": 500}
    )
    count = await db_session.scalar(
        select(func.count(Job.id)).where(
            Job.task_name == "recompute_dirty_scores",
            Job.status == JobStatus.PENDING,
        )
    )
    assert count == 1

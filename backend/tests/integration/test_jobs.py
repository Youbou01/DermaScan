"""Integration tests for PostgreSQL-backed job queue."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import (
    JobStatus,
    enqueue_job,
    execute_job,
    fetch_and_lock_next_job,
    register_task,
    run_pending_jobs,
)

pytestmark = pytest.mark.usefixtures("migrated_database")


async def test_enqueue_and_execute_successful_job(db_session: AsyncSession) -> None:
    executed_payload: dict[str, str] = {}

    @register_task("test_success_task")
    async def sample_handler(payload: dict[str, str], session: AsyncSession) -> None:
        executed_payload.update(payload)

    job_id = await enqueue_job(
        db_session,
        task_name="test_success_task",
        payload={"message": "hello world"},
        queue="default",
    )
    assert job_id is not None

    job = await fetch_and_lock_next_job(db_session, queue="default")
    assert job is not None
    assert job.id == job_id
    assert job.status == JobStatus.RUNNING
    assert job.attempts == 1

    success = await execute_job(db_session, job)
    assert success is True
    completed_status: JobStatus = job.status
    assert completed_status == JobStatus.COMPLETED
    assert job.finished_at is not None
    assert executed_payload.get("message") == "hello world"


async def test_job_failure_triggers_backoff_and_exhaustion(db_session: AsyncSession) -> None:
    fail_count = 0

    @register_task("test_failing_task")
    async def failing_handler(payload: dict[str, str], session: AsyncSession) -> None:
        nonlocal fail_count
        fail_count += 1
        raise ValueError(f"Simulated failure {fail_count}")

    job_id = await enqueue_job(
        db_session,
        task_name="test_failing_task",
        payload={"key": "val"},
        queue="default",
        max_attempts=2,
    )

    # First attempt: should fail and reschedule
    job = await fetch_and_lock_next_job(db_session, queue="default")
    assert job is not None
    assert job.id == job_id

    success = await execute_job(db_session, job)
    assert success is False
    assert job.status == JobStatus.PENDING  # Rescheduled with backoff
    assert "Simulated failure 1" in str(job.error)

    # Simulate second attempt
    job.attempts += 1
    job.status = JobStatus.RUNNING
    success_2 = await execute_job(db_session, job)
    assert success_2 is False
    assert job.status == JobStatus.FAILED
    assert "Simulated failure 2" in str(job.error)


async def test_run_pending_jobs_runner(db_session: AsyncSession) -> None:
    counter = 0

    @register_task("test_batch_task")
    async def batch_handler(payload: dict[str, int], session: AsyncSession) -> None:
        nonlocal counter
        counter += payload.get("inc", 1)

    await enqueue_job(db_session, "test_batch_task", payload={"inc": 2})
    await enqueue_job(db_session, "test_batch_task", payload={"inc": 3})

    ran = await run_pending_jobs(db_session, queue="default")
    assert ran == 2
    assert counter == 5

"""PostgreSQL-backed transactional job queue with SKIP LOCKED concurrency."""

import time
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.metrics import record_job_execution
from app.core.orm import Base, UUIDPrimaryKeyMixin, enum_check, enum_type

logger = structlog.get_logger(__name__)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "job"
    __table_args__ = (
        enum_check("status", JobStatus),
        Index("ix_job_queue_status_scheduled_at", "queue", "status", "scheduled_at"),
    )

    queue: Mapped[str] = mapped_column(
        String(64), default="default", server_default="default", index=True
    )
    task_name: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[JobStatus] = mapped_column(
        enum_type(JobStatus),
        default=JobStatus.PENDING,
        server_default=JobStatus.PENDING.value,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


TaskHandler = Callable[[dict[str, Any], AsyncSession], Coroutine[Any, Any, Any]]
_TASK_REGISTRY: dict[str, TaskHandler] = {}


def register_task(name: str) -> Callable[[TaskHandler], TaskHandler]:
    """Decorator to register an async task handler for a task name."""

    def decorator(fn: TaskHandler) -> TaskHandler:
        _TASK_REGISTRY[name] = fn
        return fn

    return decorator


def get_registered_task(name: str) -> TaskHandler | None:
    return _TASK_REGISTRY.get(name)


async def enqueue_job(
    session: AsyncSession,
    task_name: str,
    payload: dict[str, Any] | None = None,
    queue: str = "default",
    scheduled_at: datetime | None = None,
    max_attempts: int = 3,
) -> uuid.UUID:
    """Enqueue a job into the PostgreSQL job queue."""
    job = Job(
        queue=queue,
        task_name=task_name,
        payload=payload or {},
        max_attempts=max_attempts,
        scheduled_at=scheduled_at or datetime.now(UTC),
    )
    session.add(job)
    await session.flush()
    logger.info("job_enqueued", job_id=str(job.id), task_name=task_name, queue=queue)
    return job.id


async def fetch_and_lock_next_job(session: AsyncSession, queue: str = "default") -> Job | None:
    """Fetch next available pending job using SELECT ... FOR UPDATE SKIP LOCKED."""
    now = datetime.now(UTC)
    stmt = (
        select(Job)
        .where(
            Job.queue == queue,
            Job.status == JobStatus.PENDING,
            Job.scheduled_at <= now,
        )
        .order_by(Job.scheduled_at.asc(), Job.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    res = await session.execute(stmt)
    job = res.scalar_one_or_none()
    if job:
        job.status = JobStatus.RUNNING
        job.started_at = now
        job.attempts += 1
        await session.flush()
    return job


async def execute_job(session: AsyncSession, job: Job) -> bool:
    """Execute a single job with backoff retries and status tracking."""
    handler = _TASK_REGISTRY.get(job.task_name)
    now = datetime.now(UTC)
    start_t = time.perf_counter()
    if handler is None:
        job.status = JobStatus.FAILED
        job.finished_at = now
        job.error = f"No handler registered for task '{job.task_name}'"
        await session.flush()
        record_job_execution(job.queue, job.task_name, "failed", time.perf_counter() - start_t)
        logger.error("job_no_handler", task=job.task_name, job_id=str(job.id))
        return False

    try:
        await handler(job.payload, session)
        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.now(UTC)
        job.error = None
        await session.flush()
        record_job_execution(job.queue, job.task_name, "completed", time.perf_counter() - start_t)
        logger.info("job_completed", task=job.task_name, job_id=str(job.id))
        return True
    except Exception as exc:
        job.error = str(exc)
        duration_s = time.perf_counter() - start_t
        if job.attempts < job.max_attempts:
            backoff_secs = 2**job.attempts * 5
            job.status = JobStatus.PENDING
            job.scheduled_at = datetime.now(UTC) + timedelta(seconds=backoff_secs)
            record_job_execution(job.queue, job.task_name, "retrying", duration_s)
            logger.warning(
                "job_failed_retrying",
                task=job.task_name,
                job_id=str(job.id),
                attempt=job.attempts,
                error=str(exc),
            )
        else:
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(UTC)
            record_job_execution(job.queue, job.task_name, "failed", duration_s)
            logger.error(
                "job_failed_exhausted",
                task=job.task_name,
                job_id=str(job.id),
                attempts=job.attempts,
                error=str(exc),
            )
        await session.flush()
        return False


async def run_pending_jobs(
    session: AsyncSession, queue: str = "default", limit: int | None = None
) -> int:
    """In-process test and execution runner for pending jobs."""
    executed = 0
    while limit is None or executed < limit:
        job = await fetch_and_lock_next_job(session, queue=queue)
        if job is None:
            break
        await execute_job(session, job)
        await session.commit()
        executed += 1
    return executed


async def count_jobs_by_status(session: AsyncSession) -> dict[str, int]:
    """Return counts of jobs grouped by status for observability dashboards."""
    stmt = select(Job.status, func.count(Job.id)).group_by(Job.status)
    res = await session.execute(stmt)
    return {str(status): int(count) for status, count in res.all()}

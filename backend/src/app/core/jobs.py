import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
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


# In-memory registry of async task handlers: task_name -> handler(payload, session)
TaskHandler = Callable[[dict[str, Any], AsyncSession], Coroutine[Any, Any, Any]]
_TASK_REGISTRY: dict[str, TaskHandler] = {}


def register_task(name: str) -> Callable[[TaskHandler], TaskHandler]:
    """Decorator to register a task handler."""

    def decorator(func: TaskHandler) -> TaskHandler:
        _TASK_REGISTRY[name] = func
        return func

    return decorator


async def enqueue_job(
    session: AsyncSession,
    task_name: str,
    payload: dict[str, Any] | None = None,
    queue: str = "default",
    scheduled_at: datetime | None = None,
    max_attempts: int = 3,
) -> uuid.UUID:
    """Enqueue a job idempotently into the PostgreSQL job queue."""
    job = Job(
        queue=queue,
        task_name=task_name,
        payload=payload or {},
        max_attempts=max_attempts,
        scheduled_at=scheduled_at or datetime.now(UTC),
    )
    session.add(job)
    await session.flush()
    logger.info("Enqueued background job", job_id=str(job.id), task_name=task_name, queue=queue)
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

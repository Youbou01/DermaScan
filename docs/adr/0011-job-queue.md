# ADR-0011: PostgreSQL-backed transactional job queue with SKIP LOCKED

- Status: Accepted (supersedes the "no task queue" clause of ADR-0002)
- Date: 2026-10-20

## Context

In Sprint 1, ADR-0002 deferred task queues to keep infrastructure simple. With the introduction of asynchronous background scraping, AI enrichment batches, dirty-flag rescoring, and scheduled synchronization, background tasks require reliable execution, retries, observability, and concurrency control.

Adding external brokers like Redis, Celery, or RabbitMQ would introduce operational overhead, multi-container synchronization requirements, and potential distributed transaction failure modes (e.g., dual-write inconsistencies between database transactions and queue state).

## Decision

Implement a lightweight, transactional job queue directly in PostgreSQL using a dedicated `job` table and `SELECT ... FOR UPDATE SKIP LOCKED`:

1. **Transactional Enqueueing:** Enqueueing a job participates directly in the caller's database transaction. If the transaction rolls back, the job is not enqueued.
2. **Concurrency & Locking:** Workers fetch pending jobs using `SELECT ... FOR UPDATE SKIP LOCKED` ordered by `scheduled_at`, preventing race conditions without lock contention.
3. **Status & Retries:** Job state (`pending`, `running`, `completed`, `failed`, `cancelled`) is tracked explicitly with exponential backoff on failure up to `max_attempts`.
4. **Standalone Worker:** The queue is serviced by `app.worker` running concurrently in a dedicated container or process, with graceful SIGINT/SIGTERM shutdown.
5. **In-Process Test Runner:** Tests can process jobs synchronously in the test transaction via `run_pending_jobs(session)`.

## Consequences

- Zero extra infrastructure: Runs entirely on existing PostgreSQL 18 instance.
- Strong ACID consistency: Job state transitions are completely durable and atomic.
- Slower throughput than dedicated in-memory brokers like Redis, but easily handles hundreds of jobs per second—far exceeding DermaScan's enrichment and rescoring throughput needs.

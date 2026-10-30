"""Background worker process executing jobs from the PostgreSQL job queue."""

import asyncio
import contextlib
import signal
import sys

import structlog

from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.jobs import execute_job, fetch_and_lock_next_job
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)

QUEUES = ["default", "enrichment"]
POLL_INTERVAL_SECONDS = 1.0


class Worker:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.running = False
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        configure_logging(self.settings)
        engine = create_engine(self.settings)
        session_factory = create_session_factory(engine)
        self.running = True

        logger.info("worker_started", queues=QUEUES)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self.stop)

        try:
            while self.running and not self._stop_event.is_set():
                had_work = False
                async with session_factory() as session:
                    for queue in QUEUES:
                        job = await fetch_and_lock_next_job(session, queue=queue)
                        if job is not None:
                            had_work = True
                            await execute_job(session, job)
                            await session.commit()
                            break

                if not had_work:
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(
                            self._stop_event.wait(), timeout=POLL_INTERVAL_SECONDS
                        )
        finally:
            await engine.dispose()
            logger.info("worker_stopped")

    def stop(self, *args: object) -> None:
        logger.info("worker_stopping")
        self.running = False
        self._stop_event.set()


def main() -> None:
    worker = Worker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt, SystemExit:
        sys.exit(0)


if __name__ == "__main__":
    main()

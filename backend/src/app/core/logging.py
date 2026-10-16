"""Structured logging.

- local environment: human-readable coloured console output
- every other environment: one JSON object per line (searchable in any log tool)

Everything is routed through structlog, including stdlib loggers (uvicorn,
sqlalchemy, ...), so all lines share the same format and carry the request ID.

NEVER log secrets, passwords, tokens, full request bodies or auth headers.
"""

import logging
import sys

import structlog
from structlog.typing import Processor

from app.core.config import Settings

_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def configure_logging(settings: Settings) -> None:
    json_logs = settings.app_env != "local"

    # Runs for every log line, whether it comes from structlog or stdlib logging.
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # adds request_id (bound by middleware)
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    final_processors: list[Processor] = [structlog.stdlib.ProcessorFormatter.remove_processors_meta]
    if json_logs:
        final_processors += [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        final_processors.append(structlog.dev.ConsoleRenderer())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=final_processors,
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    # Let uvicorn's loggers flow through our handler instead of their own.
    for name in _UVICORN_LOGGERS:
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    # Our middleware writes one access line per request; silence uvicorn's duplicate.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

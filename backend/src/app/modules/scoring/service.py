import structlog

from app.modules.scoring.engine import SCORING_VERSION

logger = structlog.get_logger()


def get_current_scoring_version() -> int:
    """Returns the current active scoring version constant for database synchronization."""
    logger.debug("Retrieving scoring version", version=SCORING_VERSION)
    return SCORING_VERSION

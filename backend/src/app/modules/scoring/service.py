import logging

from app.modules.scoring.engine import SCORING_VERSION

logger = logging.getLogger(__name__)


def get_current_scoring_version() -> int:
    """Returns the current active scoring version constant for database synchronization."""
    return SCORING_VERSION

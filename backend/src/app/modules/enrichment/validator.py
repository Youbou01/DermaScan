import re

from app.modules.ingredients.enums import ReviewStatus

FORBIDDEN_WORDS_RE = re.compile(r"\b(safe|unsafe|toxic|harmful|dangerous)\b", re.IGNORECASE)


def validate_and_clean_plain_text(text: str | None, max_words: int) -> str | None:
    """Validate and sanitize plain language text.

    - Strips forbidden medical/fear-mongering jargon (safe, unsafe, toxic, harmful, dangerous).
    - Enforces maximum word count constraint.
    """
    if not text:
        return None

    cleaned = FORBIDDEN_WORDS_RE.sub("concerning", text.strip())
    words = cleaned.split()
    if len(words) <= max_words:
        return cleaned

    truncated = " ".join(words[:max_words]).rstrip(".,;:-")
    return f"{truncated}."


def compute_consensus_rating(
    r1: float,
    c1: float,
    r2: float | None = None,
    c2: float | None = None,
) -> tuple[float, float, ReviewStatus]:
    """Calculate consensus rating, confidence, and review status between two models.

    Rules:
    - |r1 - r2| <= 1.5: mean rating, min(c1, c2), auto approved
    - 1.5 < diff <= 3.0: mean rating, min(c1, c2) * 0.6, needs review
    - diff > 3.0: min(r1, r2) (conservative), confidence 0.3, needs review
    - Single model: r1, confidence c1 * 0.7, auto approved if >= 4.0 else needs review
    """
    if r2 is None or c2 is None:
        confidence = round(c1 * 0.7, 2)
        status = ReviewStatus.AUTO if r1 >= 4.0 else ReviewStatus.NEEDS_REVIEW
        return r1, confidence, status

    diff = abs(r1 - r2)
    if diff <= 1.5:
        rating = round((r1 + r2) / 2.0, 1)
        confidence = round(min(c1, c2), 2)
        status = ReviewStatus.AUTO
    elif diff <= 3.0:
        rating = round((r1 + r2) / 2.0, 1)
        confidence = round(min(c1, c2) * 0.6, 2)
        status = ReviewStatus.NEEDS_REVIEW
    else:
        rating = round(min(r1, r2), 1)
        confidence = 0.3
        status = ReviewStatus.NEEDS_REVIEW

    return rating, confidence, status

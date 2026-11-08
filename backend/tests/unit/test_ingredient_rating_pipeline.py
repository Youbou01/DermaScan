from app.modules.enrichment.validator import (
    compute_consensus_rating,
    validate_and_clean_plain_text,
)
from app.modules.ingredients.enums import ReviewStatus


def test_plain_text_validation_strips_forbidden_words() -> None:
    text = "This ingredient is safe and non-toxic for sensitive skin."
    cleaned = validate_and_clean_plain_text(text, max_words=20)
    assert cleaned is not None
    assert "safe" not in cleaned.lower()
    assert "toxic" not in cleaned.lower()
    assert "concerning" in cleaned.lower()


def test_plain_text_validation_word_limit() -> None:
    long_text = "word " * 50
    cleaned = validate_and_clean_plain_text(long_text, max_words=20)
    assert cleaned is not None
    assert len(cleaned.split()) <= 20
    assert cleaned.endswith(".")


def test_consensus_rating_agreement() -> None:
    # Close ratings: r1=9.0, r2=8.5 (diff=0.5 <= 1.5)
    rating, conf, status = compute_consensus_rating(r1=9.0, c1=0.9, r2=8.5, c2=0.8)
    assert rating == 8.8
    assert conf == 0.8
    assert status == ReviewStatus.AUTO


def test_consensus_rating_moderate_disagreement() -> None:
    # Diff=2.0 (1.5 < diff <= 3.0)
    rating, conf, status = compute_consensus_rating(r1=7.0, c1=0.9, r2=5.0, c2=0.8)
    assert rating == 6.0
    assert conf == round(0.8 * 0.6, 2)
    assert status == ReviewStatus.NEEDS_REVIEW


def test_consensus_rating_large_disagreement() -> None:
    # Diff=4.0 (> 3.0) -> conservative minimum rating
    rating, conf, status = compute_consensus_rating(r1=8.0, c1=0.9, r2=4.0, c2=0.8)
    assert rating == 4.0
    assert conf == 0.3
    assert status == ReviewStatus.NEEDS_REVIEW


def test_consensus_rating_single_model() -> None:
    rating, conf, status = compute_consensus_rating(r1=8.5, c1=1.0)
    assert rating == 8.5
    assert conf == 0.7
    assert status == ReviewStatus.AUTO

    rating_low, _conf_low, status_low = compute_consensus_rating(r1=3.0, c1=1.0)
    assert rating_low == 3.0
    assert status_low == ReviewStatus.NEEDS_REVIEW

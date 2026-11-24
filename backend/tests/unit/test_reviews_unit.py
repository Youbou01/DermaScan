"""Unit tests for the reviews module."""

import pytest
from pydantic import ValidationError

from app.modules.reviews.reddit_adapter import normalize_reddit_posts
from app.modules.reviews.schemas import CreateReviewIn


def test_create_review_in_valid() -> None:
    for rating in range(1, 6):
        review = CreateReviewIn(rating=rating, body="  Great moisturizer for sensitive skin!  ")
        assert review.rating == rating
        assert review.body == "Great moisturizer for sensitive skin!"


def test_create_review_in_invalid_ratings() -> None:
    for bad_rating in (0, 6, -1, 10):
        with pytest.raises(ValidationError):
            CreateReviewIn(rating=bad_rating, body="Valid body text")


def test_create_review_in_empty_body() -> None:
    for empty_body in ("", "   ", "\n\t  "):
        with pytest.raises(ValidationError):
            CreateReviewIn(rating=5, body=empty_body)


def test_normalize_reddit_posts_valid() -> None:
    payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc1234",
                        "title": "Holy grail cleanser",
                        "selftext": "I have been using this for 3 months and my skin cleared up completely.",
                        "author": "skincare_fan",
                        "permalink": "/r/SkincareAddiction/comments/abc1234/holy_grail_cleanser/",
                        "created_utc": 1700000000,
                    }
                },
                {
                    "data": {
                        "id": "def5678",
                        "title": "Title only review here with enough length",
                        "selftext": "",
                        "author": "minimalist",
                        "permalink": "/r/SkincareAddiction/comments/def5678/title_only/",
                        "created_utc": 1700001000,
                    }
                },
            ]
        }
    }
    records = normalize_reddit_posts(payload)
    assert len(records) == 2
    rec1 = records[0]
    assert rec1.external_id == "abc1234"
    assert rec1.author_name == "u/skincare_fan"
    assert "Holy grail cleanser" in rec1.body
    assert (
        rec1.external_url
        == "https://www.reddit.com/r/SkincareAddiction/comments/abc1234/holy_grail_cleanser/"
    )
    assert rec1.rating is None

    rec2 = records[1]
    assert rec2.external_id == "def5678"
    assert rec2.author_name == "u/minimalist"
    assert rec2.body == "Title only review here with enough length"


def test_normalize_reddit_posts_skips_malformed_and_short() -> None:
    payload = {
        "data": {
            "children": [
                {},  # empty child
                {"data": {}},  # missing id/body
                {"data": {"id": "short1", "title": "Too short", "selftext": ""}},  # < 10 chars
                {
                    "data": {
                        "id": "",
                        "title": "A very long title that lacks an id",
                        "selftext": "",
                    }
                },
            ]
        }
    }
    records = normalize_reddit_posts(payload)
    assert len(records) == 0

    assert normalize_reddit_posts({}) == []

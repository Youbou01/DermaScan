"""Integration tests for reviews, ratings, Reddit caching, and user review history."""

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import Job
from app.core.security import create_access_token, hash_password
from app.modules.catalog.models import Product
from app.modules.identity.models import UserAccount
from app.modules.reviews.reddit_adapter import ExternalReviewRecord, RedditReviewsAdapter
from app.modules.reviews.service import ReviewService
from tests.factories import make_brand, make_product

pytestmark = pytest.mark.usefixtures("migrated_database")


async def _create_user(
    session: AsyncSession, *, email: str | None = None, display_name: str = "Test User"
) -> UserAccount:
    user = UserAccount(
        email=email or f"user-{uuid.uuid4()}@example.test",
        password_hash=hash_password("test-password"),
        display_name=display_name,
    )
    session.add(user)
    await session.flush()
    return user


def _auth(user: UserAccount) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _create_product(session: AsyncSession, **overrides: Any) -> Product:
    product = make_product(**overrides)
    session.add(product)
    await session.flush()
    return product


async def test_get_product_reviews_empty_enqueues_refresh(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await _create_product(db_session)

    resp = await client.get(f"/api/v1/products/{product.id}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == str(product.id)
    assert data["avg_rating"] is None
    assert data["review_count"] == 0
    assert data["items"] == []
    assert data["external_source_status"] == "refreshing"

    jobs = (
        (
            await db_session.execute(
                select(Job).where(
                    Job.task_name == "refresh_reddit_reviews",
                    Job.payload["product_id"].as_string() == str(product.id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(jobs) >= 1


async def test_create_review_unauthorized(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await _create_product(db_session)
    resp = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 5, "body": "Great product!"},
    )
    assert resp.status_code == 401


async def test_create_review_validation_errors(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)

    # Invalid rating: 0
    resp0 = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 0, "body": "Too low rating"},
        headers=_auth(user),
    )
    assert resp0.status_code == 422

    # Invalid rating: 6
    resp6 = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 6, "body": "Too high rating"},
        headers=_auth(user),
    )
    assert resp6.status_code == 422

    # Blank body
    resp_empty = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 5, "body": "   "},
        headers=_auth(user),
    )
    assert resp_empty.status_code == 422


async def test_create_review_not_found(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    random_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/products/{random_id}/reviews",
        json={"rating": 5, "body": "Valid body"},
        headers=_auth(user),
    )
    assert resp.status_code == 404


async def test_create_review_success_and_aggregates(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user1 = await _create_user(db_session, display_name="Alice")
    user2 = await _create_user(db_session, display_name="Bob")
    product = await _create_product(db_session)

    # User 1 posts 5 stars
    resp1 = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 5, "body": "Excellent!"},
        headers=_auth(user1),
    )
    assert resp1.status_code == 201
    r1_data = resp1.json()
    assert r1_data["source"] == "app"
    assert r1_data["author_name"] == "Alice"
    assert r1_data["rating"] == 5
    assert r1_data["body"] == "Excellent!"

    # Product detail reflects new rating stats immediately
    detail1 = (await client.get(f"/api/v1/products/{product.id}")).json()
    assert detail1["avg_rating"] == 5.0
    assert detail1["review_count"] == 1

    # User 2 posts 4 stars
    resp2 = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 4, "body": "Pretty good"},
        headers=_auth(user2),
    )
    assert resp2.status_code == 201

    # Average recalculated: (5 + 4) / 2 = 4.5
    detail2 = (await client.get(f"/api/v1/products/{product.id}")).json()
    assert detail2["avg_rating"] == 4.5
    assert detail2["review_count"] == 2


async def test_create_review_duplicate_conflict(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)

    resp1 = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 5, "body": "First review"},
        headers=_auth(user),
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 4, "body": "Second review"},
        headers=_auth(user),
    )
    assert resp2.status_code == 409
    assert resp2.json()["type"] == "urn:skincare:problem:duplicate-review"


async def test_mixed_sources_and_idempotent_reddit_refresh(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, display_name="Carol")
    brand = make_brand(name="CeraVe")
    db_session.add(brand)
    await db_session.flush()
    product = await _create_product(db_session, brand_id=brand.id, name="Hydrating Cleanser")

    # Post app review
    await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 5, "body": "Loved it!"},
        headers=_auth(user),
    )

    # Mock Reddit adapter returning 2 records
    mock_records = [
        ExternalReviewRecord(
            external_id="post_1",
            author_name="u/reddit_user1",
            body="Great cleanser for dry skin.",
            external_url="https://reddit.com/r/SkincareAddiction/1",
            created_at=datetime.now(UTC),
            rating=None,
        ),
        ExternalReviewRecord(
            external_id="post_2",
            author_name="u/reddit_user2",
            body="Gentle and non-foaming.",
            external_url="https://reddit.com/r/SkincareAddiction/2",
            created_at=datetime.now(UTC),
            rating=None,
        ),
    ]
    mock_adapter = RedditReviewsAdapter()
    mock_adapter.fetch_reviews = AsyncMock(return_value=(mock_records, {"data": {"children": []}}))  # type: ignore[method-assign]

    service = ReviewService(db_session, reddit_adapter=mock_adapter)
    inserted1 = await service.refresh_reddit_reviews(product.id)
    await db_session.commit()
    assert inserted1 == 2

    # Refresh again: idempotent, 0 new rows
    inserted2 = await service.refresh_reddit_reviews(product.id)
    await db_session.commit()
    assert inserted2 == 0

    # GET /reviews returns combined items with status fresh
    resp = await client.get(f"/api/v1/products/{product.id}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["external_source_status"] == "fresh"
    assert data["review_count"] == 3  # 1 app + 2 reddit
    assert data["avg_rating"] == 5.0  # only app review had rating

    sources = {item["source"] for item in data["items"]}
    assert "app" in sources
    assert "reddit" in sources


async def test_reddit_failure_handling(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)

    # Post app review
    await client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 4, "body": "Works fine"},
        headers=_auth(user),
    )

    # Mock Reddit adapter raising HTTP error
    mock_adapter = RedditReviewsAdapter()
    mock_adapter.fetch_reviews = AsyncMock(  # type: ignore[method-assign]
        side_effect=httpx.HTTPStatusError(
            "Reddit 503",
            request=httpx.Request("GET", "https://reddit.com"),
            response=httpx.Response(503),
        )
    )

    service = ReviewService(db_session, reddit_adapter=mock_adapter)
    inserted = await service.refresh_reddit_reviews(product.id)
    await db_session.commit()
    assert inserted == 0

    # GET /reviews still succeeds with existing app reviews and external_source_status="unavailable"
    resp = await client.get(f"/api/v1/products/{product.id}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["external_source_status"] == "unavailable"
    assert len(data["items"]) == 1
    assert data["items"][0]["source"] == "app"


async def test_user_reviews_history_pagination(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await _create_user(db_session, display_name="Reviewer")
    other_user = await _create_user(db_session, display_name="Other")

    # Unauthorized access rejected
    unauth = await client.get("/api/v1/users/me/reviews")
    assert unauth.status_code == 401

    # Create 3 products reviewed by user, 1 reviewed by other_user
    p1 = await _create_product(db_session, name="Product 1")
    p2 = await _create_product(db_session, name="Product 2")
    p3 = await _create_product(db_session, name="Product 3")
    p_other = await _create_product(db_session, name="Other Product")

    await client.post(
        f"/api/v1/products/{p1.id}/reviews",
        json={"rating": 3, "body": "Review 1"},
        headers=_auth(user),
    )
    await client.post(
        f"/api/v1/products/{p2.id}/reviews",
        json={"rating": 4, "body": "Review 2"},
        headers=_auth(user),
    )
    await client.post(
        f"/api/v1/products/{p3.id}/reviews",
        json={"rating": 5, "body": "Review 3"},
        headers=_auth(user),
    )
    await client.post(
        f"/api/v1/products/{p_other.id}/reviews",
        json={"rating": 1, "body": "Other user review"},
        headers=_auth(other_user),
    )

    # Page 1: limit=2
    resp_p1 = await client.get("/api/v1/users/me/reviews?limit=2", headers=_auth(user))
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()
    assert len(data_p1["items"]) == 2
    assert data_p1["next_cursor"] is not None
    assert all(item["product_id"] != str(p_other.id) for item in data_p1["items"])

    # Page 2: with cursor
    cursor = data_p1["next_cursor"]
    resp_p2 = await client.get(
        f"/api/v1/users/me/reviews?limit=2&cursor={cursor}", headers=_auth(user)
    )
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()
    assert len(data_p2["items"]) == 1
    assert data_p2["next_cursor"] is None

    p1_ids = {item["id"] for item in data_p1["items"]}
    p2_ids = {item["id"] for item in data_p2["items"]}
    assert len(p1_ids & p2_ids) == 0  # no overlap

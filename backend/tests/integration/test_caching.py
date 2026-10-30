import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_session
from app.main import create_app


@pytest.mark.asyncio
async def test_etag_and_conditional_get_on_categories(client: AsyncClient) -> None:
    # First GET: expect 200 with ETag and Cache-Control headers
    r1 = await client.get("/api/v1/categories")
    assert r1.status_code == 200
    etag = r1.headers.get("etag")
    cache_control = r1.headers.get("cache-control")

    assert etag is not None
    assert cache_control is not None
    assert "public" in cache_control
    assert "max-age=3600" in cache_control

    # Second GET with matching If-None-Match: expect 304 Not Modified
    r2 = await client.get("/api/v1/categories", headers={"If-None-Match": etag})
    assert r2.status_code == 304
    assert r2.content == b""
    assert r2.headers.get("etag") == etag

    # Third GET with mismatched If-None-Match: expect 200 OK
    r3 = await client.get("/api/v1/categories", headers={"If-None-Match": '"different-hash"'})
    assert r3.status_code == 200
    assert len(r3.content) > 0


@pytest.mark.asyncio
async def test_home_caching_headers(client: AsyncClient) -> None:
    r = await client.get("/api/v1/home")
    assert r.status_code == 200
    assert r.headers.get("etag") is not None
    assert "max-age=300" in r.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_rate_limiting_enforcement(db_session: AsyncSession) -> None:
    # Set rpm=3 to easily trigger rate limiting
    settings = Settings(app_env="test", enable_rate_limiting=True, rate_limit_rpm=3)
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # 3 allowed requests
        for _ in range(3):
            res = await c.get("/api/v1/categories")
            assert res.status_code in (200, 304)

        # 4th request must be blocked with 429
        blocked = await c.get("/api/v1/categories")
        assert blocked.status_code == 429
        assert blocked.headers.get("content-type") == "application/problem+json"
        data = blocked.json()
        assert data["type"] == "urn:skincare:problem:rate-limit-exceeded"
        assert data["status"] == 429
        assert "retry-after" in blocked.headers

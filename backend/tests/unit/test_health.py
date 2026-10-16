import httpx

from app.core.config import Settings
from app.main import create_app


def make_client() -> httpx.AsyncClient:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/test",
    )
    transport = httpx.ASGITransport(app=create_app(settings))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_liveness_does_not_need_the_database() -> None:
    async with make_client() as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

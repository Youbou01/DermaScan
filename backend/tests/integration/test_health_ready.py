import httpx


async def test_readiness_reports_ok_when_database_is_reachable(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

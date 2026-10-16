import json

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.main import create_app


class ProductNotFoundError(NotFoundError):
    code = "product-not-found"
    title = "Product not found"


class Payload(BaseModel):
    barcode: str


def make_app() -> FastAPI:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/test",
    )
    app = create_app(settings)

    @app.get("/_test/not-found")
    async def not_found() -> None:
        raise ProductNotFoundError("No product with barcode 123")

    @app.get("/_test/conflict")
    async def conflict() -> None:
        raise ConflictError

    @app.get("/_test/crash")
    async def crash() -> None:
        raise RuntimeError("secret internal detail: password=hunter2")

    @app.post("/_test/validate")
    async def validate(payload: Payload) -> None:
        return None

    return app


@pytest.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=make_app(), raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_domain_error_becomes_problem_json(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/not-found")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "urn:skincare:problem:product-not-found"
    assert body["title"] == "Product not found"
    assert body["detail"] == "No product with barcode 123"
    assert body["instance"] == "/_test/not-found"
    assert body["request_id"] == response.headers["x-request-id"]


async def test_error_without_detail_uses_class_defaults(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/conflict")

    assert response.status_code == 409
    assert response.json()["type"] == "urn:skincare:problem:conflict"
    assert "detail" not in response.json()


async def test_unknown_route_is_problem_json(client: httpx.AsyncClient) -> None:
    response = await client.get("/nope")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:skincare:problem:http-404"


async def test_validation_error_lists_fields_without_echoing_input(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/_test/validate", json={"barcode": 123, "secret": "x"})

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == "urn:skincare:problem:request-validation-failed"
    assert body["errors"][0]["loc"] == ["body", "barcode"]
    assert "input" not in body["errors"][0]


async def test_unhandled_exception_hides_internals(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/crash")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text
    assert response.json()["request_id"]


async def test_valid_incoming_request_id_is_kept(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "mobile-abc-12345"})

    assert response.headers["x-request-id"] == "mobile-abc-12345"


async def test_malicious_request_id_is_replaced(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "bad id\nforged-line"})

    assert response.headers["x-request-id"] != "bad id\nforged-line"
    assert len(response.headers["x-request-id"]) == 36  # generated UUID


async def test_access_log_is_json_and_carries_request_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The app is built inside the test on purpose: logging binds to stdout when the app
    # is created, and capsys only captures what is created after it starts.
    transport = httpx.ASGITransport(app=make_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/_test/conflict")

    lines = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")
    ]
    access = next(line for line in lines if line["event"] == "request_completed")
    assert access["request_id"] == response.headers["x-request-id"]
    assert access["status_code"] == 409
    assert access["path"] == "/_test/conflict"

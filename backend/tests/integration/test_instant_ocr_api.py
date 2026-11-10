"""End-to-end coverage for the signed-in, ephemeral ingredient analysis API."""

import io
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.enrichment.schemas import OcrIngredientsResult
from app.modules.enrichment.service import EnrichmentService
from app.modules.identity.models import UserAccount
from tests.factories import make_ingredient


async def _auth_headers(session: AsyncSession) -> dict[str, str]:
    user = UserAccount(
        email="ocr-user@example.test",
        password_hash=hash_password("test-password"),
        display_name="OCR user",
    )
    session.add(user)
    await session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


async def test_text_analysis_returns_immediate_localized_breakdown(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    aqua = make_ingredient(inci_name="AQUA", aliases=["Aqua"])
    glycerin = make_ingredient(inci_name="GLYCERIN", aliases=["Glycerin"])
    db_session.add_all([aqua, glycerin])
    headers = await _auth_headers(db_session)
    await db_session.flush()

    english = await client.post(
        "/api/v1/analysis/text",
        headers=headers,
        json={"text": "Ingredients: Aqua, Glycerin", "product_name": "Hydration Mist"},
    )
    french = await client.post(
        "/api/v1/analysis/text",
        headers={**headers, "Accept-Language": "fr-FR,fr;q=0.9"},
        json={"text": "Ingrédients : Aqua, Glycerin"},
    )

    assert english.status_code == french.status_code == 200
    english_body = english.json()
    assert english_body["extracted_text"] == "Ingredients: Aqua, Glycerin"
    assert english_body["score_coverage"] == 1.0
    assert [item["inci_name"] for item in english_body["ingredients"]] == ["AQUA", "GLYCERIN"]
    assert "Hydration Mist" in english_body["summary"]
    assert "niveau de préoccupation" in french.json()["summary"]


async def test_text_analysis_normalizes_unmatched_foreign_label_tokens(
    client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    aqua = make_ingredient(inci_name="AQUA", aliases=["Aqua"])
    glycerin = make_ingredient(inci_name="GLYCERIN", aliases=["Glycerin"])
    db_session.add_all([aqua, glycerin])
    headers = await _auth_headers(db_session)
    await db_session.flush()

    async def normalize(_self: EnrichmentService, tokens: list[str]) -> dict[str, str]:
        assert tokens == ["Agua"]
        return {"Agua": "AQUA"}

    monkeypatch.setattr(EnrichmentService, "normalize_inci_tokens", normalize)
    response = await client.post(
        "/api/v1/analysis/text",
        headers=headers,
        json={"text": "Ingredientes: Agua, Glycerin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score_coverage"] == 1.0
    assert [item["name"] for item in body["ingredients"]] == ["Agua", "Glycerin"]
    assert [item["inci_name"] for item in body["ingredients"]] == ["AQUA", "GLYCERIN"]


async def test_ocr_analysis_validates_photo_and_uses_the_same_pipeline(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    aqua = make_ingredient(inci_name="AQUA", aliases=["Aqua"])
    glycerin = make_ingredient(inci_name="GLYCERIN", aliases=["Glycerin"])
    db_session.add_all([aqua, glycerin])
    headers = await _auth_headers(db_session)
    await db_session.flush()

    ocr = OcrIngredientsResult(
        ingredients_text="Aqua, Glycerin",
        confidence=0.98,
        is_readable=True,
    )
    with patch.object(EnrichmentService, "ocr_ingredients", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = ocr
        response = await client.post(
            "/api/v1/analysis/ocr",
            headers=headers,
            data={"product_name": "Label scan"},
            files={"photo": ("label.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["extracted_text"] == "Aqua, Glycerin"
    mock_ocr.assert_awaited_once()


async def test_analysis_rejects_an_unsupported_photo_type(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _auth_headers(db_session)

    response = await client.post(
        "/api/v1/analysis/ocr",
        headers=headers,
        files={"photo": ("label.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "urn:skincare:problem:unsupported-ingredient-image"

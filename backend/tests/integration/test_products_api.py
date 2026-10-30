import uuid

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.models import Product, ProductIngredient
from app.modules.ingredients.models import Ingredient
from tests.factories import (
    make_barcode,
    make_brand,
    make_category,
    make_ingredient,
    make_product,
)

pytestmark = pytest.mark.usefixtures("migrated_database")

PRODUCT_KEYS = {
    "id",
    "barcode",
    "name",
    "brand",
    "image_url",
    "category",
    "score",
    "score_band",
    "score_coverage",
    "score_is_estimated",
    "ingredients",
}
INGREDIENT_KEYS = {
    "position",
    "name",
    "inci_name",
    "matched",
    "risk_level",
    "rationale",
    "rating",
    "summary",
    "confidence",
}


async def add_product(
    session: AsyncSession,
    rows: list[tuple[int, str, Ingredient | None]] | None = None,
    **overrides: object,
) -> Product:
    """Persist a product whose label rows are (position, printed text, ingredient or None)."""
    product = make_product(**overrides)
    product.ingredients = [
        ProductIngredient(
            position=position,
            raw_text=text,
            ingredient_id=ingredient.id if ingredient else None,
        )
        for position, text, ingredient in (rows or [])
    ]
    session.add(product)
    await session.flush()
    return product


# --------------------------------------------------------------- the response contract
async def test_barcode_lookup_returns_the_documented_contract(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    aqua = make_ingredient(inci_name="AQUA", risk_level=RiskLevel.LOW)
    category = make_category(names={"en": "Moisturizer", "fr": "Hydratant"}, slug="moisturizer")
    brand = make_brand(name="Nivea")
    db_session.add_all([aqua, category, brand])
    await db_session.flush()
    product = await add_product(
        db_session,
        [(1, "Aqua (Water)", aqua)],
        brand_id=brand.id,
        primary_category_id=category.id,
        name="Soft Cream",
        score=82,
        score_band=RiskLevel.LOW,
        score_coverage=1.0,
        image_url="https://example.test/cream.jpg",
    )

    response = await client.get(f"/api/v1/products/by-barcode/{product.barcode}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PRODUCT_KEYS  # a changed shape is a breaking API change: do it on purpose
    assert set(body["ingredients"][0]) == INGREDIENT_KEYS
    assert body["id"] == str(product.id)
    assert body["barcode"] == product.barcode
    assert body["name"] == "Soft Cream"
    assert body["brand"] == "Nivea"
    assert body["image_url"] == "https://example.test/cream.jpg"
    assert body["category"] == {"slug": "moisturizer", "name": "Moisturizer"}
    assert (body["score"], body["score_band"], body["score_coverage"]) == (82, "low", 1.0)


async def test_product_by_id_equals_product_by_barcode(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session)

    by_id = await client.get(f"/api/v1/products/{product.id}")
    by_barcode = await client.get(f"/api/v1/products/by-barcode/{product.barcode}")

    assert by_id.status_code == by_barcode.status_code == 200
    assert by_id.json() == by_barcode.json()


async def test_a_bare_product_has_nulls_and_an_unknown_band_never_safe(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session)

    body = (await client.get(f"/api/v1/products/{product.id}")).json()

    assert body["brand"] is None
    assert body["category"] is None
    assert body["score"] is None
    assert body["score_band"] == "unknown"
    assert body["ingredients"] == []


# ------------------------------------------------------------------------ ingredients
async def test_ingredients_come_in_label_order_whatever_the_insertion_order(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    first, second, third = (make_ingredient(inci_name=n) for n in ("AQUA", "GLYCERIN", "PARFUM"))
    db_session.add_all([first, second, third])
    await db_session.flush()
    product = await add_product(
        db_session,
        [(3, "Parfum", third), (1, "Aqua", first), (2, "Glycerin", second)],  # shuffled on purpose
    )

    body = (await client.get(f"/api/v1/products/{product.id}")).json()

    assert [i["position"] for i in body["ingredients"]] == [1, 2, 3]
    assert [i["inci_name"] for i in body["ingredients"]] == ["AQUA", "GLYCERIN", "PARFUM"]


async def test_unrecognized_ingredients_are_shown_as_unknown_never_as_safe(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    aqua = make_ingredient(inci_name="AQUA")
    db_session.add(aqua)
    await db_session.flush()
    product = await add_product(db_session, [(1, "Aqua", aqua), (2, "Mystery Extract", None)])

    body = (await client.get(f"/api/v1/products/{product.id}")).json()
    known, unknown = body["ingredients"]

    assert (known["matched"], known["risk_level"]) == (True, "low")
    assert unknown == {
        "position": 2,
        "name": "Mystery Extract",  # exactly as printed on the label
        "inci_name": None,
        "matched": False,
        "risk_level": "unknown",
        "rationale": None,
        "rating": None,
        "summary": None,
        "confidence": None,
    }


async def test_a_known_but_unrated_ingredient_is_matched_yet_unknown(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    unrated = make_ingredient(inci_name="NEW EXTRACT", risk_level=RiskLevel.UNKNOWN)
    db_session.add(unrated)
    await db_session.flush()
    product = await add_product(db_session, [(1, "New Extract", unrated)])

    [item] = (await client.get(f"/api/v1/products/{product.id}")).json()["ingredients"]

    assert (item["matched"], item["risk_level"], item["inci_name"]) == (
        True,
        "unknown",
        "NEW EXTRACT",
    )


async def test_flagged_ingredient_exposes_its_rationale(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    paraben = make_ingredient(
        inci_name="PROPYLPARABEN",
        risk_level=RiskLevel.HIGH,
        rationale={"en": "Restricted preservative."},
    )
    db_session.add(paraben)
    await db_session.flush()
    product = await add_product(db_session, [(1, "Propylparaben", paraben)])

    [item] = (await client.get(f"/api/v1/products/{product.id}")).json()["ingredients"]

    assert (item["risk_level"], item["rationale"]) == ("high", "Restricted preservative.")


# ------------------------------------------------------------------ barcode handling
async def test_scanning_a_upc_a_finds_the_product_stored_as_gtin13(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, barcode="0036000291452")

    for scanned in ("036000291452", "0036000291452", "0 36000 29145 2", "036-000-291-452"):
        response = await client.get(f"/api/v1/products/by-barcode/{scanned}")
        assert response.status_code == 200, scanned
        assert response.json()["id"] == str(product.id)
        assert response.json()["barcode"] == "0036000291452"


async def test_scanning_an_ean8_finds_the_product_stored_as_gtin13(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, barcode="0000073513537")

    response = await client.get("/api/v1/products/by-barcode/73513537")

    assert response.status_code == 200
    assert response.json()["id"] == str(product.id)


# ----------------------------------------------------------------------------- errors
async def test_unknown_but_valid_barcode_is_a_clean_404(client: httpx.AsyncClient) -> None:
    barcode = make_barcode()

    response = await client.get(f"/api/v1/products/by-barcode/{barcode}")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "urn:skincare:problem:product-not-found"
    assert body["title"] == "Product not found"
    assert barcode in body["detail"]
    assert body["instance"] == f"/api/v1/products/by-barcode/{barcode}"
    assert body["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize(
    "scanned",
    [
        "4006381333932",  # wrong check digit
        "40063813339",  # 11 digits
        "40063813339AB",  # letters
        "%20",  # blank
        "0",
    ],
)
async def test_malformed_barcode_is_a_422_invalid_barcode(
    client: httpx.AsyncClient, scanned: str
) -> None:
    response = await client.get(f"/api/v1/products/by-barcode/{scanned}")

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:skincare:problem:invalid-barcode"


async def test_unknown_product_id_is_a_404(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:skincare:problem:product-not-found"


async def test_a_malformed_product_id_is_a_validation_error(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/products/not-a-uuid")

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == "urn:skincare:problem:request-validation-failed"
    assert body["errors"][0]["loc"] == ["path", "product_id"]


# -------------------------------------------------------------------------- language
async def test_response_language_follows_accept_language(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    category = make_category(names={"en": "Moisturizer", "fr": "Hydratant"}, slug="moisturizer")
    paraben = make_ingredient(
        inci_name="PROPYLPARABEN",
        risk_level=RiskLevel.HIGH,
        rationale={"en": "Restricted preservative.", "fr": "Conservateur restreint."},
    )
    db_session.add_all([category, paraben])
    await db_session.flush()
    product = await add_product(
        db_session, [(1, "Propylparaben", paraben)], primary_category_id=category.id
    )
    url = f"/api/v1/products/{product.id}"

    french = await client.get(url, headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"})
    english = await client.get(url, headers={"Accept-Language": "en"})
    unsupported = await client.get(url, headers={"Accept-Language": "de"})
    absent = await client.get(url)

    assert french.json()["category"]["name"] == "Hydratant"
    assert french.json()["ingredients"][0]["rationale"] == "Conservateur restreint."
    assert french.headers["content-language"] == "fr"
    assert "accept-language" in french.headers["vary"].lower()
    for response in (english, unsupported, absent):
        assert response.json()["category"]["name"] == "Moisturizer"
        assert response.json()["ingredients"][0]["rationale"] == "Restricted preservative."
        assert response.headers["content-language"] == "en"


async def test_missing_french_text_falls_back_to_english_then_to_the_slug(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    english_only = make_category(names={"en": "Cleanser"}, slug="cleanser")
    untranslated = make_category(slug="sunscreen")
    db_session.add_all([english_only, untranslated])
    await db_session.flush()
    first = await add_product(db_session, primary_category_id=english_only.id)
    second = await add_product(db_session, primary_category_id=untranslated.id)
    headers = {"Accept-Language": "fr"}

    one = (await client.get(f"/api/v1/products/{first.id}", headers=headers)).json()
    two = (await client.get(f"/api/v1/products/{second.id}", headers=headers)).json()

    assert one["category"] == {"slug": "cleanser", "name": "Cleanser"}
    assert two["category"] == {"slug": "sunscreen", "name": "sunscreen"}


# ----------------------------------------------------------------------- performance
async def test_query_count_does_not_grow_with_the_number_of_ingredients(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """Guards against the N+1 problem: 3 ingredients or 30, the same number of queries."""
    category = make_category(names={"en": "Cream"})
    brand = make_brand()
    db_session.add_all([category, brand])
    ingredients = [make_ingredient() for _ in range(30)]
    db_session.add_all(ingredients)
    await db_session.flush()

    small = await add_product(
        db_session,
        [(i + 1, ing.inci_name, ing) for i, ing in enumerate(ingredients[:3])],
        brand_id=brand.id,
        primary_category_id=category.id,
    )
    large = await add_product(
        db_session,
        [(i + 1, ing.inci_name, ing) for i, ing in enumerate(ingredients)],
        brand_id=brand.id,
        primary_category_id=category.id,
    )

    statements: list[str] = []
    connection = db_session.sync_session.connection()

    def count(*args: object) -> None:
        statements.append("query")

    event.listen(connection, "before_cursor_execute", count)
    try:
        await client.get(f"/api/v1/products/{small.id}")
        queries_small = len(statements)
        statements.clear()
        await client.get(f"/api/v1/products/{large.id}")
        queries_large = len(statements)
    finally:
        event.remove(connection, "before_cursor_execute", count)

    assert queries_small == queries_large
    assert queries_large <= 6


# ------------------------------------------------------------------------ the OpenAPI
async def test_openapi_names_operations_and_documents_errors(client: httpx.AsyncClient) -> None:
    spec = (await client.get("/openapi.json")).json()

    operation = spec["paths"]["/api/v1/products/by-barcode/{barcode}"]["get"]
    assert operation["operationId"] == "products_get_product_by_barcode"
    assert {"200", "404", "422"} <= set(operation["responses"])
    assert spec["paths"]["/api/v1/products/{product_id}"]["get"]["operationId"] == (
        "products_get_product"
    )
    assert "ProblemDetails" in spec["components"]["schemas"]
    assert "ProductDetail" in spec["components"]["schemas"]

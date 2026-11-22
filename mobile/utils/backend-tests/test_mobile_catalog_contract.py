"""Regression tests for mobile-facing catalog card semantics; no database required."""
from datetime import UTC, datetime
import uuid

import pytest

from app.core.enums import RiskLevel
from app.modules.catalog.home_repository import ProductCardRow
from app.modules.catalog.home_service import _card
from app.modules.catalog.models import Product
from app.modules.catalog.search_service import _summary


@pytest.mark.parametrize("score,estimated", [(0, False), (92, True), (None, True)])
def test_home_card_preserves_estimated_and_zero(score: int | None, estimated: bool) -> None:
    row = ProductCardRow(
        id=uuid.uuid4(), name="Product", brand_name=None, image_url=None,
        score=score, score_band=RiskLevel.LOW, category_slug=None,
        created_at=datetime.now(UTC), score_is_estimated=estimated,
    )
    card = _card(row)
    assert card.score == score
    assert card.score_is_estimated is estimated
    assert card.image_url is None
    if score is None:
        assert card.score_band is None


def test_home_card_uses_requested_locale() -> None:
    row = ProductCardRow(
        id=uuid.uuid4(), name="Original", brand_name=None, image_url=None,
        score=80, score_band=RiskLevel.LOW, category_slug=None,
        created_at=datetime.now(UTC), name_i18n={"en": "Cleanser", "fr": "Nettoyant"},
    )
    assert _card(row, "fr").name == "Nettoyant"


def test_search_summary_preserves_locale_and_estimate() -> None:
    product = Product(id=uuid.uuid4(), name="Original", barcode="0079298300086",
        name_i18n={"en": "Cleanser", "fr": "Nettoyant"}, brand=None,
        primary_category=None, image_url=None, score=70,
        score_band=RiskLevel.MODERATE, score_is_estimated=True)
    result = _summary(product, "fr")
    assert result.name == "Nettoyant"
    assert result.score_is_estimated is True

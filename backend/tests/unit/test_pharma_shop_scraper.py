"""Unit tests for strict site_config loading, PrestaShop extraction, and Scoring v4 heuristics."""

import pytest

from app.core.enums import RiskLevel
from app.modules.ingestion.sources.scraper import (
    GenericScraperAdapter,
    ScraperConfigError,
    load_site_config,
)
from app.modules.scoring.engine import (
    SCORING_VERSION,
    IngredientScoreInput,
    calculate_score,
)

SAMPLE_PHARMA_SHOP_HTML = """
<!DOCTYPE html>
<html>
<head><title>SVR Sensifine Aqua-Gel 40ml</title></head>
<body>
  <nav class="breadcrumb">
    <ol><li><a><span>Accueil</span></a></li><li><a><span>Visage</span></a></li></ol>
  </nav>
  <h1 class="h1">SVR Sensifine Aqua-Gel 40ml</h1>
  <div id="product-details" data-product='{
    "id_product": 6711,
    "id_product_attribute": 0,
    "name": "SVR Sensifine Aqua-Gel 40ml",
    "manufacturer_name": "SVR",
    "ean13": "3662361001231",
    "reference": "SVR-6711",
    "price_amount": 54.9,
    "regular_price_amount": 61.0,
    "quantity": 12,
    "availability": "available",
    "cover": {"bySize": {"large_default": {"url": "https://pharma-shop.tn/6711-large_default/svr.jpg"}}},
    "images": [
      {"bySize": {"thickbox_default": {"url": "https://pharma-shop.tn/6711-thickbox/svr-front.jpg"}}},
      {"bySize": {"thickbox_default": {"url": "https://pharma-shop.tn/6711-thickbox/svr-back.jpg"}}}
    ]
  }'></div>
  <div id="description">
    <div class="product-description">
      <p><strong>Composition :</strong> AQUA/WATER/EAU, GLYCERIN, 1,2-HEXANEDIOL,
      ALOE BARBADENSIS LEAF JUICE POWDER, PANTHENOL,
      ACRYLATES/C10-30 ALKYL ACRYLATE CROSSPOLYMER, CAPRYLYL GLYCOL, SODIUM HYDROXIDE.</p>
      <p><strong>Conseils d'utilisation :</strong> Appliquer matin et soir.</p>
    </div>
  </div>
</body>
</html>
"""


def test_strict_load_site_config_raises_on_unknown() -> None:
    with pytest.raises(ScraperConfigError):
        load_site_config("non_existent_config_xyz")


def test_pharma_shop_extraction_complete() -> None:
    cfg = load_site_config("pharma_shop")
    adapter = GenericScraperAdapter(site_config=cfg)
    url = "https://pharma-shop.tn/visage/soins-hydratants/6711-svr-sensifine-aqua-gel-40ml-3662361001231.html"
    data = adapter.extract_from_html(url, SAMPLE_PHARMA_SHOP_HTML)

    assert data["barcode"] == "3662361001231"
    assert data["brand_name"] == "SVR"
    assert data["name"] == "SVR Sensifine Aqua-Gel 40ml"
    assert data["price_tnd"] == 54.9
    assert data["in_stock"] is True
    assert data["size_volume"] == "40ML"
    assert data["has_verified_inci"] is True
    assert "ACRYLATES/C10-30 ALKYL ACRYLATE CROSSPOLYMER" in data["raw_ingredients_text"]
    assert "Conseils d'utilisation" not in data["raw_ingredients_text"]
    assert len(data["gallery_image_urls"]) == 2


def test_scoring_v4_never_returns_unknown_or_null() -> None:
    assert SCORING_VERSION == 4
    empty_res = calculate_score([])
    assert empty_res.score == 50
    assert empty_res.band == RiskLevel.MODERATE
    assert empty_res.is_estimated is True

    single_res = calculate_score(
        [IngredientScoreInput(position=1, rating=None, confidence=0.0, functions=("emollient",))]
    )
    assert single_res.score == 70
    assert single_res.band == RiskLevel.MODERATE
    assert single_res.is_estimated is True

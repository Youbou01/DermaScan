from pathlib import Path

from app.modules.ingestion.sources.scraper import (
    GenericScraperAdapter,
    load_site_config,
    parse_sitemap_xml,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "html"


def test_parse_sitemap_xml() -> None:
    xml_text = (FIXTURES_DIR / "sample_sitemap.xml").read_text(encoding="utf-8")

    # All URLs
    all_urls = parse_sitemap_xml(xml_text)
    assert len(all_urls) == 3
    assert "https://example-parapharmacie.tn/contact" in all_urls

    # Filtered by pattern
    prod_urls = parse_sitemap_xml(xml_text, pattern="/produit/")
    assert len(prod_urls) == 2
    assert all("/produit/" in u for u in prod_urls)


def test_scraper_extract_jsonld() -> None:
    html = (FIXTURES_DIR / "sample_product_jsonld.html").read_text(encoding="utf-8")
    adapter = GenericScraperAdapter()
    data = adapter.extract(html, url="https://example.com/product/123")

    assert data["name"] == "Hydrating Hyaluronic Serum"
    assert data["brand_name"] == "L'Oreal"
    assert data["barcode"] == "3600523823123"
    assert data["image_url"] == "https://example.com/images/serum.webp"
    assert "Aqua" in (data["raw_ingredients_text"] or "")

    raw = adapter.to_raw(data, url="https://example.com/product/123")
    assert raw.source == "scrape"
    assert raw.source_id == "3600523823123"
    assert len(raw.content_hash) == 64


def test_scraper_extract_selectors_tunisian() -> None:
    html = (FIXTURES_DIR / "sample_product_selectors.html").read_text(encoding="utf-8")
    config = load_site_config("tunisian_parapharmacy")
    adapter = GenericScraperAdapter()
    data = adapter.extract(
        html, url="https://example-parapharmacie.tn/produit/creme", config=config
    )

    assert data["name"] == "Crème Hydratante Apaisante"
    assert data["brand_name"] == "SVR"
    assert data["barcode"] == "6191234567890"
    assert "media/creme-svr.jpg" in (data["image_url"] or "")
    assert "Caprylic/Capric Triglyceride" in (data["raw_ingredients_text"] or "")
    assert data["source_lang"] == "fr"

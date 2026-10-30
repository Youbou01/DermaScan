"""Generic web scraping source adapter extracting JSON-LD, CSS selectors, and text."""

import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import extruct  # type: ignore[import-untyped]
import httpx
import structlog
import yaml
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog import normalize_gtin
from app.modules.ingestion.enums import RawProductSource
from app.modules.ingestion.sources.base import (
    RawRecord,
    SourceAdapter,
    compute_content_hash,
)

logger = structlog.get_logger(__name__)

SITES_DIR = Path(__file__).parent / "sites"


class SiteSelectors(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "h1.product-title, h1.product_title, h1"
    brand: str = ".product-brand, .brand, [itemprop='brand']"
    barcode: str = "[itemprop='gtin13'], [itemprop='sku'], .barcode, .sku"
    ingredients: str = ".ingredients-content, #ingredients, .product-ingredients, .ingredients"
    image: str = "meta[property='og:image'], .product-image img, .gallery-item img"
    category: str = ".breadcrumb, .product-category"


class SiteConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "default"
    base_url: str = ""
    user_agent: str = "Mozilla/5.0 (compatible; DermaScanBot/1.0; +https://dermascan.org/bot)"
    rate_limit_rps: float = 1.0
    respect_robots: bool = False
    selectors: SiteSelectors = Field(default_factory=SiteSelectors)


def load_site_config(site_name: str | None = None) -> SiteConfig:
    name = site_name or "default"
    config_file = SITES_DIR / f"{name}.yaml"
    if not config_file.exists():
        config_file = SITES_DIR / "default.yaml"
    if not config_file.exists():
        return SiteConfig()

    try:
        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                return SiteConfig(**data)
    except Exception as exc:
        logger.warning("site_config_load_error", name=name, error=str(exc))

    return SiteConfig()


def parse_sitemap_xml(xml_content: str, pattern: str | None = None, limit: int = 500) -> list[str]:
    """Parse XML sitemap (standard urlset or sitemapindex) and return URLs."""
    urls: list[str] = []
    try:
        root = ET.fromstring(xml_content)  # noqa: S314
        # Handle namespaces cleanly by matching any tag ending with 'loc'
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "loc" and elem.text:
                url = elem.text.strip()
                if pattern is None or pattern in url:
                    urls.append(url)
                if len(urls) >= limit:
                    break
    except Exception as exc:
        logger.warning("sitemap_parse_error", error=str(exc))
    return urls


class GenericScraperAdapter(SourceAdapter):
    """Generic web scraper adapter extracting product data from public websites."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._client = client
        self._timeout = timeout

    @property
    def source_name(self) -> str:
        return RawProductSource.SCRAPE.value

    async def fetch(
        self, source_id: str, config: SiteConfig | None = None
    ) -> dict[str, Any] | None:
        """Fetch URL and extract structured data."""
        url = source_id
        cfg = config or load_site_config()
        headers = {"User-Agent": cfg.user_agent}

        try:
            if self._client:
                res = await self._client.get(
                    url, headers=headers, timeout=self._timeout, follow_redirects=True
                )
            else:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        url, headers=headers, timeout=self._timeout, follow_redirects=True
                    )
            if res.status_code != 200:
                logger.warning("scraper_http_error", url=url, status_code=res.status_code)
                return None
            return self.extract(res.text, url=url, config=cfg)
        except Exception as exc:
            logger.error("scraper_fetch_error", url=url, error=str(exc))
            return None

    async def discover(self, dump_path: Path | str | None = None) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}

    def extract(self, html: str, url: str, config: SiteConfig | None = None) -> dict[str, Any]:
        """Extract structured product data using JSON-LD -> CSS Selectors -> Text fallback."""
        cfg = config or load_site_config()
        extracted: dict[str, Any] = {
            "url": url,
            "barcode": None,
            "name": None,
            "brand_name": None,
            "category_slug": None,
            "raw_ingredients_text": None,
            "image_url": None,
            "source_lang": "fr" if ".tn" in url or "/fr" in url else "en",
        }

        # 1. JSON-LD via extruct
        json_ld_prod = self._extract_jsonld(html, url)
        if json_ld_prod:
            self._populate_from_jsonld(extracted, json_ld_prod, url)

        # 2. Fallback CSS selectors
        soup = BeautifulSoup(html, "lxml")
        self._populate_from_selectors(extracted, soup, cfg.selectors, url)

        # 3. Fallback readable text for ingredients if missing
        if not extracted.get("raw_ingredients_text"):
            extracted["raw_ingredients_text"] = self._extract_ingredients_from_text(soup)

        return extracted

    def _extract_jsonld(self, html: str, url: str) -> dict[str, Any] | None:
        try:
            data = extruct.extract(html, base_url=url, syntaxes=["json-ld"])
            json_ld_list = data.get("json-ld", [])
            for block in json_ld_list:
                if isinstance(block, dict):
                    graph = block.get("@graph")
                    candidates = graph if isinstance(graph, list) else [block]
                    for item in candidates:
                        if not isinstance(item, dict):
                            continue
                        item_type = item.get("@type")
                        is_prod = (isinstance(item_type, str) and "Product" in item_type) or (
                            isinstance(item_type, list)
                            and any("Product" in str(t) for t in item_type)
                        )
                        if is_prod:
                            return item
        except Exception as exc:
            logger.debug("extruct_jsonld_error", url=url, error=str(exc))
        return None

    def _populate_from_jsonld(
        self, target: dict[str, Any], json_ld: dict[str, Any], base_url: str
    ) -> None:
        if not target.get("name") and json_ld.get("name"):
            target["name"] = str(json_ld["name"]).strip()

        if not target.get("brand_name"):
            brand_val = json_ld.get("brand")
            if isinstance(brand_val, dict):
                target["brand_name"] = brand_val.get("name")
            elif isinstance(brand_val, str):
                target["brand_name"] = brand_val.strip()

        if not target.get("barcode"):
            for key in ["gtin13", "gtin14", "gtin8", "gtin", "sku", "productID"]:
                val = json_ld.get(key)
                if val:
                    try:
                        norm = normalize_gtin(str(val))
                        target["barcode"] = norm
                        break
                    except Exception:
                        if not target.get("barcode"):
                            target["barcode"] = str(val).strip()

        if not target.get("image_url"):
            img = json_ld.get("image")
            if isinstance(img, list) and img:
                first = img[0]
                target["image_url"] = (
                    first.get("url") if isinstance(first, dict) else str(first).strip()
                )
            elif isinstance(img, dict):
                target["image_url"] = img.get("url") or img.get("contentUrl")
            elif isinstance(img, str):
                target["image_url"] = img.strip()

        if not target.get("category_slug") and json_ld.get("category"):
            target["category_slug"] = str(json_ld["category"]).strip()

        if not target.get("raw_ingredients_text"):
            # Check for ingredients in description or custom fields
            desc = json_ld.get("description")
            if desc and ("aqua" in desc.lower() or "ingredients:" in desc.lower()):
                target["raw_ingredients_text"] = str(desc).strip()

    def _populate_from_selectors(
        self,
        target: dict[str, Any],
        soup: BeautifulSoup,
        selectors: SiteSelectors,
        base_url: str,
    ) -> None:
        if not target.get("name") and selectors.name:
            el = soup.select_one(selectors.name)
            if el:
                target["name"] = el.get_text(strip=True)

        if not target.get("brand_name") and selectors.brand:
            el = soup.select_one(selectors.brand)
            if el:
                target["brand_name"] = el.get_text(strip=True)

        if not target.get("barcode") and selectors.barcode:
            el = soup.select_one(selectors.barcode)
            if el:
                raw_bc = el.get_text(strip=True)
                try:
                    target["barcode"] = normalize_gtin(raw_bc)
                except Exception:
                    target["barcode"] = raw_bc

        if not target.get("raw_ingredients_text") and selectors.ingredients:
            el = soup.select_one(selectors.ingredients)
            if el:
                target["raw_ingredients_text"] = el.get_text(strip=True)

        if not target.get("image_url") and selectors.image:
            el = soup.select_one(selectors.image)
            if el:
                img_src = el.get("content") or el.get("src") or el.get("data-src")
                if isinstance(img_src, str) and img_src.strip():
                    target["image_url"] = urllib.parse.urljoin(base_url, img_src.strip())

        if not target.get("category_slug") and selectors.category:
            el = soup.select_one(selectors.category)
            if el:
                target["category_slug"] = el.get_text(strip=True)

    def _extract_ingredients_from_text(self, soup: BeautifulSoup) -> str | None:
        text = soup.get_text(separator="\n", strip=True)
        patterns = [
            r"(?i)(?:ingr[ée]dients|composition|inci)\s*[:\-]\s*([^\n\r]+(?:\n[^\n\r]+){0,5})",
            r"(?i)(aqua\s*(?:/[a-z\s]+)?,[^\.\n]+)",
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                return match.group(1).strip()
        return None

    def to_raw(self, payload: dict[str, Any], url: str | None = None) -> RawRecord:
        source_id = str(payload.get("barcode") or payload.get("url") or url or "unknown").strip()
        content_hash = compute_content_hash(payload)
        return RawRecord(
            source=self.source_name,
            source_id=source_id,
            content_hash=content_hash,
            payload=payload,
            url=url or payload.get("url"),
        )

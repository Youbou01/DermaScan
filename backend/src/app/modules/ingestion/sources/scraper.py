"""Declarative and high-throughput web scraper adapter (PrestaShop, JSON-LD, CSS, Playwright)."""

import asyncio
import hashlib
import html as html_lib
import json
import random
import re
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import extruct  # type: ignore[import-untyped]
import httpx
import structlog
import yaml
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.modules.catalog import normalize_gtin
from app.modules.ingestion.enums import RawProductSource
from app.modules.ingestion.sources.base import (
    RawRecord,
    SourceAdapter,
    compute_content_hash,
)

logger = structlog.get_logger(__name__)

SITES_DIR = Path(__file__).resolve().parent / "sites"


class ScraperConfigError(ValueError):
    """Raised when a requested site_config does not exist or has invalid YAML."""


class ScraperFetchError(RuntimeError):
    """Raised when an HTTP fetch fails or returns non-200 so the job queue retries."""


class SiteSelectors(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = "h1.product-title, h1.product_title, h1"
    brand: str = ".product-brand, .brand, [itemprop='brand']"
    barcode: str = "[itemprop='gtin13'], [itemprop='sku'], .barcode, .sku"
    ingredients: str = ".ingredients-content, #ingredients, .product-ingredients, .ingredients"
    image: str = "meta[property='og:image'], .product-image img, .gallery-item img"
    gallery_images: str = ".product-images img, .thumb-container img"
    category: str = ".breadcrumb, .product-category"
    price: str = ".current-price span[itemprop='price'], .product-price, [itemprop='price']"
    availability: str = "#product-availability, [itemprop='availability']"
    reference: str = ".product-reference span, [itemprop='sku']"


class SiteConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = "default"
    base_url: str = ""
    user_agent: str = "Mozilla/5.0 (compatible; DermaScanBot/1.0; +https://dermascan.org/bot)"
    rate_limit_rps: float = Field(default=10.0, gt=0.0)
    concurrency: int = Field(default=15, ge=1, le=100)
    timeout_seconds: float = Field(default=25.0, gt=0.0)
    respect_robots: bool = False
    render_js: bool = False
    url_pattern: str | None = None
    seed_paths: list[str] = Field(default_factory=list)
    sitemap_urls: list[str] = Field(default_factory=list)
    selectors: SiteSelectors = Field(default_factory=SiteSelectors)


def load_site_config(site_name: str | None = None) -> SiteConfig:
    """Strictly load per-site YAML config into a SiteConfig Pydantic model."""
    clean_name = (site_name or "default").strip()
    if clean_name.endswith((".yaml", ".yml")):
        clean_name = Path(clean_name).stem

    path = SITES_DIR / f"{clean_name}.yaml"
    if not path.exists():
        if site_name is None:
            return SiteConfig()
        available = sorted(p.stem for p in SITES_DIR.glob("*.yaml"))
        raise ScraperConfigError(
            f"Site config '{clean_name}' not found at {path}. Available: {available}"
        )

    try:
        raw_text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ScraperConfigError(f"Invalid YAML syntax in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ScraperConfigError(f"YAML config in {path} must be a mapping/dictionary.")

    if isinstance(data.get("selectors"), dict) and "image_url" in data["selectors"]:
        data["selectors"] = dict(data["selectors"])
        data["selectors"].setdefault("image", data["selectors"].pop("image_url"))

    return SiteConfig.model_validate(data)


def canonicalize_url(url: str) -> str:
    """Strip tracking query params, fragments, and trailing slashes for deduplication."""
    parsed = urlparse(url.strip())
    clean_path = re.sub(r"/+$", "", parsed.path) or "/"
    return urlunparse(
        (parsed.scheme.lower() or "https", parsed.netloc.lower(), clean_path, "", "", "")
    )


def parse_sitemap_xml(
    xml_content: str,
    pattern: str | None = None,
    limit: int | None = 500,
) -> list[str]:
    """Parse XML sitemap and return matching URLs."""
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml_content, flags=re.IGNORECASE)
    compiled = re.compile(pattern, re.IGNORECASE) if pattern else None
    urls: list[str] = []
    seen: set[str] = set()
    for loc in locs:
        clean = html_lib.unescape(loc).strip()
        if pattern and not (pattern in clean or (compiled and compiled.search(clean))):
            continue
        if clean not in seen:
            seen.add(clean)
            urls.append(clean)
            if limit is not None and len(urls) >= limit:
                break
    return urls


_SIZE_VOLUME_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?\s*(?:ml|g|gr|l|oz|fl\.?\s*oz|gélules|capsules|ampoules|comprimés))\b",
    re.IGNORECASE,
)
_INCI_COMPOSITION_RE = re.compile(
    r"(?:Composition\s*(?:INCI)?|Ingr[ée]dients\s*(?:\(INCI\))?|Formule\s*(?:INCI)?|Liste\s+INCI)\s*[:.\-\u2013]?\s*"
    r"(?:</?(?:strong|b|u|span|p|div|h\d)[^>]*>\s*)*"
    r"([^<]{15,4000})",
    re.IGNORECASE,
)
_REAL_INCI_MARKERS = re.compile(
    r"\b(aqua|water|eau|glycerin|glycérine|cetearyl|tocopherol|niacinamide|caprylic|dimethicone|"
    r"sodium|citric acid|parfum|fragrance|xanthan gum|propanediol|butylene glycol|panthenol|"
    r"titanium dioxide|butyrospermum parkii|alcohol|phenoxyethanol|sorbitol|lecithin|squalane)\b",
    re.IGNORECASE,
)


def extract_prestashop_full_payload(url: str, html: str, soup: BeautifulSoup) -> dict[str, Any]:
    """Deep extractor for PrestaShop 1.7/8 product pages (pharma-shop.tn and similar)."""
    out: dict[str, Any] = {}

    url_ean = re.search(r"-(\d{8,14})\.html(?:\?.*)?$", url)
    if url_ean:
        raw_bc = url_ean.group(1)
        try:
            out["barcode"] = normalize_gtin(raw_bc)
        except Exception:
            out["barcode"] = raw_bc

    url_pid = re.search(r"/(\d+)-[a-z0-9-]+", urlparse(url).path, re.IGNORECASE)
    if url_pid:
        out["prestashop_product_id"] = int(url_pid.group(1))

    details_node = soup.select_one("#product-details[data-product], [data-product]")
    if details_node and details_node.has_attr("data-product"):
        raw_attr = str(details_node["data-product"])
        try:
            ps = json.loads(html_lib.unescape(raw_attr))
            if isinstance(ps, dict):
                out["prestashop_product_id"] = ps.get("id_product") or out.get(
                    "prestashop_product_id"
                )
                out["id_product_attribute"] = ps.get("id_product_attribute")
                ean13 = str(ps.get("ean13") or "").strip()
                if re.fullmatch(r"\d{8,14}", ean13):
                    try:
                        out["barcode"] = normalize_gtin(ean13)
                    except Exception:
                        out["barcode"] = ean13
                if ps.get("name"):
                    out["name"] = str(ps["name"]).strip()
                if ps.get("manufacturer_name"):
                    out["brand_name"] = str(ps["manufacturer_name"]).strip()
                if ps.get("reference"):
                    out["sku_reference"] = str(ps["reference"]).strip()
                if ps.get("category_name"):
                    out["category_slug"] = str(ps["category_name"]).strip()
                if ps.get("price_amount") is not None:
                    out["price_tnd"] = float(ps["price_amount"])
                if ps.get("regular_price_amount") is not None:
                    out["regular_price_tnd"] = float(ps["regular_price_amount"])
                if ps.get("discount_percentage"):
                    out["discount_percentage"] = str(ps["discount_percentage"])
                out["currency"] = "TND"
                out["quantity_available"] = ps.get("quantity")
                out["availability"] = ps.get("availability")
                out["in_stock"] = ps.get("availability") == "available" or (
                    isinstance(ps.get("quantity"), int) and ps["quantity"] > 0
                )

                gallery: list[str] = []
                images_list = ps.get("images")
                if isinstance(images_list, list):
                    for img_obj in images_list:
                        if isinstance(img_obj, dict):
                            by_size = img_obj.get("bySize") or {}
                            for sz in (
                                "thickbox_default",
                                "large_default",
                                "medium_default",
                                "home_default",
                            ):
                                if isinstance(by_size.get(sz), dict) and by_size[sz].get("url"):
                                    gallery.append(str(by_size[sz]["url"]))
                                    break
                cover = ps.get("cover")
                if isinstance(cover, dict):
                    by_size = cover.get("bySize") or {}
                    for sz in (
                        "thickbox_default",
                        "large_default",
                        "medium_default",
                        "home_default",
                    ):
                        if isinstance(by_size.get(sz), dict) and by_size[sz].get("url"):
                            out["image_url"] = str(by_size[sz]["url"])
                            break
                if gallery:
                    out["gallery_image_urls"] = list(dict.fromkeys(gallery))
                    out.setdefault("image_url", gallery[0])

                if isinstance(ps.get("features"), list):
                    out["features"] = {
                        str(f.get("name", "")).strip(): str(f.get("value", "")).strip()
                        for f in ps["features"]
                        if isinstance(f, dict) and f.get("name")
                    }
                if isinstance(ps.get("attributes"), dict):
                    out["attributes"] = ps["attributes"]

                desc_html = str(ps.get("description") or "")
                short_html = str(ps.get("description_short") or "")
                if desc_html or short_html:
                    out["description_text"] = BeautifulSoup(
                        f"{short_html}\n{desc_html}", "html.parser"
                    ).get_text(" ", strip=True)
        except json.JSONDecodeError, TypeError, ValueError:
            pass

    breadcrumbs = [
        a.get_text(" ", strip=True)
        for a in soup.select(".breadcrumb li a span, .breadcrumb li a, .breadcrumb a")
        if a.get_text(" ", strip=True)
    ]
    if breadcrumbs:
        dedup_crumbs = list(dict.fromkeys(breadcrumbs))
        out["category_breadcrumb"] = dedup_crumbs
        if len(dedup_crumbs) >= 2 and not out.get("category_slug"):
            out["category_slug"] = dedup_crumbs[-1]

    desc_container = soup.select_one(
        "#description .product-description, #description, [itemprop='description']"
    )
    desc_raw_html = str(desc_container) if desc_container else html
    comp_match = _INCI_COMPOSITION_RE.search(desc_raw_html)
    if comp_match:
        candidate = html_lib.unescape(re.sub(r"<[^>]+>", " ", comp_match.group(1)))
        candidate = re.sub(r"\s+", " ", candidate).strip()
        candidate = re.split(
            r"\b(?:Conseils?\s+d['\u2019]utilisation|Mode\s+d['\u2019]emploi|"
            r"Comment\s+utiliser|Pr[ée]cautions\s+d['\u2019]emploi)\b",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" :.-•")
        if len(_REAL_INCI_MARKERS.findall(candidate)) >= 2 and (
            "," in candidate or "•" in candidate or "/" in candidate
        ):
            out["raw_ingredients_text"] = candidate
            out["has_verified_inci"] = True
        else:
            out["marketing_ingredients_note"] = candidate
            out["has_verified_inci"] = False

    if not out.get("raw_ingredients_text") and desc_container:
        for p_tag in desc_container.find_all(["p", "div", "span"]):
            p_txt = p_tag.get_text(" ", strip=True)
            if (
                p_txt.count(",") >= 4
                and len(_REAL_INCI_MARKERS.findall(p_txt)) >= 3
                and len(p_txt) < 3500
            ):
                out["raw_ingredients_text"] = p_txt
                out["has_verified_inci"] = True
                break

    title_for_size = str(out.get("name") or "")
    sz_match = _SIZE_VOLUME_RE.search(title_for_size)
    if sz_match:
        out["size_volume"] = sz_match.group(1).upper()

    return out


class GenericScraperAdapter(SourceAdapter):
    """Full-featured web scraper adapter supporting discovery, PrestaShop XHR,
    JSON-LD, CSS, and Playwright.
    """

    def __init__(
        self,
        site_config: SiteConfig | str | httpx.AsyncClient | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 25.0,
    ) -> None:
        if isinstance(site_config, httpx.AsyncClient):
            client = site_config
            site_config = None
        if isinstance(site_config, SiteConfig):
            self.config = site_config
        else:
            self.config = load_site_config(site_config)
        self._client = client
        self._timeout = timeout
        self._proxy_clients: dict[str | None, httpx.AsyncClient] = (
            {None: client} if client is not None else {}
        )
        self._robot_parsers: dict[str, RobotFileParser | None] = {}
        self._settings = get_settings()
        self._last_request_ts = 0.0
        self._rate_lock = asyncio.Lock()

    @property
    def source_name(self) -> str:
        return RawProductSource.SCRAPE.value

    def _pick_user_agent(self, cfg: SiteConfig) -> str:
        raw_uas = self._settings.scraper_user_agents
        if raw_uas and "|" in raw_uas:
            choices = [u.strip() for u in raw_uas.split("|") if u.strip()]
            if choices:
                return random.choice(choices)  # noqa: S311
        return cfg.user_agent

    def _pick_proxy(self) -> str | None:
        raw_proxies = self._settings.scraper_proxy_list
        if raw_proxies:
            choices = [p.strip() for p in raw_proxies.split(",") if p.strip()]
            if choices:
                return random.choice(choices)  # noqa: S311
        return None

    async def _check_robots_allowed(self, url: str, user_agent: str, cfg: SiteConfig) -> bool:
        if not (cfg.respect_robots or self._settings.scraper_respect_robots):
            return True
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robot_parsers:
            robots_url = f"{origin}/robots.txt"
            rp = RobotFileParser()
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as cli:
                    resp = await cli.get(robots_url)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                        self._robot_parsers[origin] = rp
                    else:
                        self._robot_parsers[origin] = None
            except httpx.HTTPError:
                self._robot_parsers[origin] = None
        parser = self._robot_parsers.get(origin)
        return True if parser is None else parser.can_fetch(user_agent, url)

    async def _throttle(self, cfg: SiteConfig) -> None:
        min_interval = 1.0 / max(0.1, cfg.rate_limit_rps)
        async with self._rate_lock:
            now = time.monotonic()
            wait = min_interval - (now - self._last_request_ts)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_ts = time.monotonic()

    async def fetch_html(
        self,
        url: str,
        config: SiteConfig | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        cfg = config or self.config
        ua = self._pick_user_agent(cfg)
        if not await self._check_robots_allowed(url, ua, cfg):
            raise ScraperFetchError(f"Blocked by robots.txt: {url}")

        await self._throttle(cfg)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-TN,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            **(extra_headers or {}),
        }
        proxy = self._pick_proxy()

        if not cfg.render_js:
            cli = self._proxy_clients.get(proxy)
            owns_client = False
            if cli is None:
                cli = httpx.AsyncClient(
                    timeout=cfg.timeout_seconds,
                    follow_redirects=True,
                    proxy=proxy,
                )
                if self._client is not None:
                    self._proxy_clients[proxy] = cli
                else:
                    owns_client = True
            try:
                resp = await cli.get(url, headers=headers)
                if resp.status_code != 200:
                    raise ScraperFetchError(f"HTTP {resp.status_code} fetching {url}")
                text = resp.text
            except httpx.HTTPError as exc:
                raise ScraperFetchError(
                    f"HTTP error fetching {url}: {type(exc).__name__}: {exc!r}"
                ) from exc
            finally:
                if owns_client:
                    await cli.aclose()

            if len(text.strip()) > 200 or not cfg.render_js:
                return text

        try:
            from playwright.async_api import async_playwright  # type: ignore[import-not-found]

            async with async_playwright() as p:
                launch_kwargs: dict[str, Any] = {"headless": True}
                if proxy:
                    launch_kwargs["proxy"] = {"server": proxy}
                browser = await p.chromium.launch(**launch_kwargs)
                try:
                    page = await browser.new_page(user_agent=headers["User-Agent"])
                    resp = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=int(cfg.timeout_seconds * 1000),
                    )
                    if resp is not None and resp.status >= 400:
                        raise ScraperFetchError(f"Playwright HTTP {resp.status} fetching {url}")
                    return str(await page.content())
                finally:
                    await browser.close()
        except ImportError as exc:
            raise ScraperFetchError(
                f"Page {url} requires Playwright JS rendering, which is not installed."
            ) from exc

    def extract(self, html: str, url: str, config: SiteConfig | None = None) -> dict[str, Any]:
        """Extract structured product data using JSON-LD -> PrestaShop data-product
        -> CSS Selectors -> Text.
        """
        cfg = config or self.config
        extracted: dict[str, Any] = {
            "url": url,
            "source_site": cfg.name,
            "barcode": None,
            "name": None,
            "brand_name": None,
            "category_slug": None,
            "raw_ingredients_text": None,
            "image_url": None,
            "source_lang": "fr" if ".tn" in url or "/fr" in url else "en",
        }

        json_ld_prod = self._extract_jsonld(html, url)
        if json_ld_prod:
            self._populate_from_jsonld(extracted, json_ld_prod, url)

        soup = BeautifulSoup(html, "lxml")
        ps_data = extract_prestashop_full_payload(url, html, soup)
        for k, v in ps_data.items():
            if v is not None and v != "":
                extracted[k] = v

        self._populate_from_selectors(extracted, soup, cfg.selectors, url)

        if not extracted.get("raw_ingredients_text"):
            extracted["raw_ingredients_text"] = self._extract_ingredients_from_text(soup)

        if extracted.get("brand_name") and not extracted.get("brand"):
            extracted["brand"] = extracted["brand_name"]
        elif extracted.get("brand") and not extracted.get("brand_name"):
            extracted["brand_name"] = extracted["brand"]

        return extracted

    def extract_from_html(
        self, url: str, html: str, config: SiteConfig | None = None
    ) -> dict[str, Any]:
        return self.extract(html, url=url, config=config)

    def _extract_jsonld(self, html: str, url: str) -> dict[str, Any] | None:
        try:
            data = extruct.extract(html, base_url=url, syntaxes=["json-ld"])
            json_ld_list = data.get("json-ld", [])
            for block in json_ld_list:
                candidates: list[Any] = []
                if isinstance(block, dict):
                    graph = block.get("@graph")
                    candidates = graph if isinstance(graph, list) else [block]
                elif isinstance(block, list):
                    candidates = block
                for item in candidates:
                    if not isinstance(item, dict):
                        continue
                    item_type = item.get("@type")
                    is_prod = (isinstance(item_type, str) and "Product" in item_type) or (
                        isinstance(item_type, list) and any("Product" in str(t) for t in item_type)
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
                        target["barcode"] = normalize_gtin(str(val))
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
                target["brand_name"] = el.get("alt") or el.get("content") or el.get_text(strip=True)

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
                txt = el.get_text(" ", strip=True)
                if len(_REAL_INCI_MARKERS.findall(txt)) >= 2 or "aqua" in txt.lower():
                    target["raw_ingredients_text"] = txt

        if not target.get("image_url") and selectors.image:
            el = soup.select_one(selectors.image)
            if el:
                img_src = el.get("content") or el.get("src") or el.get("data-src")
                if isinstance(img_src, str) and img_src.strip():
                    target["image_url"] = urljoin(base_url, img_src.strip())

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

    async def fetch(self, source_id: str, config: SiteConfig | None = None) -> dict[str, Any]:
        """Fetch URL and extract structured product dictionary.
        Raises ScraperFetchError on failure.
        """
        cfg = config or self.config
        html = await self.fetch_html(source_id, config=cfg)
        extracted = self.extract(html, url=source_id, config=cfg)
        if not (extracted.get("name") or extracted.get("barcode")):
            raise ScraperFetchError(f"Failed to extract product data from {source_id}")
        return extracted

    def to_raw(self, payload: dict[str, Any], url: str | None = None) -> RawRecord:
        target_url = str(url or payload.get("url") or "")
        source_id = str(
            payload.get("barcode")
            or payload.get("prestashop_product_id")
            or payload.get("url")
            or url
            or hashlib.sha256(canonicalize_url(target_url).encode("utf-8")).hexdigest()[:16]
        ).strip()
        content_hash = compute_content_hash(payload)
        return RawRecord(
            source=self.source_name,
            source_id=source_id,
            content_hash=content_hash,
            payload=payload,
            url=target_url or None,
        )

    async def discover(
        self,
        dump_path: Path | str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[str]:
        """Multi-vector URL discovery (sitemaps + homepage category/brand
        auto-discovery + XHR pagination).
        """
        seen_products: set[str] = set()
        yielded = 0
        url_regex = re.compile(
            self.config.url_pattern or r"https?://[^\"'\s>]+/\d+-[a-z0-9-]+(?:-\d{8,14})?\.html",
            re.IGNORECASE,
        )

        for sm_url in self.config.sitemap_urls:
            try:
                xml_text = await self.fetch_html(sm_url)
                for loc in parse_sitemap_xml(
                    xml_text, pattern=self.config.url_pattern, limit=limit
                ):
                    canon = canonicalize_url(loc)
                    if canon not in seen_products:
                        seen_products.add(canon)
                        yield canon
                        yielded += 1
                        if limit and yielded >= limit:
                            return
            except ScraperFetchError:
                logger.info("sitemap_unavailable_falling_back_to_crawl", sitemap=sm_url)

        listing_queue: list[str] = [
            urljoin(self.config.base_url, p) for p in self.config.seed_paths
        ]
        seen_listings: set[str] = set(listing_queue)

        if self.config.base_url:
            try:
                home_html = await self.fetch_html(self.config.base_url)
                for m in re.findall(r'href=["\'](https?://[^"\']+|/[^"\']+)["\']', home_html):
                    full = canonicalize_url(urljoin(self.config.base_url, m))
                    if not full.startswith(self.config.base_url):
                        continue
                    if url_regex.search(full):
                        if full not in seen_products:
                            seen_products.add(full)
                            yield full
                            yielded += 1
                            if limit and yielded >= limit:
                                return
                    elif full not in seen_listings and re.search(
                        r"/(\d+-[a-z0-9-]+|\d+_[a-z0-9-]+|nouveaux-produits|promotions|meilleures-ventes)$",
                        full,
                        re.I,
                    ):
                        seen_listings.add(full)
                        listing_queue.append(full)
            except ScraperFetchError as exc:
                logger.warning("homepage_discovery_error", error=str(exc))

        idx = 0
        while idx < len(listing_queue):
            base_listing_url = listing_queue[idx]
            idx += 1
            page = 1
            max_page_known: int | None = None

            while max_page_known is None or page <= max_page_known:
                sep = "&" if "?" in base_listing_url else "?"
                page_url = f"{base_listing_url}{sep}page={page}" if page > 1 else base_listing_url
                xhr_url = f"{page_url}{'&' if '?' in page_url else '?'}from-xhr"

                new_on_page = 0
                try:
                    raw_resp = await self.fetch_html(
                        xhr_url,
                        extra_headers={
                            "Accept": "application/json, text/javascript, */*; q=0.01",
                            "X-Requested-With": "XMLHttpRequest",
                        },
                    )
                except ScraperFetchError:
                    break

                try:
                    xhr_data = json.loads(raw_resp)
                    if isinstance(xhr_data, dict):
                        pag = xhr_data.get("pagination") or {}
                        if isinstance(pag.get("pages_count"), int):
                            max_page_known = int(pag["pages_count"])
                        for prod in xhr_data.get("products") or []:
                            if isinstance(prod, dict) and prod.get("url"):
                                canon_p = canonicalize_url(str(prod["url"]))
                                if canon_p not in seen_products:
                                    seen_products.add(canon_p)
                                    new_on_page += 1
                                    yield canon_p
                                    yielded += 1
                                    if limit and yielded >= limit:
                                        return
                        rendered = str(xhr_data.get("rendered_products") or "")
                        raw_resp = rendered if rendered else raw_resp
                except ValueError:
                    pass

                for m in re.findall(r'href=["\'](https?://[^"\']+|/[^"\']+)["\']', raw_resp):
                    full = canonicalize_url(urljoin(self.config.base_url, m))
                    if not full.startswith(self.config.base_url):
                        continue
                    if url_regex.search(full):
                        if full not in seen_products:
                            seen_products.add(full)
                            new_on_page += 1
                            yield full
                            yielded += 1
                            if limit and yielded >= limit:
                                return
                    elif (
                        page == 1
                        and full not in seen_listings
                        and re.search(r"/(\d+-[a-z0-9-]+|\d+_[a-z0-9-]+)$", full, re.I)
                    ):
                        seen_listings.add(full)
                        listing_queue.append(full)

                if new_on_page == 0:
                    break
                page += 1

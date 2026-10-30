"""DermaScan backend load testing suite using Locust.

Targeted scenarios:
- Browsing home feed shelves (keyset pagination)
- Browsing category trees
- Searching products (trigram full-text search)
- Fetching product details by barcode
- Conditional GET caching with ETag / 304 Not Modified
"""

import secrets

from locust import HttpUser, between, task

SAMPLE_BARCODES = [
    "3337875597203",  # CeraVe Hydrating Cleanser
    "3337872412493",  # La Roche-Posay Toleriane
    "3600523959823",  # L'Oreal Revitalift
    "3508240003326",  # Bioderma Sensibio H2O
    "3337875597173",  # CeraVe Foaming Cleanser
]

SEARCH_QUERIES = [
    "cleanser",
    "moisturizer",
    "serum",
    "retinol",
    "cerave",
    "sunscreen",
    "spf",
    "hyaluronic",
    "niacinamide",
    "creme",
    "lotion",
]


class DermaScanUser(HttpUser):
    """Simulates a mobile app user browsing the catalog and scanning barcodes."""

    # Realistic thinking time between app interactions
    wait_time = between(0.05, 0.2)

    def on_start(self) -> None:
        self.cached_etags: dict[str, str] = {}

    @task(4)
    def browse_home(self) -> None:
        """Fetch home feed shelves."""
        path = "/api/v1/home"
        headers = {}
        if path in self.cached_etags:
            headers["If-None-Match"] = self.cached_etags[path]

        with self.client.get(
            path, headers=headers, name="/api/v1/home", catch_response=True
        ) as res:
            if res.status_code in (200, 304):
                res.success()
                if "etag" in res.headers:
                    self.cached_etags[path] = res.headers["etag"]
            else:
                res.failure(f"Unexpected status: {res.status_code}")

    @task(2)
    def browse_categories(self) -> None:
        """Fetch category hierarchy tree."""
        path = "/api/v1/categories"
        headers = {}
        if path in self.cached_etags:
            headers["If-None-Match"] = self.cached_etags[path]

        with self.client.get(
            path, headers=headers, name="/api/v1/categories", catch_response=True
        ) as res:
            if res.status_code in (200, 304):
                res.success()
                if "etag" in res.headers:
                    self.cached_etags[path] = res.headers["etag"]
            else:
                res.failure(f"Unexpected status: {res.status_code}")

    @task(5)
    def search_products(self) -> None:
        """Execute trigram search with score ranking."""
        query = secrets.choice(SEARCH_QUERIES)
        path = f"/api/v1/products/search?q={query}"
        with self.client.get(path, name="/api/v1/products/search", catch_response=True) as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"Search failed with status: {res.status_code}")

    @task(6)
    def scan_barcode(self) -> None:
        """Lookup product by GTIN barcode."""
        barcode = secrets.choice(SAMPLE_BARCODES)
        path = f"/api/v1/products/by-barcode/{barcode}"
        headers = {}
        if path in self.cached_etags:
            headers["If-None-Match"] = self.cached_etags[path]

        with self.client.get(
            path,
            headers=headers,
            name="/api/v1/products/by-barcode/:barcode",
            catch_response=True,
        ) as res:
            # 200 (found), 304 (cached), or 404 (valid barcode not in db) are valid responses
            if res.status_code in (200, 304, 404):
                res.success()
                if res.status_code == 200 and "etag" in res.headers:
                    self.cached_etags[path] = res.headers["etag"]
            else:
                res.failure(f"Barcode lookup error: {res.status_code}")

    @task(1)
    def health_check(self) -> None:
        """Liveness ping."""
        self.client.get("/health/live", name="/health/live")

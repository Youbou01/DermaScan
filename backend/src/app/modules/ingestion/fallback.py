import json
import urllib.request
from typing import Any


def fetch_remote_product_by_barcode(barcode: str) -> dict[str, Any] | None:
    """Task E4: Fetches a single product live from Open Beauty Facts API on barcode miss."""
    clean_barcode = barcode.strip()
    url = f"https://world.openbeautyfacts.org/api/v2/product/{clean_barcode}.json"
    headers = {"User-Agent": "DermaScan-LiveFallback/1.0 (Academic Project)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            if data.get("status") == 1 and "product" in data:
                prod = data["product"]
                if isinstance(prod, dict):
                    return prod
    except Exception:
        return None
    return None

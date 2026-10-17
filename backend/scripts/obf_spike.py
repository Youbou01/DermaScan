#!/usr/bin/env python3
"""Task E1: Open Beauty Facts Data-Source Spike."""

# ruff: noqa: S108, S310, T201
import gzip
import json
import urllib.request
from collections import Counter
from pathlib import Path

DUMP_URL = "https://static.openbeautyfacts.org/data/openbeautyfacts-products.jsonl.gz"
DUMP_PATH = Path("/tmp/openbeautyfacts-products.jsonl.gz")


def main() -> None:
    if not DUMP_PATH.exists():
        print(f"Downloading {DUMP_URL} to {DUMP_PATH}...")
        req = urllib.request.Request(DUMP_URL, headers={"User-Agent": "DermaScan-Spike/1.0"})
        with urllib.request.urlopen(req) as resp, open(DUMP_PATH, "wb") as out:
            out.write(resp.read())

    total = 0
    has_ingredients = 0
    has_categories = 0
    has_both = 0
    tn_619_total = 0
    tn_619_usable = 0
    top_categories: Counter[str] = Counter()

    with gzip.open(DUMP_PATH, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            code = str(row.get("code") or "").strip()
            ing_text = str(row.get("ingredients_text") or "").strip()
            ing_list = row.get("ingredients") or []
            cats = row.get("categories_tags") or []

            ing_ok = bool(ing_text) or (isinstance(ing_list, list) and len(ing_list) > 0)
            cat_ok = isinstance(cats, list) and len(cats) > 0

            if ing_ok:
                has_ingredients += 1
            if cat_ok:
                has_categories += 1
                for c in cats:
                    if isinstance(c, str):
                        top_categories[c] += 1
            if ing_ok and cat_ok and code:
                has_both += 1

            clean_code = code[1:] if len(code) == 14 and code.startswith("0") else code
            if clean_code.startswith("619"):
                tn_619_total += 1
                if ing_ok:
                    tn_619_usable += 1

    print("\n================ E1 SPIKE REPORT ================")
    print(f"Total products in OBF dump          : {total:,}")
    ing_pct = has_ingredients / max(1, total) * 100
    print(f"Products with ingredients           : {has_ingredients:,} ({ing_pct:.1f}%)")
    cat_pct = has_categories / max(1, total) * 100
    print(f"Products with categories_tags       : {has_categories:,} ({cat_pct:.1f}%)")
    both_pct = has_both / max(1, total) * 100
    print(f"Products with barcode + ing + cat   : {has_both:,} ({both_pct:.1f}%)")
    print(f"Tunisian barcodes (619*) total      : {tn_619_total:,}")
    print(f"Tunisian barcodes (619*) w/ ingred. : {tn_619_usable:,}")
    print("\nTop 25 Category Tags (for Task E3 mapping):")
    for tag, count in top_categories.most_common(25):
        print(f"  {tag:<40} {count:,}")


if __name__ == "__main__":
    main()

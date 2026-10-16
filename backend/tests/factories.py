"""Plain factory functions that build valid, unsaved model instances.

Why not polyfactory? Our tables carry CHECK constraints (13-digit barcode, "moderate or
high needs a source", two-letter locale ...). Randomly generated values violate them
constantly, so we'd override nearly every field anyway. Explicit defaults + keyword
overrides are shorter and always valid.

Usage:  session.add(make_product(name="Cream", score=80))
"""

import itertools
from typing import Any

from app.core.enums import RiskLevel
from app.modules.catalog.enums import ProductSource
from app.modules.catalog.models import Brand, Category, Product
from app.modules.ingredients.models import Ingredient

_sequence = itertools.count(1)


def make_barcode() -> str:
    """A unique, valid 13-digit barcode (Tunisian prefix 619)."""
    return f"619{next(_sequence):010d}"


def make_brand(**overrides: Any) -> Brand:
    n = next(_sequence)
    return Brand(**{"name": f"Brand {n}", **overrides})


def make_category(**overrides: Any) -> Category:
    n = next(_sequence)
    return Category(**{"slug": f"category-{n}", **overrides})


def make_ingredient(**overrides: Any) -> Ingredient:
    n = next(_sequence)
    values: dict[str, Any] = {"inci_name": f"INGREDIENT {n}", "risk_level": RiskLevel.LOW}
    values.update(overrides)
    if values["risk_level"] in (RiskLevel.MODERATE, RiskLevel.HIGH):
        values.setdefault("source_ref", "test-source")  # required by a DB constraint
    return Ingredient(**values)


def make_product(**overrides: Any) -> Product:
    n = next(_sequence)
    values: dict[str, Any] = {
        "barcode": make_barcode(),
        "name": f"Product {n}",
        "source": ProductSource.MANUAL,
    }
    values.update(overrides)
    return Product(**values)

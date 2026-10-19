"""Idempotent category tree seed. Data lives next to this module; writes go through catalog.

uv run python scripts/seed_categories.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CategorySeedNode, CategoryService

DATA_FILE = Path(__file__).resolve().parent / "data" / "categories.json"


def load_category_seed(path: Path = DATA_FILE) -> list[CategorySeedNode]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [_parse_node(raw) for raw in payload["categories"]]


def _parse_node(raw: dict[str, Any]) -> CategorySeedNode:
    names = raw["names"]
    if "en" not in names:
        msg = f"Category '{raw.get('slug')}' is missing a required English name."
        raise ValueError(msg)
    children = [_parse_node(child) for child in raw.get("children") or []]
    return CategorySeedNode(slug=raw["slug"], names=names, children=children)


async def seed_categories(session: AsyncSession, path: Path = DATA_FILE) -> int:
    """Upsert the tree from the versioned JSON file. Safe to run twice. Returns touched count."""
    service = CategoryService(session)
    touched = await service.upsert_tree(load_category_seed(path))
    await session.commit()
    return touched

"""Category read/write used by the home feed, category tree endpoint, and seed loaders."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import DEFAULT_LOCALE
from app.modules.catalog.category_repository import CategoryRepository
from app.modules.catalog.models import Category, CategoryTranslation
from app.modules.catalog.schemas import CategoryNodeOut


@dataclass(frozen=True, slots=True)
class CategorySeedNode:
    """One node from the category seed file (ingestion passes these in)."""

    slug: str
    names: Mapping[str, str]
    children: Sequence[CategorySeedNode] = ()


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._categories = CategoryRepository(session)

    async def get_tree(self, locale: str) -> list[CategoryNodeOut]:
        """Top-level categories with their direct children, names localized."""
        rows = await self._categories.get_all_with_translations()
        by_parent: dict[object, list[Category]] = {}
        for category in rows:
            by_parent.setdefault(category.parent_id, []).append(category)

        def to_node(category: Category) -> CategoryNodeOut:
            children = sorted(by_parent.get(category.id, []), key=lambda c: c.slug)
            return CategoryNodeOut(
                slug=category.slug,
                name=_localized_name(category.translations, locale, category.slug),
                children=[to_node(child) for child in children],
            )

        roots = sorted(by_parent.get(None, []), key=lambda c: c.slug)
        return [to_node(root) for root in roots]

    async def upsert_tree(self, nodes: Sequence[CategorySeedNode]) -> int:
        """Insert or update categories and translations. Idempotent. Returns touched row count.

        Parent links are applied after every slug exists so a seed file can list children
        before their parent without failing. Cycles are rejected up front.
        """
        flat = list(_flatten(nodes))
        _assert_no_cycles(flat)
        touched = 0
        by_slug: dict[str, Category] = {}

        for slug, _parent_slug, names in flat:
            category = await self._categories.get_by_slug(slug)
            if category is None:
                category = await self._categories.add(Category(slug=slug))
                touched += 1
            by_slug[slug] = category
            for locale, name in names.items():
                if await self._categories.upsert_translation(category.id, locale, name):
                    touched += 1

        for slug, parent_slug, _names in flat:
            parent_id = by_slug[parent_slug].id if parent_slug else None
            if await self._categories.set_parent(by_slug[slug], parent_id):
                touched += 1

        return touched


def _localized_name(translations: Iterable[CategoryTranslation], locale: str, fallback: str) -> str:
    names = {translation.locale: translation.name for translation in translations}
    return names.get(locale) or names.get(DEFAULT_LOCALE) or fallback


def _flatten(
    nodes: Sequence[CategorySeedNode], parent_slug: str | None = None
) -> list[tuple[str, str | None, Mapping[str, str]]]:
    rows: list[tuple[str, str | None, Mapping[str, str]]] = []
    for node in nodes:
        rows.append((node.slug, parent_slug, node.names))
        rows.extend(_flatten(node.children, parent_slug=node.slug))
    return rows


def _assert_no_cycles(flat: Sequence[tuple[str, str | None, Mapping[str, str]]]) -> None:
    parent_of = {slug: parent for slug, parent, _ in flat}
    for slug in parent_of:
        seen: set[str] = set()
        current: str | None = slug
        while current is not None:
            if current in seen:
                msg = f"Category seed has a cycle involving '{slug}'."
                raise ValueError(msg)
            seen.add(current)
            current = parent_of.get(current)

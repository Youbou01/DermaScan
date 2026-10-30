"""Home feed (story 1): category grid, top-rated (daily rotation), recently added."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import DEFAULT_LOCALE, pick_translation, resolve_product_name
from app.core.pagination import decode_cursor, encode_cursor
from app.modules.catalog.category_service import CategoryService
from app.modules.catalog.exceptions import (
    InvalidCursorError,
    InvalidLimitError,
    SectionNotFoundError,
)
from app.modules.catalog.home_repository import HomeRepository, ProductCardRow
from app.modules.catalog.schemas import (
    CategoryOut,
    HomeFeedOut,
    HomeSectionOut,
    ProductCardOut,
)

DEFAULT_LIMIT = 10
MIN_LIMIT = 1
MAX_LIMIT = 50

_SECTION_TITLES: dict[str, dict[str, str]] = {
    "categories": {"en": "Categories", "fr": "Catégories"},
    "top_rated": {"en": "Top rated", "fr": "Mieux notés"},
    "recently_added": {"en": "Recently added", "fr": "Ajoutés récemment"},
}


class HomeFeedService:
    def __init__(self, session: AsyncSession, *, feed_date: date | None = None) -> None:
        self._home = HomeRepository(session)
        self._categories = CategoryService(session)
        self._feed_date = feed_date

    def today(self) -> date:
        return self._feed_date or datetime.now(UTC).date()

    async def get_feed(self, locale: str, *, limit: int = DEFAULT_LIMIT) -> HomeFeedOut:
        limit = _validate_limit(limit)
        categories = await self._category_section(locale)
        top_rated = await self._top_rated_section(locale, limit=limit, cursor=None)
        recent = await self._recent_section(locale, limit=limit, cursor=None)
        return HomeFeedOut(sections=[categories, top_rated, recent])

    async def get_section(
        self,
        section_id: str,
        locale: str,
        *,
        cursor: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> HomeSectionOut:
        limit = _validate_limit(limit)
        if section_id == "categories":
            if cursor is not None:
                raise InvalidCursorError("The categories section does not support pagination.")
            return await self._category_section(locale)
        if section_id == "top_rated":
            return await self._top_rated_section(locale, limit=limit, cursor=cursor)
        if section_id == "recently_added":
            return await self._recent_section(locale, limit=limit, cursor=cursor)
        raise SectionNotFoundError(f"No home section named '{section_id}'.")

    async def _category_section(self, locale: str) -> HomeSectionOut:
        tree = await self._categories.get_tree(locale)
        items = [CategoryOut(slug=node.slug, name=node.name) for node in tree]
        return HomeSectionOut(
            id="categories",
            type="category_grid",
            title=_title("categories", locale),
            items=items,
            next_cursor=None,
        )

    async def _top_rated_section(
        self, locale: str, *, limit: int, cursor: str | None
    ) -> HomeSectionOut:
        seed_date, after_score, after_rotation, after_id = _parse_top_rated_cursor(
            cursor, default_date=self.today()
        )
        rows = await self._home.list_top_rated(
            seed_date=seed_date,
            limit=limit + 1,
            after_score=after_score,
            after_rotation=after_rotation,
            after_id=after_id,
        )
        page, next_cursor = _page_top_rated(rows, limit=limit, seed_date=seed_date)
        return HomeSectionOut(
            id="top_rated",
            type="top_rated",
            title=_title("top_rated", locale),
            items=[_card(row, locale) for row in page],
            next_cursor=next_cursor,
        )

    async def _recent_section(
        self, locale: str, *, limit: int, cursor: str | None
    ) -> HomeSectionOut:
        after_created_at, after_id = _parse_recent_cursor(cursor)
        rows = await self._home.list_recently_added(
            limit=limit + 1, after_created_at=after_created_at, after_id=after_id
        )
        page, next_cursor = _page_recent(rows, limit=limit)
        return HomeSectionOut(
            id="recently_added",
            type="recently_added",
            title=_title("recently_added", locale),
            items=[_card(row, locale) for row in page],
            next_cursor=next_cursor,
        )


def _title(section_id: str, locale: str) -> str:
    return pick_translation(_SECTION_TITLES[section_id], locale) or section_id


def _validate_limit(limit: int) -> int:
    if limit < MIN_LIMIT or limit > MAX_LIMIT:
        raise InvalidLimitError(f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}.")
    return limit


def _card(row: ProductCardRow, locale: str = DEFAULT_LOCALE) -> ProductCardOut:
    return ProductCardOut(
        id=row.id,
        name=resolve_product_name(row.name, row.name_i18n, locale),
        brand=row.brand_name,
        image_url=row.image_url,
        score=row.score,
        score_band=row.score_band if row.score is not None else None,
        category_slug=row.category_slug,
    )


def _parse_top_rated_cursor(
    cursor: str | None, *, default_date: date
) -> tuple[date, int | None, str | None, uuid.UUID | None]:
    if cursor is None:
        return default_date, None, None, None
    try:
        data = decode_cursor(cursor)
        if data.get("s") != "top_rated":
            msg = "Cursor belongs to another section."
            raise ValueError(msg)
        seed_date = date.fromisoformat(str(data["d"]))
        return (
            seed_date,
            int(data["score"]),
            str(data["rot"]),
            uuid.UUID(str(data["id"])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidCursorError("The cursor is invalid or tampered with.") from exc


def _parse_recent_cursor(
    cursor: str | None,
) -> tuple[datetime | None, uuid.UUID | None]:
    if cursor is None:
        return None, None
    try:
        data = decode_cursor(cursor)
        if data.get("s") != "recently_added":
            msg = "Cursor belongs to another section."
            raise ValueError(msg)
        created_at = datetime.fromisoformat(str(data["created_at"]))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return created_at, uuid.UUID(str(data["id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidCursorError("The cursor is invalid or tampered with.") from exc


def _page_top_rated(
    rows: list[ProductCardRow], *, limit: int, seed_date: date
) -> tuple[list[ProductCardRow], str | None]:
    page = rows[:limit]
    if len(rows) <= limit or not page:
        return page, None
    last = page[-1]
    if last.rotation_key is None:
        return page, None
    token = encode_cursor(
        {
            "s": "top_rated",
            "d": seed_date.isoformat(),
            "score": last.score,
            "rot": last.rotation_key,
            "id": str(last.id),
        }
    )
    return page, token


def _page_recent(
    rows: list[ProductCardRow], *, limit: int
) -> tuple[list[ProductCardRow], str | None]:
    page = rows[:limit]
    if len(rows) <= limit or not page:
        return page, None
    last = page[-1]
    token = encode_cursor(
        {
            "s": "recently_added",
            "created_at": last.created_at.isoformat(),
            "id": str(last.id),
        }
    )
    return page, token

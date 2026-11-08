"""Product search by name (story 5) and filtered search (story 6)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.errors import UnprocessableError
from app.core.i18n import DEFAULT_LOCALE, resolve_product_name
from app.core.keyset import InvalidCursorError, Page, paginate
from app.modules.catalog.models import Product
from app.modules.catalog.search_repository import (
    ProductSearchRepository,
    by_bands,
    by_categories,
    by_score_range,
    with_ingredients,
    without_ingredients,
)
from app.modules.catalog.search_schemas import ProductSummary
from app.modules.catalog.search_text import normalize_name
from app.modules.ingredients import IngredientService

MAX_SEARCH_RESULTS = 200  # ranked fuzzy results use an offset cursor: keep it bounded


class InvalidScoreRangeError(UnprocessableError):
    code = "invalid-score-range"
    title = "min_score must not exceed max_score"


def _summary(product: Product, locale: str = DEFAULT_LOCALE) -> ProductSummary:
    return ProductSummary(
        id=product.id,
        barcode=product.barcode,
        name=resolve_product_name(product.name, product.name_i18n, locale),
        brand=product.brand.name if product.brand else None,
        image_url=product.image_url,
        score=product.score,
        score_band=product.score_band,
    )


def _empty() -> Page[ProductSummary]:
    return Page[ProductSummary](items=[], next_cursor=None)


def _parse_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise InvalidCursorError from exc
    if offset < 0:
        raise InvalidCursorError
    return offset


async def _resolve_ingredient_ids(
    session: AsyncSession, names: list[str]
) -> tuple[list[uuid.UUID], list[str]]:
    """Resolve names through the ingredients alias pipeline (public service only).
    Returns (distinct ingredient ids, names that did not match)."""
    matches = await IngredientService(session).match(names)
    ids: list[uuid.UUID] = []
    unmatched: list[str] = []
    for match in matches:
        if match.ingredient_id is None:
            unmatched.append(match.raw_text)
        elif match.ingredient_id not in ids:
            ids.append(match.ingredient_id)
    return ids, unmatched


class ProductSearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProductSearchRepository(session)

    async def search_by_name(
        self, q: str, *, limit: int, cursor: str | None
    ) -> Page[ProductSummary]:
        offset = _parse_offset(cursor)
        q_norm = normalize_name(q)
        if not q_norm or offset >= MAX_SEARCH_RESULTS:
            return _empty()
        page_size = min(limit, MAX_SEARCH_RESULTS - offset)
        rows = await self._repo.search_by_name(q_norm, limit=page_size + 1, offset=offset)
        has_more = len(rows) > page_size and offset + page_size < MAX_SEARCH_RESULTS
        return Page[ProductSummary](
            items=[_summary(p) for p in rows[:page_size]],
            next_cursor=str(offset + page_size) if has_more else None,
        )

    async def filter_products(
        self,
        *,
        category: str | None,
        bands: list[RiskLevel] | None,
        min_score: int | None,
        max_score: int | None,
        include: list[str] | None,
        exclude: list[str] | None,
        limit: int,
        cursor: str | None,
    ) -> Page[ProductSummary]:
        """Scored products only, best score first (unscored = insufficient data).
        An unknown category slug or an unrecognized `include` name gives an empty page;
        an unrecognized `exclude` name is ignored."""
        if min_score is not None and max_score is not None and min_score > max_score:
            raise InvalidScoreRangeError

        stmt = self._repo.base_query().where(Product.score.is_not(None))
        if category:
            category_ids = await self._repo.category_subtree_ids(category)
            if not category_ids:
                return _empty()
            stmt = by_categories(stmt, category_ids)
        if bands:
            stmt = by_bands(stmt, bands)
        stmt = by_score_range(stmt, min_score, max_score)
        if include:
            include_ids, unmatched = await _resolve_ingredient_ids(self._session, include)
            if unmatched:
                return _empty()
            stmt = with_ingredients(stmt, include_ids)
        if exclude:
            exclude_ids, _ = await _resolve_ingredient_ids(self._session, exclude)
            stmt = without_ingredients(stmt, exclude_ids)

        items, next_cursor = await paginate(
            self._session,
            stmt,
            sort="score",
            sort_column=Product.score,
            id_column=Product.id,
            key=lambda p: (p.score, p.id),
            parse_value=int,
            limit=limit,
            cursor=cursor,
        )
        return Page[ProductSummary](items=[_summary(p) for p in items], next_cursor=next_cursor)

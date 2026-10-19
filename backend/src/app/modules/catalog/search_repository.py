"""SQL for product search and filters. Private: use `ProductSearchService`."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Float, Select, Text, case, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.enums import RiskLevel
from app.modules.catalog.models import Category, Product, ProductIngredient

ProductQuery = Select[Product]


# Each filter is a small pure function: easy to test and to combine.
def by_categories(stmt: ProductQuery, category_ids: Sequence[uuid.UUID]) -> ProductQuery:
    return stmt.where(Product.primary_category_id.in_(category_ids))


def by_bands(stmt: ProductQuery, bands: Sequence[RiskLevel]) -> ProductQuery:
    return stmt.where(Product.score_band.in_(bands))


def by_score_range(
    stmt: ProductQuery, min_score: int | None, max_score: int | None
) -> ProductQuery:
    if min_score is not None:
        stmt = stmt.where(Product.score >= min_score)
    if max_score is not None:
        stmt = stmt.where(Product.score <= max_score)
    return stmt


def with_ingredients(stmt: ProductQuery, ingredient_ids: Sequence[uuid.UUID]) -> ProductQuery:
    """Product contains ALL the given ingredients."""
    for ingredient_id in ingredient_ids:
        stmt = stmt.where(
            exists().where(
                ProductIngredient.product_id == Product.id,
                ProductIngredient.ingredient_id == ingredient_id,
            )
        )
    return stmt


def without_ingredients(stmt: ProductQuery, ingredient_ids: Sequence[uuid.UUID]) -> ProductQuery:
    """Product contains NONE of the given ingredients."""
    if not ingredient_ids:
        return stmt
    return stmt.where(
        ~exists().where(
            ProductIngredient.product_id == Product.id,
            ProductIngredient.ingredient_id.in_(ingredient_ids),
        )
    )


class ProductSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def base_query() -> ProductQuery:
        return select(Product).options(joinedload(Product.brand))

    async def category_subtree_ids(self, slug: str) -> list[uuid.UUID]:
        """The category with this slug plus all its descendants."""
        tree = select(Category.id).where(Category.slug == slug).cte("tree", recursive=True)
        tree = tree.union_all(select(Category.id).join(tree, Category.parent_id == tree.c.id))
        return list((await self._session.scalars(select(tree.c.id))).all())

    async def search_by_name(self, q_norm: str, *, limit: int, offset: int) -> list[Product]:
        """Prefix matches first, then fuzzy (trigram) matches by similarity."""
        prefix = Product.name_normalized.startswith(q_norm, autoescape=True)
        rank = func.greatest(
            func.similarity(Product.name_normalized, q_norm),
            func.word_similarity(q_norm, Product.name_normalized),
        ) + case((prefix, literal(1.0, Float)), else_=literal(0.0, Float))
        stmt = (
            self.base_query()
            .where(
                or_(
                    prefix,
                    Product.name_normalized.op("%")(q_norm),
                    literal(q_norm, Text).op("<%")(Product.name_normalized),
                )
            )
            .order_by(rank.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self._session.scalars(stmt)).all())

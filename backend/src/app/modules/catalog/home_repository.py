"""Queries for home-feed product shelves. Private to the catalog module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import String, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.models import Brand, Category, Product


@dataclass(frozen=True, slots=True)
class ProductCardRow:
    id: uuid.UUID
    name: str
    brand_name: str | None
    image_url: str | None
    score: int | None
    score_band: RiskLevel
    category_slug: str | None
    created_at: datetime
    rotation_key: str | None = None
    name_i18n: dict[str, str] | None = None


class HomeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_top_rated(
        self,
        *,
        seed_date: date,
        limit: int,
        after_score: int | None = None,
        after_rotation: str | None = None,
        after_id: uuid.UUID | None = None,
    ) -> list[ProductCardRow]:
        """Products with a real score, best first, daily rotation as tie-breaker."""
        seed = seed_date.isoformat()
        rotation = func.md5(func.concat(seed, Product.id.cast(String))).label("rotation_key")
        stmt = (
            select(Product, Brand.name, Category.slug, rotation)
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .outerjoin(Category, Product.primary_category_id == Category.id)
            .where(
                Product.score.is_not(None),
                Product.score_band != RiskLevel.UNKNOWN,
            )
            .order_by(Product.score.desc(), rotation.asc(), Product.id.asc())
            .limit(limit)
        )
        if after_score is not None and after_rotation is not None and after_id is not None:
            stmt = stmt.where(
                or_(
                    Product.score < after_score,
                    and_(
                        Product.score == after_score,
                        or_(
                            rotation > after_rotation,
                            and_(rotation == after_rotation, Product.id > after_id),
                        ),
                    ),
                )
            )
        rows = (await self._session.execute(stmt)).all()
        return [
            ProductCardRow(
                id=product.id,
                name=product.name,
                brand_name=brand_name,
                image_url=product.image_url,
                score=product.score,
                score_band=RiskLevel(product.score_band),
                category_slug=category_slug,
                created_at=product.created_at,
                rotation_key=rot_key,
                name_i18n=product.name_i18n,
            )
            for product, brand_name, category_slug, rot_key in rows
        ]

    async def list_recently_added(
        self,
        *,
        limit: int,
        after_created_at: datetime | None = None,
        after_id: uuid.UUID | None = None,
    ) -> list[ProductCardRow]:
        stmt = (
            select(Product, Brand.name, Category.slug)
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .outerjoin(Category, Product.primary_category_id == Category.id)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .limit(limit)
        )
        if after_created_at is not None and after_id is not None:
            stmt = stmt.where(
                or_(
                    Product.created_at < after_created_at,
                    and_(Product.created_at == after_created_at, Product.id < after_id),
                )
            )
        rows = (await self._session.execute(stmt)).all()
        return [
            ProductCardRow(
                id=product.id,
                name=product.name,
                brand_name=brand_name,
                image_url=product.image_url,
                score=product.score,
                score_band=RiskLevel(product.score_band),
                category_slug=category_slug,
                created_at=product.created_at,
                name_i18n=product.name_i18n,
            )
            for product, brand_name, category_slug in rows
        ]

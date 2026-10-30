"""The catalog module's public service (read side; writes arrive with the importer)."""

import uuid
from collections.abc import Collection, Iterable

import structlog
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.i18n import DEFAULT_LOCALE
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.catalog.gtin import normalize_gtin
from app.modules.catalog.miss_repository import BarcodeMissRepository
from app.modules.catalog.models import Category, CategoryTranslation, Product
from app.modules.catalog.repository import ProductRepository
from app.modules.catalog.schemas import CategoryOut, ProductDetail, ProductIngredientOut
from app.modules.ingredients import IngredientInfo, IngredientService
from app.modules.scoring import (
    INTERIM_RISK_TO_RATING,
    SCORING_VERSION,
    IngredientScoreInput,
    calculate_score,
)

logger = structlog.get_logger(__name__)


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._products = ProductRepository(session)
        self._misses = BarcodeMissRepository(session)
        # Same session = same transaction. Ingredient data comes ONLY through the other
        # module's public service, never through its tables or models.
        self._ingredients = IngredientService(session)

    async def get_product_detail(self, product_id: uuid.UUID, locale: str) -> ProductDetail:
        product = await self._products.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(f"No product with id {product_id}.")
        return await self._to_detail(product, locale)

    async def get_product_detail_by_barcode(self, barcode: str, locale: str) -> ProductDetail:
        """Accepts EAN-13, UPC-A or EAN-8, with or without spaces/hyphens.
        Raises InvalidBarcodeError (422) for a malformed code, ProductNotFoundError (404)
        for a valid code we do not have."""
        gtin = normalize_gtin(barcode)
        product = await self._products.get_by_barcode(gtin)
        if product is None:
            await self._record_miss(gtin)
            raise ProductNotFoundError(f"No product with barcode {gtin}.")
        return await self._to_detail(product, locale)

    async def _record_miss(self, gtin: str) -> None:
        """Count the miss. It must never turn a clean 404 into a 500."""
        try:
            await self._misses.record(gtin)
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            logger.warning("barcode_miss_not_recorded", barcode=gtin, exc_info=True)

    async def _to_detail(self, product: Product, locale: str) -> ProductDetail:
        ingredient_ids = {
            item.ingredient_id for item in product.ingredients if item.ingredient_id is not None
        }
        infos = await self._ingredients.get_many(ingredient_ids, locale)

        return ProductDetail(
            id=product.id,
            barcode=product.barcode,
            name=product.name,
            brand=product.brand.name if product.brand else None,
            image_url=product.image_url,
            category=_category_out(product.primary_category, locale),
            score=product.score,
            score_band=RiskLevel(product.score_band),
            score_coverage=product.score_coverage,
            score_is_estimated=product.score_is_estimated,
            ingredients=[
                _ingredient_out(
                    item.position,
                    item.raw_text,
                    infos.get(item.ingredient_id) if item.ingredient_id else None,
                )
                for item in product.ingredients
            ],
        )

    async def rematch_unmatched(self, batch_size: int = 500) -> int:
        """Re-runs exact matching on product_ingredient rows with ingredient_id IS NULL."""
        unmatched_rows = await self._products.find_unmatched_ingredients(limit=batch_size)
        if not unmatched_rows:
            return 0

        tokens = [row.raw_text for row in unmatched_rows]
        matches = await self._ingredients.match(tokens)

        matched_count = 0
        dirty_product_ids = set()

        for row, match in zip(unmatched_rows, matches, strict=True):
            if match.ingredient_id is not None:
                row.ingredient_id = match.ingredient_id
                dirty_product_ids.add(row.product_id)
                matched_count += 1

        if dirty_product_ids:
            await self._session.execute(
                update(Product).where(Product.id.in_(dirty_product_ids)).values(score_dirty=True)
            )
        await self._session.flush()
        return matched_count

    async def recompute_dirty_scores(self, batch_size: int = 100) -> int:
        """Selects products where score_dirty = True or version is old and rescores them."""
        products = await self._products.find_dirty_or_stale_products(
            batch_size=batch_size, min_scoring_version=SCORING_VERSION
        )
        if not products:
            return 0

        all_ing_ids: set[uuid.UUID] = set()
        for prod in products:
            for pi in prod.ingredients:
                if pi.ingredient_id is not None:
                    all_ing_ids.add(pi.ingredient_id)

        infos = await self._ingredients.get_many(all_ing_ids, locale="en") if all_ing_ids else {}

        for prod in products:
            score_inputs: list[IngredientScoreInput] = []
            for pi in prod.ingredients:
                info = infos.get(pi.ingredient_id) if pi.ingredient_id else None
                if info is not None:
                    rating = (
                        info.rating
                        if info.rating is not None
                        else INTERIM_RISK_TO_RATING.get(info.risk_level)
                    )
                    conf = (
                        info.rating_confidence
                        if info.rating_confidence is not None
                        else (0.0 if rating is None else 1.0)
                    )
                    is_proh = info.is_prohibited
                else:
                    rating = None
                    conf = 0.0
                    is_proh = False
                score_inputs.append(
                    IngredientScoreInput(
                        position=pi.position,
                        rating=rating,
                        confidence=conf,
                        is_prohibited=is_proh,
                    )
                )

            res = calculate_score(score_inputs)
            prod.score = res.score
            prod.score_band = res.band
            prod.score_coverage = res.confidence
            prod.score_is_estimated = res.is_estimated
            prod.scoring_version = res.version
            prod.score_dirty = False

        await self._session.flush()
        return len(products)

    async def mark_products_dirty_for_ingredients(
        self, ingredient_ids: Collection[uuid.UUID]
    ) -> int:
        count = await self._products.mark_products_dirty_for_ingredients(ingredient_ids)
        await self._session.flush()
        return count


def _ingredient_out(
    position: int, raw_text: str, info: IngredientInfo | None
) -> ProductIngredientOut:
    if info is None:  # not recognized: shown, but never presented as safe
        return ProductIngredientOut(
            position=position,
            name=raw_text,
            inci_name=None,
            matched=False,
            risk_level=RiskLevel.UNKNOWN,
            rationale=None,
            rating=None,
            summary=None,
            confidence=None,
        )
    return ProductIngredientOut(
        position=position,
        name=raw_text,
        inci_name=info.inci_name,
        matched=True,
        risk_level=info.risk_level,
        rationale=info.rationale,
        rating=info.rating,
        summary=info.summary,
        confidence=info.rating_confidence,
    )


def _category_out(category: Category | None, locale: str) -> CategoryOut | None:
    if category is None:
        return None
    return CategoryOut(
        slug=category.slug, name=_localized_name(category.translations, locale, category.slug)
    )


def _localized_name(translations: Iterable[CategoryTranslation], locale: str, fallback: str) -> str:
    names = {translation.locale: translation.name for translation in translations}
    return names.get(locale) or names.get(DEFAULT_LOCALE) or fallback

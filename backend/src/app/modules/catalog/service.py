"""The catalog module's public service (read side; writes arrive with the importer)."""

import uuid
from collections.abc import Iterable

import structlog
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
            ingredients=[
                _ingredient_out(
                    item.position,
                    item.raw_text,
                    infos.get(item.ingredient_id) if item.ingredient_id else None,
                )
                for item in product.ingredients
            ],
        )


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
        )
    return ProductIngredientOut(
        position=position,
        name=raw_text,
        inci_name=info.inci_name,
        matched=True,
        risk_level=info.risk_level,
        rationale=info.rationale,
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

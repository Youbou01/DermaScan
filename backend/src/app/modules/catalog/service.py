"""The catalog module's public service."""

import uuid
from collections.abc import Awaitable, Callable, Collection, Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.i18n import DEFAULT_LOCALE, resolve_product_name
from app.modules.catalog.category_repository import CategoryRepository
from app.modules.catalog.enums import EnrichmentStatus, ImageStatus
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.catalog.gtin import normalize_gtin
from app.modules.catalog.miss_repository import BarcodeMissRepository
from app.modules.catalog.models import Category, CategoryTranslation, Product, ProductIngredient
from app.modules.catalog.repository import ProductRepository
from app.modules.catalog.schemas import (
    CategoryOut,
    CreateProductInput,
    ProductDetail,
    ProductIngredientOut,
    ProductUpsert,
)
from app.modules.catalog.search_text import normalize_name
from app.modules.ingredients import IngredientInfo, IngredientService
from app.modules.scoring import (
    INTERIM_RISK_TO_RATING,
    SCORING_VERSION,
    IngredientScoreInput,
    calculate_score,
)

logger = structlog.get_logger(__name__)

FallbackHandler = Callable[[str, str], Awaitable[ProductDetail | None]]


class CatalogService:
    def __init__(
        self,
        session: AsyncSession,
        fallback_handler: FallbackHandler | None = None,
    ) -> None:
        self._session = session
        self._products = ProductRepository(session)
        self._categories = CategoryRepository(session)
        self._misses = BarcodeMissRepository(session)
        self._ingredients = IngredientService(session)
        self._fallback_handler = fallback_handler

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
            if self._fallback_handler is not None:
                fallback_detail = await self._fallback_handler(gtin, locale)
                if fallback_detail is not None:
                    return fallback_detail
            else:
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

    async def record_barcode_miss(self, barcode: str) -> None:
        gtin = normalize_gtin(barcode)
        await self._record_miss(gtin)

    async def is_barcode_miss_negative_cached(
        self, barcode: str, duration: timedelta = timedelta(hours=24)
    ) -> bool:
        try:
            gtin = normalize_gtin(barcode)
        except Exception:
            return False
        miss = await self._misses.get_by_barcode(gtin)
        if miss is None:
            return False
        now = datetime.now(UTC)
        last_seen = miss.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        return (now - last_seen) < duration

    async def _to_detail(self, product: Product, locale: str) -> ProductDetail:
        ingredient_ids = {
            item.ingredient_id for item in product.ingredients if item.ingredient_id is not None
        }
        infos = await self._ingredients.get_many(ingredient_ids, locale)

        return ProductDetail(
            id=product.id,
            barcode=product.barcode,
            name=resolve_product_name(product.name, product.name_i18n, locale),
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

    async def upsert_product_from_import(self, data: CreateProductInput) -> Product:
        brand_id: uuid.UUID | None = None
        if data.brand_name:
            brand = await self._products.get_or_create_brand(data.brand_name)
            brand_id = brand.id

        category_id: uuid.UUID | None = None
        if data.category_slug:
            category = await self._categories.get_by_slug(data.category_slug)
            if category:
                category_id = category.id

        product = await self._products.get_by_source(data.source, data.source_id)
        if product is None:
            product = await self._products.get_by_barcode(data.barcode)

        if product is None:
            product = Product(
                barcode=data.barcode,
                name=data.name,
                name_normalized=normalize_name(data.name),
                source=data.source,
                source_id=data.source_id,
                brand_id=brand_id,
                primary_category_id=category_id,
                image_url=data.image_url,
                raw_ingredients_text=data.raw_ingredients_text,
                source_lang=data.source_lang,
                name_i18n=data.name_i18n,
                field_provenance=data.field_provenance,
                enrichment_status=EnrichmentStatus.PENDING,
                image_status=ImageStatus.CANDIDATE if data.image_url else ImageStatus.NONE,
            )
            self._session.add(product)
            await self._session.flush()
        else:
            product.barcode = data.barcode
            product.name = data.name
            product.name_normalized = normalize_name(data.name)
            product.brand_id = brand_id
            if category_id is not None:
                product.primary_category_id = category_id
            if data.image_url:
                product.image_url = data.image_url
            product.raw_ingredients_text = data.raw_ingredients_text
            product.source_lang = data.source_lang
            if data.name_i18n:
                product.name_i18n = data.name_i18n
            if data.field_provenance:
                product.field_provenance = data.field_provenance
            await self._session.flush()

        await self._products.delete_product_ingredients(product.id)
        new_ingredients: list[ProductIngredient] = [
            ProductIngredient(
                product_id=product.id,
                position=pos,
                raw_text=raw_text,
                ingredient_id=ing_id,
            )
            for pos, raw_text, ing_id in data.ingredients
        ]
        self._session.add_all(new_ingredients)
        await self._session.flush()

        all_ing_ids = {ing_id for _, _, ing_id in data.ingredients if ing_id is not None}
        infos = await self._ingredients.get_many(all_ing_ids, locale="en") if all_ing_ids else {}

        score_inputs: list[IngredientScoreInput] = []
        for pos, _, ing_id in data.ingredients:
            info = infos.get(ing_id) if ing_id else None
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
                    position=pos,
                    rating=rating,
                    confidence=conf,
                    is_prohibited=is_proh,
                )
            )

        res = calculate_score(score_inputs)
        product.score = res.score
        product.score_band = res.band
        product.score_coverage = res.confidence
        product.score_is_estimated = res.is_estimated
        product.scoring_version = res.version
        product.score_dirty = False
        await self._session.flush()

        loaded = await self._products.get_by_id(product.id)
        return loaded or product

    async def upsert_product(self, data: ProductUpsert) -> Product:
        """Publish a product with strict per-field provenance precedence:
        curated > retailer/brand > open_beauty_facts > ai.
        A lower-precedence source never overwrites a higher-precedence field.
        """
        source_precedence: dict[str, int] = {
            "curated": 4,
            "manual": 4,
            "retailer": 3,
            "brand": 3,
            "scrape": 3,
            "open_beauty_facts": 2,
            "obf": 2,
            "ai": 1,
            "ai-guess": 1,
        }

        brand_id: uuid.UUID | None = None
        if data.brand_name:
            brand = await self._products.get_or_create_brand(data.brand_name)
            brand_id = brand.id

        category_id: uuid.UUID | None = None
        if data.category_slug:
            category = await self._categories.get_by_slug(data.category_slug)
            if category:
                category_id = category.id

        product = await self._products.get_by_source(data.source, data.source_id)
        if product is None:
            product = await self._products.get_by_barcode(data.barcode)

        now_iso = datetime.now(UTC).isoformat()
        current_prov: dict[str, Any] = dict(product.field_provenance or {}) if product else {}

        def can_update_field(field_name: str) -> bool:
            if product is None:
                return True
            old_source = str(
                current_prov.get(field_name, {}).get("source", product.source.value)
            ).lower()
            new_source = str(
                data.field_provenance.get(field_name, {}).get("source", data.source.value)
            ).lower()
            old_rank = source_precedence.get(old_source, 0)
            new_rank = source_precedence.get(new_source, 0)
            return new_rank >= old_rank

        if product is None:
            prov: dict[str, Any] = {}
            for field in ("name", "brand", "category", "ingredients", "image"):
                if field in data.field_provenance:
                    prov[field] = data.field_provenance[field]
                else:
                    prov[field] = {"source": data.source.value, "updated_at": now_iso}

            product = Product(
                barcode=data.barcode,
                name=data.name,
                name_normalized=normalize_name(data.name),
                source=data.source,
                source_id=data.source_id,
                brand_id=brand_id,
                primary_category_id=category_id,
                image_url=data.image_url,
                image_source_url=data.image_source_url,
                raw_ingredients_text=data.raw_ingredients_text,
                source_lang=data.source_lang,
                name_i18n=data.name_i18n,
                field_provenance=prov,
                enrichment_status=data.enrichment_status,
                image_status=ImageStatus.CANDIDATE if data.image_url else ImageStatus.NONE,
                score_dirty=True,
                data_quality=(
                    Decimal(str(data.data_quality)) if data.data_quality is not None else None
                ),
            )
            self._session.add(product)
            await self._session.flush()
        else:
            if can_update_field("name"):
                product.name = data.name
                product.name_normalized = normalize_name(data.name)
                if data.name_i18n:
                    product.name_i18n = data.name_i18n
                if "name" in data.field_provenance:
                    current_prov["name"] = data.field_provenance["name"]

            if can_update_field("brand") and brand_id is not None:
                product.brand_id = brand_id
                if "brand" in data.field_provenance:
                    current_prov["brand"] = data.field_provenance["brand"]

            if can_update_field("category") and category_id is not None:
                product.primary_category_id = category_id
                if "category" in data.field_provenance:
                    current_prov["category"] = data.field_provenance["category"]

            if can_update_field("image") and (data.image_url or data.image_source_url):
                if data.image_url:
                    product.image_url = data.image_url
                if data.image_source_url:
                    product.image_source_url = data.image_source_url
                if "image" in data.field_provenance:
                    current_prov["image"] = data.field_provenance["image"]

            if data.source_lang:
                product.source_lang = data.source_lang
            if data.raw_ingredients_text:
                product.raw_ingredients_text = data.raw_ingredients_text

            product.field_provenance = current_prov
            product.enrichment_status = data.enrichment_status
            if data.data_quality is not None:
                product.data_quality = Decimal(str(data.data_quality))

            await self._session.flush()

        if can_update_field("ingredients") and data.ingredients:
            await self._products.delete_product_ingredients(product.id)
            new_ingredients = [
                ProductIngredient(
                    product_id=product.id,
                    position=pos,
                    raw_text=raw_text,
                    ingredient_id=ing_id,
                )
                for pos, raw_text, ing_id in data.ingredients
            ]
            self._session.add_all(new_ingredients)
            current_prov["ingredients"] = data.field_provenance.get(
                "ingredients", {"source": data.source.value, "updated_at": now_iso}
            )
            product.field_provenance = current_prov
            product.score_dirty = True
            await self._session.flush()

        loaded = await self._products.get_by_id(product.id)
        return loaded or product

    async def get_image_info(
        self, product_id: uuid.UUID
    ) -> tuple[str, str | None, ImageStatus] | None:
        """Returns (barcode, image_source_url, image_status) for image processing."""
        prod = await self._products.get_by_id(product_id)
        if prod is None:
            return None
        return (prod.barcode, prod.image_source_url, prod.image_status)

    async def update_image_result(
        self,
        product_id: uuid.UUID,
        image_url: str | None,
        image_status: ImageStatus,
        image_quality: Decimal | None = None,
    ) -> None:
        """Updates product image URL, status, and quality."""
        prod = await self._products.get_by_id(product_id)
        if prod is None:
            return
        prod.image_url = image_url
        prod.image_status = image_status
        if image_quality is not None:
            prod.image_quality = image_quality
        await self._session.flush()


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

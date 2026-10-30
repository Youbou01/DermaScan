from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.enrichment.llm.fake import FakeLLMClient
from app.modules.enrichment.llm.router import LLMRouter
from app.modules.enrichment.service import EnrichmentService
from app.modules.ingredients.enums import RatingSource, ReviewStatus
from app.modules.ingredients.models import Ingredient, IngredientAlias


@pytest.fixture
def fake_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://skincare:test@localhost:5432/skincare_test",
        llm_providers="fake_primary,fake_secondary",
        llm_chain_rate="fake_primary,fake_secondary",
    )


@pytest.mark.asyncio
async def test_rate_ingredients_pipeline_end_to_end(
    db_session: AsyncSession,
    fake_settings: Settings,
) -> None:
    # 1. Create test ingredients: one normal, one prohibited, one restricted
    prohibited = Ingredient(
        inci_name="Test Prohibited X",
        is_prohibited=True,
        rating_source=RatingSource.UNRATED,
    )
    restricted = Ingredient(
        inci_name="Test Restricted Y",
        is_restricted=True,
        rating_source=RatingSource.UNRATED,
    )
    benign = Ingredient(
        inci_name="Test Benign Z",
        rating_source=RatingSource.UNRATED,
    )
    db_session.add_all([prohibited, restricted, benign])
    await db_session.flush()

    # 2. Fake LLM responses
    primary_fake = FakeLLMClient(
        provider="fake_primary",
        default_response={
            "ingredients": [
                {
                    "inci": "Test Restricted Y",
                    "rating": 9.5,  # Should be capped at 8.0 due to is_restricted
                    "confidence": 0.9,
                    "functions": ["preservative"],
                    "summary": {"en": "Preserves formula.", "fr": "Conserve la formule."},
                    "concern_note": None,
                    "aliases": [],
                },
                {
                    "inci": "Test Benign Z",
                    "rating": 9.0,
                    "confidence": 0.95,
                    "functions": ["humectant"],
                    "summary": {"en": "Hydrates skin.", "fr": "Hydrate la peau."},
                    "concern_note": None,
                    "aliases": [{"name": "Z-Extract", "language": "en"}],
                },
            ]
        },
    )

    secondary_fake = FakeLLMClient(
        provider="fake_secondary",
        default_response={
            "ingredients": [
                {
                    "inci": "Test Restricted Y",
                    "rating": 8.5,
                    "confidence": 0.85,
                    "functions": ["preservative"],
                    "summary": {"en": "Preserves.", "fr": "Conserve."},
                    "concern_note": None,
                    "aliases": [],
                },
                {
                    "inci": "Test Benign Z",
                    "rating": 9.0,
                    "confidence": 0.95,
                    "functions": ["humectant"],
                    "summary": {"en": "Hydrates.", "fr": "Hydrate."},
                    "concern_note": None,
                    "aliases": [],
                },
            ]
        },
    )

    router = LLMRouter(
        settings=fake_settings,
        clients={"fake_primary": primary_fake, "fake_secondary": secondary_fake},
    )
    service = EnrichmentService(db_session, router=router, settings=fake_settings)

    # 3. Execute rating pipeline
    count = await service.rate_ingredients(
        [prohibited.id, restricted.id, benign.id],
        second_opinion=True,
    )
    assert count == 3

    # 4. Verify results
    # Prohibited -> 0.5 regulatory
    await db_session.refresh(prohibited)
    assert prohibited.rating == Decimal("0.5")
    assert prohibited.rating_source == RatingSource.REGULATORY

    # Restricted -> capped at 8.0
    await db_session.refresh(restricted)
    assert restricted.rating == Decimal("8.0")
    assert restricted.rating_source == RatingSource.AI

    # Benign -> consensus rating 9.0, confidence 0.95
    await db_session.refresh(benign)
    assert benign.rating == Decimal("9.0")
    assert benign.rating_confidence == Decimal("0.95")
    assert benign.review_status == ReviewStatus.AUTO

    # Check alias was stored
    alias_stmt = select(IngredientAlias).where(IngredientAlias.alias == "Z-Extract")
    alias_row = (await db_session.execute(alias_stmt)).scalar_one_or_none()
    assert alias_row is not None
    assert alias_row.ingredient_id == benign.id


@pytest.mark.asyncio
async def test_adjudicate_aliases_end_to_end(
    db_session: AsyncSession,
    fake_settings: Settings,
) -> None:
    # Create canonical ingredient
    niacinamide = Ingredient(
        inci_name="Niacinamide",
        rating=Decimal("8.5"),
        rating_source=RatingSource.CURATED,
    )
    db_session.add(niacinamide)
    await db_session.flush()

    # Add existing alias so suggest() finds it
    db_session.add(
        IngredientAlias(
            ingredient_id=niacinamide.id,
            alias="Niacinamide",
            normalized_alias="niacinamide",
        )
    )
    await db_session.flush()

    # Fake LLM response for alias adjudication
    fake_client = FakeLLMClient(
        provider="fake_primary",
        default_response={
            "adjudications": [
                {
                    "token": "Niacinamid",
                    "matched_candidate": "Niacinamide",
                    "confidence": 0.95,
                    "reason": "German/Dutch spelling of Niacinamide",
                }
            ]
        },
    )

    router = LLMRouter(
        settings=fake_settings,
        clients={"fake_primary": fake_client, "fake_secondary": fake_client},
    )
    service = EnrichmentService(db_session, router=router, settings=fake_settings)

    count = await service.adjudicate_aliases(["Niacinamid"], confidence_threshold=0.8)
    assert count == 1

    # Verify alias added to DB
    alias_stmt = select(IngredientAlias).where(IngredientAlias.alias == "Niacinamid")
    alias_row = (await db_session.execute(alias_stmt)).scalar_one_or_none()
    assert alias_row is not None
    assert alias_row.ingredient_id == niacinamide.id

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, ProductUpsert
from app.modules.catalog.enums import EnrichmentStatus, ProductSource
from app.modules.enrichment import (
    EnrichmentService,
    FakeLLMClient,
    LLMRouter,
)
from app.modules.ingestion import IngestionService, RawRecord, store_raw_product
from app.modules.ingestion.enums import QuarantineStatus, RawProductSource
from app.modules.ingestion.tasks import enrich_raw_product_task


@pytest.mark.asyncio
async def test_upsert_product_provenance_precedence(db_session: AsyncSession) -> None:
    catalog = CatalogService(db_session)
    barcode = "1234567890123"

    # 1. First insert with curated source
    curated_dto = ProductUpsert(
        barcode=barcode,
        name="Curated Face Cream",
        source=ProductSource.MANUAL,
        source_id="curated-1",
        field_provenance={"name": {"source": "curated", "confidence": 1.0}},
        enrichment_status=EnrichmentStatus.DONE,
    )
    prod1 = await catalog.upsert_product(curated_dto)
    assert prod1.name == "Curated Face Cream"
    assert prod1.score_dirty is True

    # 2. Try to overwrite name with AI source (lower precedence)
    ai_dto = ProductUpsert(
        barcode=barcode,
        name="AI Overwrite Attempt",
        source=ProductSource.OPEN_BEAUTY_FACTS,
        source_id="obf-1",
        field_provenance={"name": {"source": "ai", "confidence": 0.95}},
        enrichment_status=EnrichmentStatus.DONE,
    )
    prod2 = await catalog.upsert_product(ai_dto)
    # Name MUST remain the curated name
    assert prod2.name == "Curated Face Cream"
    assert prod2.field_provenance is not None
    assert prod2.field_provenance["name"]["source"] == "curated"


@pytest.mark.asyncio
async def test_enrich_product_validation_rules(db_session: AsyncSession) -> None:
    # Set up FakeLLMClient with different responses
    fake_llm = FakeLLMClient()
    router = LLMRouter(clients={"fake": fake_llm})
    router.get_chain = lambda task: ["fake"]  # type: ignore[method-assign]
    enrichment = EnrichmentService(db_session, router=router)

    # 1. Non-skincare LLM result -> FAILED with not_skincare
    fake_llm.add_response(
        {
            "is_skincare": False,
            "is_skincare_confidence": 0.9,
            "name_clean": "Effaclar Duo+",
            "name_i18n": {},
            "source_lang": "en",
            "ingredients_inci": [
                {"original": "Aqua", "inci": "AQUA"},
                {"original": "Glycerin", "inci": "GLYCERIN"},
            ],
            "ingredients_confidence": 0.9,
            "flags": [],
        }
    )
    res_non_skincare = await enrichment.enrich_product(
        {"barcode": "1111111111111", "name": "Test 1", "raw_ingredients_text": "Aqua, Glycerin"}
    )
    assert res_non_skincare.status == EnrichmentStatus.FAILED
    assert res_non_skincare.reason == "not_skincare"

    # 2. Insufficient ingredients (< 2) -> QUARANTINED
    fake_llm.add_response(
        {
            "is_skincare": True,
            "is_skincare_confidence": 0.95,
            "name_clean": "Effaclar Duo+",
            "name_i18n": {},
            "source_lang": "en",
            "ingredients_inci": [{"original": "Aqua", "inci": "AQUA"}],
            "ingredients_confidence": 0.9,
            "flags": [],
        }
    )
    res_few_ing = await enrichment.enrich_product(
        {"barcode": "2222222222222", "name": "Test 2", "raw_ingredients_text": "Aqua"}
    )
    assert res_few_ing.status == EnrichmentStatus.QUARANTINED
    assert res_few_ing.reason == "insufficient_ingredients"

    # 3. Jaccard parser disagreement (< 0.5) -> QUARANTINED
    fake_llm.add_response(
        {
            "is_skincare": True,
            "is_skincare_confidence": 0.95,
            "name_clean": "Effaclar Duo+",
            "name_i18n": {},
            "source_lang": "en",
            "ingredients_inci": [
                {"original": "Petrolatum", "inci": "PETROLATUM"},
                {"original": "Mineral Oil", "inci": "MINERAL OIL"},
            ],
            "ingredients_confidence": 0.9,
            "flags": [],
        }
    )
    res_disagree = await enrichment.enrich_product(
        {
            "barcode": "3333333333333",
            "name": "Test 3",
            "raw_ingredients_text": "Aqua, Glycerin, Niacinamide",
        }
    )
    assert res_disagree.status == EnrichmentStatus.QUARANTINED
    assert res_disagree.reason == "parser_llm_disagree"

    # 4. Valid result -> DONE
    fake_llm.add_response(
        {
            "is_skincare": True,
            "is_skincare_confidence": 0.95,
            "name_clean": "Effaclar Duo+",
            "name_i18n": {"fr": "Effaclar Duo+"},
            "source_lang": "en",
            "ingredients_inci": [
                {"original": "Aqua", "inci": "AQUA"},
                {"original": "Glycerin", "inci": "GLYCERIN"},
                {"original": "Dimethicone", "inci": "DIMETHICONE"},
                {"original": "Niacinamide", "inci": "NIACINAMIDE"},
            ],
            "ingredients_confidence": 0.95,
            "flags": [],
        }
    )
    res_valid = await enrichment.enrich_product(
        {
            "barcode": "4444444444444",
            "name": "Test 4",
            "raw_ingredients_text": "Aqua, Glycerin, Dimethicone, Niacinamide",
        }
    )
    assert res_valid.status == EnrichmentStatus.DONE
    assert res_valid.result is not None
    assert len(res_valid.result.ingredients_inci) == 4


@pytest.mark.asyncio
async def test_enrich_raw_product_task_quarantine_flow(db_session: AsyncSession) -> None:
    fake_llm = FakeLLMClient()
    # Queue a response that triggers quarantine
    fake_llm.add_response(
        {
            "is_skincare": False,
            "is_skincare_confidence": 0.9,
            "name_clean": "Motor Oil",
            "name_i18n": {},
            "source_lang": "en",
            "ingredients_inci": [
                {"original": "Oil", "inci": "OIL"},
                {"original": "Additive", "inci": "ADDITIVE"},
            ],
            "ingredients_confidence": 0.9,
            "flags": [],
        }
    )

    payload = {
        "code": "5000000000001",
        "product_name": "Motor Oil",
        "ingredients_text": "Oil, Additive",
    }
    raw = await store_raw_product(
        db_session,
        RawRecord(
            source=RawProductSource.OPEN_BEAUTY_FACTS.value,
            source_id="5000000000001",
            content_hash="hash-quarantine-1",
            payload=payload,
        ),
    )

    # Monkeypatch or pass router via service:
    # enrich_raw_product_task instantiates EnrichmentService(session) which uses default router.
    # We can inject fake_llm by patching EnrichmentService router or setting FakeLLMClient.
    from unittest.mock import patch

    fake_json_fn = enrichment_service_fake_json(fake_llm)
    with (
        patch("app.modules.enrichment.service.LLMRouter.get_chain", return_value=["fake"]),
        patch.object(EnrichmentService, "generate_json", side_effect=fake_json_fn),
    ):
        await enrich_raw_product_task({"raw_product_id": str(raw)}, db_session)

    ingestion_service = IngestionService(db_session)
    quarantined = await ingestion_service.list_quarantine(status=QuarantineStatus.PENDING)
    matches = [q for q in quarantined if q.raw_product_id == raw]
    assert len(matches) == 1
    assert matches[0].reason == "not_skincare"


def enrichment_service_fake_json(
    fake_client: FakeLLMClient,
) -> Callable[..., Awaitable[tuple[Any, dict[str, str]]]]:
    async def fake_generate_json(**kwargs: Any) -> tuple[Any, dict[str, str]]:
        schema = kwargs["schema"]
        resp = fake_client._responses.pop(0)
        return schema.model_validate(resp), {"model": "fake", "provider": "fake"}

    return fake_generate_json

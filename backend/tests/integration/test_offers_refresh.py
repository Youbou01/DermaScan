"""Integration tests for refreshing offers (refresh function, repository, background task)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.jobs import Job, JobStatus, enqueue_job, run_pending_jobs
from app.modules.catalog.models import Product
from app.modules.offers import tasks as offers_tasks
from app.modules.offers.refresh import refresh_product_offers
from app.modules.offers.repository import OfferRepository
from app.modules.offers.sources import (
    FIXTURE_NO_OFFERS,
    FIXTURE_NORMAL,
    FIXTURE_STALE,
    FixtureAdapter,
    PriceSourceAdapter,
    RawOffer,
)
from tests.factories import make_product

pytestmark = pytest.mark.usefixtures("migrated_database")

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


class _OnePrice:
    """Test source with one shop whose price we control."""

    def __init__(self, price: str) -> None:
        self._price = Decimal(price)

    async def fetch_offers(self, barcode: str, product_name: str) -> list[RawOffer]:
        return [
            RawOffer(
                retailer_name="Shop A",
                retailer_domain="shop-a.example",
                price=self._price,
                currency="EUR",
                url=f"https://shop-a.example/p/{barcode}",
            )
        ]


class _FailingSource:
    """Test source that always fails, like a real source outage."""

    async def fetch_offers(self, barcode: str, product_name: str) -> list[RawOffer]:
        raise RuntimeError("source is down")


async def _product(session: AsyncSession, barcode: str) -> Product:
    product = make_product(barcode=barcode)
    session.add(product)
    await session.flush()
    return product


async def _refresh(
    session: AsyncSession,
    product: Product,
    adapter: PriceSourceAdapter,
    now: datetime = NOW,
) -> int:
    return await refresh_product_offers(
        session,
        product_id=product.id,
        barcode=product.barcode,
        product_name=product.name,
        adapter=adapter,
        source="fixture",
        now=now,
    )


async def test_refresh_stores_offers_and_retailers(db_session: AsyncSession) -> None:
    product = await _product(db_session, FIXTURE_NORMAL)

    stored = await _refresh(db_session, product, FixtureAdapter())

    rows = await OfferRepository(db_session).list_for_product(product.id)
    assert stored == 3
    assert [offer.price for offer, _ in rows] == [
        Decimal("12.00"),
        Decimal("15.50"),
        Decimal("20.00"),
    ]
    assert {offer.source for offer, _ in rows} == {"fixture"}
    assert {offer.last_checked_at for offer, _ in rows} == {NOW}
    assert {retailer.domain for _, retailer in rows} == {
        "shop-a.example",
        "shop-b.example",
        "shop-c.example",
    }


async def test_refresh_twice_changes_only_last_checked_at(db_session: AsyncSession) -> None:
    product = await _product(db_session, FIXTURE_NORMAL)
    repository = OfferRepository(db_session)
    await _refresh(db_session, product, FixtureAdapter())
    before = [
        (offer.id, offer.price, offer.content_hash)
        for offer, _ in await repository.list_for_product(product.id)
    ]

    later = NOW + timedelta(hours=1)
    await _refresh(db_session, product, FixtureAdapter(), now=later)

    rows = await repository.list_for_product(product.id)
    assert [(offer.id, offer.price, offer.content_hash) for offer, _ in rows] == before
    assert {offer.last_checked_at for offer, _ in rows} == {later}


async def test_changed_price_updates_the_same_row(db_session: AsyncSession) -> None:
    product = await _product(db_session, FIXTURE_NORMAL)
    repository = OfferRepository(db_session)
    await _refresh(db_session, product, _OnePrice("10.00"))
    [(first, _)] = await repository.list_for_product(product.id)
    first_id, first_hash = first.id, first.content_hash

    await _refresh(db_session, product, _OnePrice("8.00"), now=NOW + timedelta(hours=1))

    [(second, _)] = await repository.list_for_product(product.id)
    assert second.id == first_id
    assert second.price == Decimal("8.00")
    assert second.content_hash != first_hash


async def test_failing_source_keeps_existing_offers(db_session: AsyncSession) -> None:
    product = await _product(db_session, FIXTURE_NORMAL)
    await _refresh(db_session, product, FixtureAdapter())

    stored = await _refresh(db_session, product, _FailingSource(), now=NOW + timedelta(days=3))

    rows = await OfferRepository(db_session).list_for_product(product.id)
    assert stored == 0
    assert len(rows) == 3
    assert {offer.last_checked_at for offer, _ in rows} == {NOW}


async def test_stale_demo_offer_is_ten_days_old(db_session: AsyncSession) -> None:
    product = await _product(db_session, FIXTURE_STALE)

    await _refresh(db_session, product, FixtureAdapter())

    rows = await OfferRepository(db_session).list_for_product(product.id)
    assert sorted(NOW - offer.last_checked_at for offer, _ in rows) == [
        timedelta(0),
        timedelta(days=10),
    ]


async def test_product_without_offers_stores_nothing(db_session: AsyncSession) -> None:
    product = await _product(db_session, FIXTURE_NO_OFFERS)

    stored = await _refresh(db_session, product, FixtureAdapter())

    assert stored == 0
    assert await OfferRepository(db_session).list_for_product(product.id) == []


async def test_task_refreshes_offers_with_the_fixture_source(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings().model_copy(update={"price_source": "fixture"})
    monkeypatch.setattr(offers_tasks, "get_settings", lambda: settings)
    product = await _product(db_session, FIXTURE_NORMAL)
    await enqueue_job(db_session, "refresh_offers", {"product_id": str(product.id)})

    executed = await run_pending_jobs(db_session, queue="default")

    assert executed == 1
    rows = await OfferRepository(db_session).list_for_product(product.id)
    assert len(rows) == 3


async def test_task_does_not_fail_for_an_unknown_product(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings().model_copy(update={"price_source": "fixture"})
    monkeypatch.setattr(offers_tasks, "get_settings", lambda: settings)
    job_id = await enqueue_job(db_session, "refresh_offers", {"product_id": str(uuid.uuid4())})

    executed = await run_pending_jobs(db_session, queue="default")

    job = await db_session.get(Job, job_id)
    assert job is not None
    await db_session.refresh(job)
    assert executed == 1
    assert job.status == JobStatus.COMPLETED


async def test_task_with_unsupported_source_stores_nothing_and_completes(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings().model_copy(update={"price_source": "serpapi"})
    monkeypatch.setattr(offers_tasks, "get_settings", lambda: settings)
    product = await _product(db_session, FIXTURE_NORMAL)
    job_id = await enqueue_job(db_session, "refresh_offers", {"product_id": str(product.id)})

    await run_pending_jobs(db_session, queue="default")

    job = await db_session.get(Job, job_id)
    assert job is not None
    await db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert await OfferRepository(db_session).list_for_product(product.id) == []

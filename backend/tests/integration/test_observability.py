from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.jobs import Job, JobStatus, execute_job, register_task
from app.core.metrics import REGISTRY, record_llm_request
from app.main import create_app


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_data() -> None:
    settings = Settings(app_env="test")
    app = create_app(settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request health live endpoint
        await client.get("/health/live")

        # Request /metrics
        res = await client.get("/metrics")
        assert res.status_code == 200
        assert "text/plain" in res.headers["content-type"]
        body = res.text
        assert "dermascan_http_requests_total" in body
        assert 'endpoint="/health/live"' in body


@pytest.mark.asyncio
async def test_admin_metrics_summary_endpoint(db_session: AsyncSession) -> None:
    settings = Settings(app_env="test", admin_api_key="secret-key")
    app = create_app(settings)
    from app.core.dependencies import get_session

    app.dependency_overrides[get_session] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            "/admin/metrics/summary",
            headers={"X-Admin-Key": "secret-key"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "jobs" in data
        assert "quarantine" in data


@pytest.mark.asyncio
async def test_job_execution_metric_recording(db_session: AsyncSession) -> None:
    @register_task("test_observability_task")
    async def dummy_task(payload: dict[str, Any], session: AsyncSession) -> None:
        pass

    job = Job(
        queue="default",
        task_name="test_observability_task",
        payload={"dummy": True},
        status=JobStatus.RUNNING,
    )
    db_session.add(job)
    await db_session.flush()

    ok = await execute_job(db_session, job)
    assert ok is True
    assert job.status == JobStatus.COMPLETED

    val = REGISTRY.get_sample_value(
        "dermascan_job_status_total",
        {"queue": "default", "task_name": "test_observability_task", "status": "completed"},
    )
    assert val is not None
    assert val >= 1.0


def test_llm_metrics_recording() -> None:
    record_llm_request(provider="fake_provider", task="enrich", outcome="success", latency_s=0.25)
    val = REGISTRY.get_sample_value(
        "dermascan_llm_requests_total",
        {"provider": "fake_provider", "task": "enrich", "outcome": "success"},
    )
    assert val is not None
    assert val >= 1.0

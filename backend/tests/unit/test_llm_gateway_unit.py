import pytest

from app.modules.enrichment.llm.cache import compute_cache_key
from app.modules.enrichment.llm.client import LLMRateLimitError
from app.modules.enrichment.llm.ratelimit import InMemoryTokenBucket, RateLimiterRegistry


def test_compute_cache_key_deterministic() -> None:
    k1 = compute_cache_key("enrich", 1, 1, "Water, Glycerin")
    k2 = compute_cache_key("enrich", 1, 1, "Water, Glycerin")
    assert k1 == k2
    assert len(k1) == 64

    # Different prompt or version changes key
    k3 = compute_cache_key("enrich", 2, 1, "Water, Glycerin")
    assert k1 != k3


def test_in_memory_token_bucket() -> None:
    bucket = InMemoryTokenBucket(rpm=60)
    assert bucket.acquire(1.0) is True

    exhausted_bucket = InMemoryTokenBucket(rpm=1)
    assert exhausted_bucket.acquire(1.0) is True
    assert exhausted_bucket.acquire(1.0) is False


def test_rate_limiter_registry() -> None:
    RateLimiterRegistry.check_rate_limit("test_prov", rpm=60)
    # Check that rate limiter error is raised if exhausted
    low_bucket = InMemoryTokenBucket(rpm=1)
    low_bucket.acquire(1.0)
    RateLimiterRegistry._buckets["limited_prov"] = low_bucket

    with pytest.raises(LLMRateLimitError):
        RateLimiterRegistry.check_rate_limit("limited_prov", rpm=1)

"""Prometheus observability and application metrics."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS_TOTAL = Counter(
    "dermascan_http_requests_total",
    "Total count of HTTP requests handled by the API",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "dermascan_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    registry=REGISTRY,
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

JOB_STATUS_TOTAL = Counter(
    "dermascan_job_status_total",
    "Count of asynchronous jobs executed by queue, task, and status",
    ["queue", "task_name", "status"],
    registry=REGISTRY,
)

JOB_DURATION_SECONDS = Histogram(
    "dermascan_job_duration_seconds",
    "Asynchronous job execution duration in seconds",
    ["queue", "task_name"],
    registry=REGISTRY,
    buckets=(0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

LLM_REQUESTS_TOTAL = Counter(
    "dermascan_llm_requests_total",
    "Count of LLM gateway invocations by provider, task, and outcome",
    ["provider", "task", "outcome"],
    registry=REGISTRY,
)

LLM_LATENCY_SECONDS = Histogram(
    "dermascan_llm_latency_seconds",
    "LLM call latency in seconds",
    ["provider", "task"],
    registry=REGISTRY,
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0),
)

QUARANTINE_ITEMS_TOTAL = Gauge(
    "dermascan_quarantine_items_total",
    "Current number of pending items in the quarantine queue",
    ["stage"],
    registry=REGISTRY,
)


def normalize_endpoint(path: str) -> str:
    """Normalize request path into a template string to keep metric label cardinality low."""
    if path.startswith("/api/v1/products/by-barcode/"):
        return "/api/v1/products/by-barcode/:barcode"
    if path.startswith("/api/v1/products/search"):
        return "/api/v1/products/search"
    if path.startswith("/api/v1/products/"):
        return "/api/v1/products/:id"
    if path.startswith("/api/v1/home/sections/"):
        return "/api/v1/home/sections/:section_id"
    if path.startswith("/admin/review/quarantine/"):
        return "/admin/review/quarantine/:id"
    if path.startswith("/admin/ingredients/"):
        return "/admin/ingredients/:id"
    return path


def record_http_request(method: str, endpoint: str, status_code: int, duration_s: float) -> None:
    """Record an HTTP request execution."""
    norm_ep = normalize_endpoint(endpoint)
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=norm_ep, status_code=str(status_code)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=norm_ep).observe(duration_s)


def record_job_execution(queue: str, task_name: str, status: str, duration_s: float) -> None:
    """Record a background job execution outcome and duration."""
    JOB_STATUS_TOTAL.labels(queue=queue, task_name=task_name, status=status).inc()
    JOB_DURATION_SECONDS.labels(queue=queue, task_name=task_name).observe(duration_s)


def record_llm_request(provider: str, task: str, outcome: str, latency_s: float = 0.0) -> None:
    """Record an LLM provider request outcome and latency."""
    LLM_REQUESTS_TOTAL.labels(provider=provider, task=task, outcome=outcome).inc()
    if latency_s > 0:
        LLM_LATENCY_SECONDS.labels(provider=provider, task=task).observe(latency_s)


def set_quarantine_count(stage: str, count: int) -> None:
    """Set the current quarantine queue size for a given stage."""
    QUARANTINE_ITEMS_TOTAL.labels(stage=stage).set(count)


def generate_metrics() -> bytes:
    """Generate the latest Prometheus formatted metrics payload."""
    return generate_latest(REGISTRY)


__all__ = [
    "CONTENT_TYPE_LATEST",
    "REGISTRY",
    "generate_metrics",
    "normalize_endpoint",
    "record_http_request",
    "record_job_execution",
    "record_llm_request",
    "set_quarantine_count",
]

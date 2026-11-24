"""Asynchronous Reddit public search adapter for external product reviews."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus

import httpx
import structlog

logger = structlog.get_logger(__name__)

REDDIT_SEARCH_URL = (
    "https://www.reddit.com/r/SkincareAddiction/search.json"
    "?q={query}&restrict_sr=1&sort=relevance&limit={limit}"
)
REDDIT_USER_AGENT = "DermaScan/1.0 (academic skincare analysis platform)"


@dataclass(frozen=True, slots=True)
class ExternalReviewRecord:
    external_id: str
    author_name: str
    body: str
    external_url: str | None
    created_at: datetime
    rating: int | None = None


def normalize_reddit_posts(payload: dict[str, Any]) -> list[ExternalReviewRecord]:
    """Pure parser turning Reddit listing JSON into normalized review records."""
    children = payload.get("data", {}).get("children", [])
    if not isinstance(children, list):
        return []

    records: list[ExternalReviewRecord] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        post = child.get("data")
        if not isinstance(post, dict):
            continue
        post_id = str(post.get("id") or "").strip()
        title = str(post.get("title") or "").strip()
        selftext = str(post.get("selftext") or "").strip()
        text = f"{title}\n{selftext}".strip() if selftext else title
        if not post_id or len(text) < 10:
            continue
        author = str(post.get("author") or "reddit_user").strip()
        permalink = str(post.get("permalink") or "").strip()
        url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else None
        created_utc = post.get("created_utc")
        created_at = (
            datetime.fromtimestamp(float(created_utc), tz=UTC)
            if isinstance(created_utc, (int, float))
            else datetime.now(UTC)
        )
        records.append(
            ExternalReviewRecord(
                external_id=post_id[:128],
                author_name=f"u/{author}"[:120],
                body=text[:2000],
                external_url=url,
                created_at=created_at,
                rating=None,
            )
        )
    return records


class RedditReviewsAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 5.0) -> None:
        self._client = client
        self._timeout = timeout

    async def fetch_reviews(
        self, query: str, *, limit: int = 5
    ) -> tuple[list[ExternalReviewRecord], dict[str, Any]]:
        clean_query = query.strip()
        if not clean_query:
            return [], {}
        url = REDDIT_SEARCH_URL.format(query=quote_plus(clean_query), limit=limit)
        headers = {"User-Agent": REDDIT_USER_AGENT, "Accept": "application/json"}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            payload: dict[str, Any] = resp.json()
            return normalize_reddit_posts(payload), payload
        finally:
            if owns_client:
                await client.aclose()

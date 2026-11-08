"""In-memory sliding window rate limiting middleware for public API endpoints."""

import json
import time
from collections import defaultdict

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings, get_settings


class RateLimitMiddleware:
    """Sliding-window IP rate limiter returning RFC 9457 problem details when exhausted."""

    def __init__(self, app: ASGIApp, settings: Settings | None = None) -> None:
        self.app = app
        self._settings = settings
        # Mapping: ip -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def _cleanup_old_records(self, now: float) -> None:
        """Purge entries older than 60s every 30s to prevent unbounded memory growth."""
        if now - self._last_cleanup < 30.0:
            return
        self._last_cleanup = now
        cutoff = now - 60.0
        expired_ips = []
        for ip, timestamps in self._requests.items():
            self._requests[ip] = [ts for ts in timestamps if ts > cutoff]
            if not self._requests[ip]:
                expired_ips.append(ip)
        for ip in expired_ips:
            self._requests.pop(ip, None)

    def _get_client_ip(self, scope: Scope) -> str:
        headers = Headers(scope=scope)
        x_forwarded_for = headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        client = scope.get("client")
        if client:
            return str(client[0])
        return "127.0.0.1"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Only apply rate limiting to public /api/v1/ endpoints
        path: str = scope["path"]
        if not path.startswith("/api/v1"):
            await self.app(scope, receive, send)
            return

        if not self.settings.enable_rate_limiting:
            await self.app(scope, receive, send)
            return

        now = time.monotonic()
        self._cleanup_old_records(now)

        client_ip = self._get_client_ip(scope)
        limit = self.settings.rate_limit_rpm
        window = 60.0
        cutoff = now - window

        # Keep timestamps within the sliding 60s window
        timestamps = [ts for ts in self._requests[client_ip] if ts > cutoff]
        if len(timestamps) >= limit:
            retry_after = int(window - (now - timestamps[0])) + 1
            problem_body = json.dumps(
                {
                    "type": "urn:skincare:problem:rate-limit-exceeded",
                    "title": "Too many requests",
                    "status": 429,
                    "detail": (
                        f"Rate limit of {limit} req/min exceeded. Retry after {retry_after}s."
                    ),
                    "instance": path,
                }
            ).encode("utf-8")

            res_headers: list[tuple[bytes, bytes]] = [
                (b"content-type", b"application/problem+json"),
                (b"retry-after", str(retry_after).encode("latin-1")),
                (b"x-ratelimit-limit", str(limit).encode("latin-1")),
                (b"x-ratelimit-remaining", b"0"),
            ]
            req_id = scope.get("state", {}).get("request_id")
            if req_id:
                res_headers.append((b"x-request-id", req_id.encode("latin-1")))

            start_msg: Message = {
                "type": "http.response.start",
                "status": 429,
                "headers": res_headers,
            }
            await send(start_msg)
            await send({"type": "http.response.body", "body": problem_body, "more_body": False})
            return

        timestamps.append(now)
        self._requests[client_ip] = timestamps
        await self.app(scope, receive, send)

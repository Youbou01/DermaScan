"""HTTP Caching middleware: ETag generation, Cache-Control, and 304 Not Modified handling."""

import hashlib

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class HttpCacheMiddleware:
    """Pure ASGI middleware providing conditional ETag caching and Cache-Control headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    def _get_cache_policy(self, path: str) -> tuple[int, int] | None:
        """Returns (max_age, stale_while_revalidate) for cacheable endpoints."""
        if path.startswith("/api/v1/categories"):
            return 3600, 300
        if path.startswith("/api/v1/home"):
            return 300, 60
        if path.startswith("/api/v1/products"):
            return 300, 60
        return None

    def _match_etag(self, if_none_match: str, etag: str) -> bool:
        """Compare client If-None-Match against current entity tag."""
        if if_none_match == "*":
            return True
        tags = [t.strip() for t in if_none_match.split(",")]
        clean_etag = etag.strip()
        weak_etag = f"W/{clean_etag}" if not clean_etag.startswith("W/") else clean_etag
        raw_etag = clean_etag[2:] if clean_etag.startswith("W/") else clean_etag

        for candidate in tags:
            c = candidate.strip()
            if c in (clean_etag, weak_etag, raw_etag):
                return True
            if c.strip('"') == raw_etag.strip('"'):
                return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in ("GET", "HEAD"):
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]
        policy = self._get_cache_policy(path)
        if policy is None:
            await self.app(scope, receive, send)
            return

        req_headers = Headers(scope=scope)
        req_cache_control = req_headers.get("cache-control", "")
        if "no-cache" in req_cache_control or "no-store" in req_cache_control:
            await self.app(scope, receive, send)
            return

        status_code = 200
        response_start_message: Message = {}
        body_parts: list[bytes] = []

        async def capture_send(message: Message) -> None:
            nonlocal status_code, response_start_message
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_start_message = message
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))
                if not message.get("more_body", False):
                    await self._handle_complete_response(
                        scope=scope,
                        send=send,
                        status_code=status_code,
                        start_msg=response_start_message,
                        body=b"".join(body_parts),
                        policy=policy,
                    )

        await self.app(scope, receive, capture_send)

    async def _handle_complete_response(
        self,
        scope: Scope,
        send: Send,
        status_code: int,
        start_msg: Message,
        body: bytes,
        policy: tuple[int, int],
    ) -> None:
        if status_code != 200:
            await send(start_msg)
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return

        etag = f'"{hashlib.sha256(body).hexdigest()[:32]}"'
        max_age, stale = policy
        cache_control_val = f"public, max-age={max_age}, stale-while-revalidate={stale}"

        req_headers = Headers(scope=scope)
        if_none_match = req_headers.get("if-none-match")

        if if_none_match and self._match_etag(if_none_match, etag):
            # Client has fresh copy: return 304 Not Modified
            res_headers = [
                (b"etag", etag.encode("latin-1")),
                (b"cache-control", cache_control_val.encode("latin-1")),
                (b"vary", b"Accept-Language, Accept-Encoding"),
            ]
            req_id = scope.get("state", {}).get("request_id")
            if req_id:
                res_headers.append((b"x-request-id", req_id.encode("latin-1")))

            await send(
                {
                    "type": "http.response.start",
                    "status": 304,
                    "headers": res_headers,
                }
            )
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        headers = MutableHeaders(scope=start_msg)
        if "etag" not in headers:
            headers["etag"] = etag
        if "cache-control" not in headers:
            headers["cache-control"] = cache_control_val
        if "vary" not in headers:
            headers["vary"] = "Accept-Language, Accept-Encoding"

        await send(start_msg)
        if scope["method"] == "HEAD":
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        else:
            await send({"type": "http.response.body", "body": body, "more_body": False})

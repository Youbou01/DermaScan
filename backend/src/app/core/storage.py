"""Storage client protocol and implementations for product images.

Follows Section 6.2: S3-compatible API with MinIO/S3 and local/in-memory fallbacks.
"""

import hashlib
import hmac
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import httpx
import structlog

from app.core.config import Settings, get_settings

logger = structlog.get_logger(__name__)


def _sign_s3_v4(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: bytes,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
) -> dict[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc
    uri = parsed.path or "/"
    now = datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(payload).hexdigest()

    signed_headers_map: dict[str, str] = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    if "Content-Type" in headers:
        signed_headers_map["content-type"] = headers["Content-Type"]

    sorted_keys = sorted(signed_headers_map.keys())
    canonical_headers = "".join(f"{k}:{signed_headers_map[k]}\n" for k in sorted_keys)
    signed_headers_str = ";".join(sorted_keys)

    canonical_request = "\n".join(
        [
            method.upper(),
            uri,
            parsed.query,
            canonical_headers,
            signed_headers_str,
            payload_hash,
        ]
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{datestamp}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            algorithm,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _hmac(f"AWS4{secret_key}".encode(), datestamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, "s3")
    k_signing = _hmac(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    auth_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers_str}, Signature={signature}"
    )
    return {
        **headers,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": auth_header,
    }


class StorageClient(Protocol):
    """Protocol for uploading and checking binary assets (WebP product images)."""

    @property
    def base_url(self) -> str: ...

    async def put_image(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/webp",
    ) -> str:
        """Upload asset bytes at `key` and return the public CDN URL."""
        ...

    async def get_image(self, key: str) -> bytes | None:
        """Retrieve asset bytes if present, else None."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if an asset exists at `key`."""
        ...


class InMemoryStorageClient:
    """Fast, in-memory storage client for unit and offline tests."""

    def __init__(self, base_url: str = "http://localhost:9000/dermascan") -> None:
        self._base_url = base_url.rstrip("/")
        self._files: dict[str, tuple[bytes, str]] = {}

    @property
    def base_url(self) -> str:
        return self._base_url

    async def put_image(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/webp",
    ) -> str:
        clean_key = key.lstrip("/")
        self._files[clean_key] = (data, content_type)
        return f"{self._base_url}/{clean_key}"

    async def get_image(self, key: str) -> bytes | None:
        clean_key = key.lstrip("/")
        item = self._files.get(clean_key)
        return item[0] if item else None

    async def exists(self, key: str) -> bool:
        return key.lstrip("/") in self._files


class LocalStorageClient:
    """Local filesystem storage client for development when S3 is unavailable."""

    def __init__(
        self,
        base_dir: Path | str = "uploads",
        base_url: str = "http://localhost:9000/dermascan",
    ) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._base_url = base_url.rstrip("/")

    @property
    def base_url(self) -> str:
        return self._base_url

    async def put_image(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/webp",
    ) -> str:
        clean_key = key.lstrip("/")
        dest = self._base_dir / clean_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return f"{self._base_url}/{clean_key}"

    async def get_image(self, key: str) -> bytes | None:
        clean_key = key.lstrip("/")
        dest = self._base_dir / clean_key
        if dest.exists() and dest.is_file():
            return dest.read_bytes()
        return None

    async def exists(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        dest = self._base_dir / clean_key
        return dest.exists() and dest.is_file()


class S3StorageClient:
    """Async S3 / MinIO client using HTTP REST API."""

    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self._endpoint_url = endpoint_url.rstrip("/")
        self._bucket = bucket
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._access_key = access_key or "minioadmin"
        self._secret_key = secret_key or "minioadmin"

    @property
    def base_url(self) -> str:
        return self._base_url

    async def _ensure_bucket(self, cli: httpx.AsyncClient) -> None:
        bucket_url = f"{self._endpoint_url}/{self._bucket}"
        headers = _sign_s3_v4(
            "HEAD",
            bucket_url,
            headers={},
            payload=b"",
            access_key=self._access_key,
            secret_key=self._secret_key,
        )
        try:
            resp = await cli.head(bucket_url, headers=headers)
            if resp.status_code == 404:
                put_headers = _sign_s3_v4(
                    "PUT",
                    bucket_url,
                    headers={},
                    payload=b"",
                    access_key=self._access_key,
                    secret_key=self._secret_key,
                )
                put_resp = await cli.put(bucket_url, headers=put_headers)
                if put_resp.status_code not in (200, 409):
                    logger.warning(
                        "ensure_bucket_failed", status=put_resp.status_code, text=put_resp.text
                    )
        except httpx.HTTPError as exc:
            logger.warning("ensure_bucket_http_error", error=str(exc))

    async def put_image(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/webp",
    ) -> str:
        clean_key = key.lstrip("/")
        target_url = f"{self._endpoint_url}/{self._bucket}/{clean_key}"
        headers = {"Content-Type": content_type}

        owns_client = self._client is None
        cli = self._client or httpx.AsyncClient(timeout=10.0)
        try:
            await self._ensure_bucket(cli)
            signed_headers = _sign_s3_v4(
                method="PUT",
                url=target_url,
                headers=headers,
                payload=data,
                access_key=self._access_key,
                secret_key=self._secret_key,
            )
            resp = await cli.put(target_url, content=data, headers=signed_headers)
            resp.raise_for_status()
            return f"{self._base_url}/{clean_key}"
        finally:
            if owns_client:
                await cli.aclose()

    async def get_image(self, key: str) -> bytes | None:
        clean_key = key.lstrip("/")
        target_url = f"{self._endpoint_url}/{self._bucket}/{clean_key}"
        owns_client = self._client is None
        cli = self._client or httpx.AsyncClient(timeout=10.0)
        try:
            signed_headers = _sign_s3_v4(
                method="GET",
                url=target_url,
                headers={},
                payload=b"",
                access_key=self._access_key,
                secret_key=self._secret_key,
            )
            resp = await cli.get(target_url, headers=signed_headers)
            if resp.status_code == 200:
                return resp.content
            return None
        except httpx.HTTPError:
            return None
        finally:
            if owns_client:
                await cli.aclose()

    async def exists(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        target_url = f"{self._endpoint_url}/{self._bucket}/{clean_key}"
        owns_client = self._client is None
        cli = self._client or httpx.AsyncClient(timeout=10.0)
        try:
            signed_headers = _sign_s3_v4(
                method="HEAD",
                url=target_url,
                headers={},
                payload=b"",
                access_key=self._access_key,
                secret_key=self._secret_key,
            )
            resp = await cli.head(target_url, headers=signed_headers)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
        finally:
            if owns_client:
                await cli.aclose()


_storage_singleton: StorageClient | None = None


def get_storage_client(settings: Settings | None = None) -> StorageClient:
    """Return default storage client based on application configuration."""
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    cfg = settings or get_settings()

    if cfg.app_env == "test":
        _storage_singleton = InMemoryStorageClient(base_url=cfg.image_cdn_base_url)
    elif cfg.s3_endpoint_url:
        _storage_singleton = S3StorageClient(
            endpoint_url=cfg.s3_endpoint_url,
            bucket=cfg.s3_bucket,
            base_url=cfg.image_cdn_base_url,
            access_key=cfg.s3_access_key,
            secret_key=cfg.s3_secret_key,
        )
    else:
        _storage_singleton = LocalStorageClient(base_url=cfg.image_cdn_base_url)

    return _storage_singleton


def set_storage_client(client: StorageClient | None) -> None:
    """Override storage client for tests."""
    global _storage_singleton
    _storage_singleton = client

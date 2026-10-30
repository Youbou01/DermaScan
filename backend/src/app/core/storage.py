"""Storage client protocol and implementations for product images.

Follows Section 6.2: S3-compatible API with MinIO/S3 and local/in-memory fallbacks.
"""

from pathlib import Path
from typing import Protocol

import httpx
import structlog

from app.core.config import Settings, get_settings

logger = structlog.get_logger(__name__)


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
    ) -> None:
        self._endpoint_url = endpoint_url.rstrip("/")
        self._bucket = bucket
        self._base_url = base_url.rstrip("/")
        self._client = client

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
        target_url = f"{self._endpoint_url}/{self._bucket}/{clean_key}"
        headers = {"Content-Type": content_type}

        owns_client = self._client is None
        cli = self._client or httpx.AsyncClient(timeout=10.0)
        try:
            resp = await cli.put(target_url, content=data, headers=headers)
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
            resp = await cli.get(target_url)
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
            resp = await cli.head(target_url)
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
        )
    else:
        _storage_singleton = LocalStorageClient(base_url=cfg.image_cdn_base_url)

    return _storage_singleton


def set_storage_client(client: StorageClient | None) -> None:
    """Override storage client for tests."""
    global _storage_singleton
    _storage_singleton = client

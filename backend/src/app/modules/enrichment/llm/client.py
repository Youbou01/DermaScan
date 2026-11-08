import base64
from dataclasses import dataclass
from typing import Any, Protocol


def detect_image_mime_type(data: bytes | str) -> str:
    """Inspect magic bytes to determine image MIME type (PNG, WebP, GIF, JPEG)."""
    if isinstance(data, str):
        if data.startswith("data:"):
            header, _, rest = data.partition(",")
            if ";base64" in header:
                data = rest
        try:
            head_bytes = base64.b64decode(data[:64])
        except Exception:
            head_bytes = b""
    else:
        head_bytes = data[:32]

    if head_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head_bytes.startswith(b"RIFF") and len(head_bytes) >= 12 and head_bytes[8:12] == b"WEBP":
        return "image/webp"
    if head_bytes.startswith(b"GIF8"):
        return "image/gif"
    return "image/jpeg"


class LLMError(Exception):
    """Base exception for LLM operations."""


class LLMRateLimitError(LLMError):
    """Raised when a provider returns HTTP 429 / rate limited."""


class LLMQuotaExhaustedError(LLMError):
    """Raised when a provider's daily quota or token budget is exhausted."""


class LLMInvalidResponseError(LLMError):
    """Raised when provider returns invalid non-JSON or unparseable output."""


class LLMChainExhaustedError(LLMError):
    """Raised when all candidate providers in a chain failed or are exhausted."""


@dataclass(slots=True, frozen=True)
class LLMResult:
    content: str
    parsed: dict[str, Any] | None
    provider: str
    model: str
    tokens_used: int = 0
    cached: bool = False
    latency_ms: float = 0.0


class LLMClient(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def generate(
        self,
        system: str,
        prompt: str,
        schema: dict[str, Any] | None = None,
        images: list[str] | None = None,
    ) -> LLMResult: ...

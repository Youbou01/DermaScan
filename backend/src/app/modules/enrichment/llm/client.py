from dataclasses import dataclass
from typing import Any, Protocol


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

import json
import time
from typing import Any

import httpx

from app.modules.enrichment.llm.client import (
    LLMClient,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMResult,
)


class OpenAICompatClient(LLMClient):
    """Client for any OpenAI-compatible completions API (Ollama, Groq, Mistral, etc.)."""

    def __init__(
        self,
        provider: str,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._provider = provider
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    async def generate(
        self,
        system: str,
        prompt: str,
        schema: dict[str, Any] | None = None,
        images: list[str] | None = None,
    ) -> LLMResult:
        url = f"{self._base_url}/chat/completions"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        start_time = time.monotonic()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                raise LLMInvalidResponseError(
                    f"HTTP transport error communicating with {self._provider}: {exc}"
                ) from exc

        latency_ms = (time.monotonic() - start_time) * 1000.0

        if response.status_code == 429:
            raise LLMRateLimitError(f"Rate limit exceeded (HTTP 429) for provider {self._provider}")

        if response.status_code >= 400:
            raise LLMInvalidResponseError(
                f"Provider {self._provider} returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMInvalidResponseError(
                f"Malformed response format from {self._provider}: {data}"
            ) from exc

        tokens_used = data.get("usage", {}).get("total_tokens", 0)

        try:
            parsed = json.loads(content)
        except Exception:
            parsed = None

        return LLMResult(
            content=content,
            parsed=parsed if isinstance(parsed, dict) else None,
            provider=self.provider,
            model=self.model,
            tokens_used=tokens_used,
            cached=False,
            latency_ms=latency_ms,
        )

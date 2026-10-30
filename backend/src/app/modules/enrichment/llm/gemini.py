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


class GeminiClient(LLMClient):
    """Client for Google Gemini free-tier REST API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        timeout: float = 60.0,
    ) -> None:
        self._provider = "gemini"
        self._model = model
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
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )

        parts: list[dict[str, Any]] = [{"text": prompt}]
        if images:
            for img in images:
                parts.append(
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": img,
                        }
                    }
                )

        payload: dict[str, Any] = {
            "contents": [{"parts": parts}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }

        start_time = time.monotonic()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.HTTPError as exc:
                raise LLMInvalidResponseError(
                    f"HTTP transport error communicating with Gemini: {exc}"
                ) from exc

        latency_ms = (time.monotonic() - start_time) * 1000.0

        if response.status_code == 429:
            raise LLMRateLimitError("Gemini rate limit exceeded (HTTP 429)")

        if response.status_code >= 400:
            raise LLMInvalidResponseError(
                f"Gemini returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            candidate = data["candidates"][0]
            content = candidate["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMInvalidResponseError(f"Malformed Gemini response: {data}") from exc

        tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 0)

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

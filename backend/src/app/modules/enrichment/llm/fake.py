import json
from collections.abc import Callable
from typing import Any

from app.modules.enrichment.llm.client import (
    LLMClient,
    LLMResult,
)


class FakeLLMClient(LLMClient):
    """Deterministic, offline fake LLM client for testing."""

    def __init__(
        self,
        provider: str = "fake",
        model: str = "fake-model",
        responses: list[dict[str, Any] | str | Exception] | None = None,
        default_response: dict[str, Any] | str | None = None,
        handler: Callable[..., Any] | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._responses: list[dict[str, Any] | str | Exception] = list(responses or [])
        self._default_response = default_response
        self._handler = handler
        self.calls: list[dict[str, Any]] = []

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    def add_response(self, response: dict[str, Any] | str | Exception) -> None:
        self._responses.append(response)

    async def generate(
        self,
        system: str,
        prompt: str,
        schema: dict[str, Any] | None = None,
        images: list[str] | None = None,
    ) -> LLMResult:
        self.calls.append(
            {
                "system": system,
                "prompt": prompt,
                "schema": schema,
                "images": images,
            }
        )

        if self._handler is not None:
            raw = self._handler(system=system, prompt=prompt, schema=schema, images=images)
        elif self._responses:
            raw = self._responses.pop(0)
        elif self._default_response is not None:
            raw = self._default_response
        else:
            schema_title = (schema or {}).get("title", "")
            if schema_title == "OcrIngredientsResult":
                raw = {
                    "ingredients_text": "Aqua, Glycerin, Niacinamide, Sodium Hyaluronate",
                    "confidence": 0.95,
                    "is_readable": True,
                }
            else:
                raw = {"status": "ok"}

        if isinstance(raw, Exception):
            raise raw

        if isinstance(raw, dict):
            content_str = json.dumps(raw)
            parsed_dict = raw
        else:
            content_str = str(raw)
            try:
                parsed_dict = json.loads(content_str)
            except Exception:
                parsed_dict = None

        return LLMResult(
            content=content_str,
            parsed=parsed_dict,
            provider=self.provider,
            model=self.model,
            tokens_used=10,
            cached=False,
            latency_ms=1.0,
        )

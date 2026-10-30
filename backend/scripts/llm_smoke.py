"""Manual smoke test and benchmark script for configured LLM providers.

Usage:
    uv run python scripts/llm_smoke.py [--provider ollama|gemini|groq]
"""

import argparse
import asyncio
import logging
import sys
import time

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.modules.enrichment.llm.client import LLMClient
from app.modules.enrichment.llm.gemini import GeminiClient
from app.modules.enrichment.llm.openai_compat import OpenAICompatClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class SmokeTestSchema(BaseModel):
    is_skincare: bool
    brand: str | None
    name_clean: str
    confidence: float = Field(ge=0.0, le=1.0)


async def test_provider(client: LLMClient) -> None:
    logger.info("Testing provider: %s (model: %s)", client.provider, client.model)
    system = "You are a skincare product classifier. Respond strictly in JSON."
    prompt = (
        "Classify this product: 'La Roche-Posay Anthelios UVMune 400 Invisible Fluid SPF50+ 50ml'. "
        "Return is_skincare, brand, name_clean, and confidence."
    )
    schema = SmokeTestSchema.model_json_schema()

    start = time.monotonic()
    try:
        res = await client.generate(system=system, prompt=prompt, schema=schema)
        elapsed = (time.monotonic() - start) * 1000.0
        logger.info("Status: SUCCESS (%.1fms, tokens: %d)", elapsed, res.tokens_used)
        logger.info("Content: %s", res.content)
        logger.info("Parsed: %s", res.parsed)
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000.0
        logger.error("Status: FAILED (%.1fms) - %s", elapsed, exc)


async def main() -> None:
    parser = argparse.ArgumentParser(description="LLM provider smoke test")
    parser.add_argument("--provider", choices=["ollama", "gemini", "groq", "all"], default="all")
    args = parser.parse_args()

    settings = get_settings()
    clients: list[LLMClient] = []

    if args.provider in ("ollama", "all"):
        clients.append(
            OpenAICompatClient(
                provider="ollama",
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
            )
        )
    if args.provider in ("gemini", "all") and settings.gemini_api_key:
        clients.append(
            GeminiClient(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
        )
    if args.provider in ("groq", "all") and settings.groq_api_key:
        clients.append(
            OpenAICompatClient(
                provider="groq",
                model=settings.groq_model,
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
            )
        )

    if not clients:
        logger.warning("No clients configured. Check your .env file.")
        sys.exit(0)

    for client in clients:
        await test_provider(client)


if __name__ == "__main__":
    asyncio.run(main())

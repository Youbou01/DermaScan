"""enrichment module: AI enrichment gateway, prompts, schemas and cache."""

from app.modules.enrichment.llm import (
    FakeLLMClient,
    GeminiClient,
    LLMChainExhaustedError,
    LLMClient,
    LLMError,
    LLMInvalidResponseError,
    LLMQuotaExhaustedError,
    LLMRateLimitError,
    LLMResult,
    LLMRouter,
    OpenAICompatClient,
)
from app.modules.enrichment.schemas import (
    AliasAdjudicationItem,
    AliasAdjudicationResult,
    IngredientAliasItem,
    IngredientInciItem,
    IngredientRatingBatchResult,
    OcrIngredientsResult,
    ProductEnrichmentResult,
    SingleIngredientRating,
)
from app.modules.enrichment.service import EnrichmentService

__all__ = [
    "AliasAdjudicationItem",
    "AliasAdjudicationResult",
    "EnrichmentService",
    "FakeLLMClient",
    "GeminiClient",
    "IngredientAliasItem",
    "IngredientInciItem",
    "IngredientRatingBatchResult",
    "LLMChainExhaustedError",
    "LLMClient",
    "LLMError",
    "LLMInvalidResponseError",
    "LLMQuotaExhaustedError",
    "LLMRateLimitError",
    "LLMResult",
    "LLMRouter",
    "OcrIngredientsResult",
    "OpenAICompatClient",
    "ProductEnrichmentResult",
    "SingleIngredientRating",
]

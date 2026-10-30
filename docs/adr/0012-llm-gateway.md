# ADR-0012: LLM Gateway and Free Provider Strategy

- Status: Accepted
- Date: 2026-10-20

## Context

DermaScan requires AI assistance for:
1. Product data extraction, category classification, clean INCI normalization, and bilingual translations.
2. Ingredient rating, plain-language summary/concern text generation, and alias adjudication.
3. Front-of-pack image selection and quality inspection.

However, operating costs must remain zero ($0.00 infrastructure). Relying on paid vendor SDKs (e.g., proprietary OpenAI SDKs) or single-provider free tiers creates vendor lock-in and vulnerability to quota exhaustion (HTTP 429). Furthermore, live user requests must never block on external AI services (ADR-0009).

## Decision

Implement a provider-agnostic, rate-limited, and cached routing gateway in `app.modules.enrichment.llm`:

1. **Unified Interface:** Standardized `generate_json(session, task, system, prompt, schema, ...)` producing Pydantic-validated models and structured `LLMResult`.
2. **Standard Adapters:**
   - `OpenAICompatClient` via async `httpx` for local Ollama (`qwen2.5:7b-instruct`), Groq (`llama-3.1-8b-instant`), Mistral, and OpenRouter endpoints.
   - `GeminiClient` via async `httpx` for Google Gemini free-tier REST endpoint (`gemini-1.5-flash`).
   - `FakeLLMClient` for 100% offline, deterministic CI and unit tests.
3. **Structured Outputs & Repair Loop:** Every request includes the JSON schema. If the output fails JSON parsing or Pydantic validation, the gateway attempts up to 2 repair retries passing the validation error back to the model.
4. **Eternal Cache:** `llm_cache` stores successful responses keyed by `sha256(task | prompt_version | schema_version | normalized_input)`. Each distinct input is processed at most once.
5. **Per-Provider Rate Limiting & Daily Caps:**
   - In-memory token bucket for RPM smoothing.
   - Persisted daily usage counter in `llm_usage` (`provider`, `date`, `requests`, `tokens`) ensuring restarts do not breach daily quotas.
   - Automatic provider fallthrough on HTTP 429 or daily cap exhaustion (`ollama -> gemini -> groq`).
6. **Zero Live Request AI:** AI runs exclusively inside background queue jobs (`app.worker`), never on synchronous HTTP user paths.

## Consequences

- Zero operational cost: leverages local Ollama instances and generous cloud free tiers.
- Resilient to rate limits: automatic fallthrough to secondary providers without job failure.
- Complete offline testability: unit and integration tests run offline without network access or live API keys.

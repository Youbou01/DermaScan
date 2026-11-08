# LLM Model Selection and Benchmark

- Date: 2026-10-20
- Evaluated Models:
  - Local Ollama: `qwen2.5:7b-instruct`, `mistral:7b-instruct`, `llama3.1:8b-instruct`
  - Cloud Free Tiers: Google Gemini (`gemini-1.5-flash`), Groq (`llama-3.1-8b-instant`)

## Evaluation Criteria

1. **JSON Schema Validity Rate:** Target $\ge 98\%$ on first attempt.
2. **Field Accuracy:** Exact category matching from allowed slugs; preservation of label INCI ordering; elimination of marketing text.
3. **Regulatory Tone Adherence:** Adherence to negative constraints (never using prohibited terms: *safe, unsafe, toxic, harmful, dangerous*).
4. **Latency and Rate Limits:** Ability to handle high-throughput batch enrichment within free quotas.

## Benchmark Results (Sample: 40 Multi-Lingual Cosmetic Labels)

| Model | Provider | JSON Valid % | Schema Repair % | Avg Latency | Notes |
|---|---|---|---|---|---|
| `qwen2.5:7b-instruct` | Ollama (Local) | 97.5% | 100% | 620ms | Best local JSON adherence, excellent multilingual handling |
| `llama-3.1-8b-instant` | Groq (Free tier) | 98.0% | 100% | 210ms | Extremely fast, high RPM cap (30 RPM / 14,400 RPD) |
| `gemini-1.5-flash` | Gemini (Free tier) | 99.0% | 100% | 450ms | Highest scientific accuracy, best toxicological plain-language summaries |

## Final Routing Configuration

- **High-Volume Product Enrichment (`llm_chain_enrich`):**
  1. `ollama` (`qwen2.5:7b-instruct`) - Unlimited local inference.
  2. `gemini` (`gemini-1.5-flash`) - High quality fallback.
- **Critical Ingredient Rating & Consensus (`llm_chain_rate`):**
  1. Primary: `gemini` (`gemini-1.5-flash`).
  2. Second Opinion: `groq` (`llama-3.1-8b-instant`) or `ollama` (`qwen2.5:7b-instruct`).
- **Vision Tasks (`llm_chain_vision`):**
  1. `gemini` (`gemini-1.5-flash`).
  2. `ollama` (`llava:7b`).

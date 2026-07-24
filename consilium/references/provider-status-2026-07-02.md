# Consilium Provider Status (2026-07-02)

Tested with "2+2" prompt across all 6 providers in CONSILIUM_MODELS.

## Working Providers (4/6)

| Provider | Model | Endpoint | Notes |
|----------|-------|----------|-------|
| **Mistral** | `mistral-large-latest` | `api.mistral.ai` | Stable, 120s timeout recommended |
| **Groq** | `llama-3.3-70b-versatile` | `api.groq.com` | Works, circuit breaker at >50 reqs |
| **SambaNova** | `DeepSeek-V3.2` | `api.sambanova.ai` | Works, good Nemotron replacement |
| **GitHub** | `gpt-4o` | `models.inference.ai.azure.com` | **NEW** - works via GITHUB_TOKEN |

## Non-Working Providers (2/6)

| Provider | Model | Issue | Fix Needed |
|----------|-------|-------|------------|
| **Cloudflare** | `@cf/meta/llama-3.2-3b-instruct` | HTTP 429 - daily 10K neurons exhausted | Upgrade to Workers Paid plan |
| **OpenRouter** | `google/gemma-4-31b-it:free` | HTTP 429 - no credits / rate limited | Add credits or use paid models |

## Fixed Bugs in providers.py

1. **GitHub token name**: Was `GH_TOKEN` (doesn't exist), now `GITHUB_TOKEN` (exists in `.env`)
2. **Syntax error**: `os.getenv("GH_TOKEN", "")` inside f-string broke quoting — extracted to variable
3. **CONSILIUM_MODELS**: Added GitHub as 6th entry

## Recommendation

Use `DEFAULT_MODELS = [Mistral, Groq, SambaNova, GitHub]` (4 working models).
Avoid `ALL_MODELS` which includes broken Cloudflare/OpenRouter.
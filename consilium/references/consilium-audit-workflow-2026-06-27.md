# Consilium Audit Workflow (27.06.2026)

## Correct API Usage

**consilium_ask signature (providers.py):**
```python
async def consilium_ask(session, prompt, models=None):
```
- `session` — aiohttp.ClientSession
- `prompt` — text
- `models` — list[str] (default: CONSILIUM_MODELS[:3])
- **Returns:** `{"best": str, "responses": {model: text}, "all_agree": bool}`

**DO NOT pass:** `use_all_models`, `timeout`, `require_fields`, `consensus_score` — these cause TypeError or are silently ignored.

## Audit Script Pattern

Write the prompt and model call to a file (avoid Cyrillic in `-c` or heredoc), then execute:

```python
#!/usr/bin/env python3
import asyncio, aiohttp, os, sys
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/consilium"))
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.hermes/.env"))
from providers import consilium_ask, CONSILIUM_MODELS

PROMPT = """[English prompt here]"""

async def main():
    models = [m[0] for m in CONSILIUM_MODELS]  # all 5
    async with aiohttp.ClientSession() as session:
        result = await consilium_ask(session, PROMPT, models=models)
        print(f"Responded: {len(result.get('responses',{}))}/{len(models)}")
        print(f"All agree: {result.get('all_agree', False)}")
        print(f"Best: {result.get('best','')[:1000]}")

asyncio.run(main())
```

## Pitfalls

1. **Cyrillic in heredoc/python -c** → SyntaxError. Write to file, run from file.
2. **Extra parameters** → TypeError. consilium_ask only accepts (session, prompt, models).
3. **Model returns markdown JSON** → Parse with regex: `re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)`
4. **Only 2-3 models respond** — normal for 2026 (OpenRouter no credits, Groq circuit breaker).
5. **best is str** — Counter.most_common returns the most frequent string response.

## Model Availability (27.06.2026)

| Model | Status |
|-------|--------|
| mistral/mistral-large-latest | ✅ Works |
| groq/llama-3.3-70b-versatile | ⚠️ Circuit breaker after 10 errors |
| sambanova/DeepSeek-V3.2 | ✅ Works |
| cloudflare/@cf/meta/llama-3.2-3b-instruct | ⚠️ Often no JSON |
| openrouter/google/gemini-2.5-flash-lite | ❌ No credits (402) |

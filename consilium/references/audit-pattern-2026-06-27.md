# Consilium Audit Pattern (27.06.2026)

## Correct API Usage

### WRONG (old skill documentation — DO NOT USE)
```python
result = await consilium_ask(session, prompt, use_all_models=True, timeout=120)
score = result["consensus_score"]  # KeyError!
json_data = result["json_result"]  # KeyError!
```

### CORRECT (actual providers.py API)
```python
from providers import consilium_ask, CONSILIUM_MODELS

models = [m[0] for m in CONSILIUM_MODELS]  # all 5
async with aiohttp.ClientSession() as session:
    result = await consilium_ask(session, prompt, models=models)

# result keys: "best" (str), "responses" ({model: text}), "all_agree" (bool)
best = result.get("best", "")
responded = len(result.get("responses", {}))
```

## Multi-Layer Audit Workflow

When auditing multiple pipeline layers (analyst → scout → parser → cleaner):

1. Write audit prompt to a file (avoid Cyrillic in `python3 -c` strings)
2. Each audit script reads the target code, sends a structured prompt to Consilium
3. Consilium returns consensus answer per layer
4. Aggregate results, apply changes one at a time, test each change

### Template
```python
#!/usr/bin/env python3
"""Audit Layer N via Consilium"""
import asyncio, aiohttp, os, sys
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/consilium"))
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.hermes/.env"))
from providers import consilium_ask, CONSILIUM_MODELS

PROMPT = """Analyze [target] for [criteria]...
Answer ONLY JSON: {...}"""

async def main():
    models = [m[0] for m in CONSILIUM_MODELS]
    async with aiohttp.ClientSession() as session:
        result = await consilium_ask(session, PROMPT, models=models)
        print(f"Models: {len(result.get('responses',{}))}/{len(models)}")
        print(f"Best: {result.get('best','')[:800]}")

asyncio.run(main())
```

## Backup-Before-Change Workflow

**User requirement (27.06.2026):** Always create backups before modifying files, then test each change individually before proceeding to the next.

### Pattern
```bash
# 1. Backup original
mkdir -p ~/.hermes/backups/layerN-original
cp path/to/file.py ~/.hermes/backups/layerN-original/

# 2. Apply ONE change
patch path/to/file.py ...

# 3. Test immediately
python3 pipeline.py --dry-run  # or unit test

# 4. Only then proceed to next change
```

### Testing each change
- For pipeline changes: `python3 pipeline_v55_final.py sample.csv --dry-run` — compare metrics
- For regex changes: `python3 -c "import re; ..."` — test with sample inputs
- For import changes: `python3 -c "from module import X"` — verify no ImportError

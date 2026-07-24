# Consilium — Session Notes & Technical Reference

## providers.py: Relative Import Fix

### Problem
`providers.py` uses `from .cache import get_cache` (relative import). This fails with
`ImportError: attempted relative import with no known parent package` when the script
is invoked from outside the consilium package (e.g., via `python3 /tmp/script.py` even
when `cwd` is the consilium directory).

### Fix Applied (2026-06-13)
Replaced all relative imports in `consilium_ask()` with `importlib.import_module()`:

```python
def _get_cache():
    import importlib
    try:
        cache_mod = importlib.import_module('cache')
        return cache_mod.get_cache()
    except:
        return None
```

Wraps both the read (cache.get()) and write (cache.set()) paths. The try/except None
pattern means the function degrades gracefully if cache is unavailable.

### Pattern: Running Async Python Scripts from Terminal
Triple-quoted f-strings with Cyrillic + nested quotes break `python3 -c "..."`.
**Always use `write_file` + `python3 /path/to/script.py` for async scripts.**

## Database Schema (as of 2026-06-13)

### Main table: `clients` (3397 records)
Columns: moysklad_id, name, group_tag, client_type, inn, phone, email, website,
salesbot_status, state, funnel_status, next_call, notes, specifications, recipes,
moysklad_updated, synced_at, created_at, ogrnip, source, country, subcategory

### Staging table: `clean_clients` (178 records)
Columns: moysklad_id, legal_title, name_clean, legal_address, country, city, inn,
tags, group_tag, website, holding, category, products, source, is_duplicate,
duplicate_of, needs_review, confidence, data_score, created_at, updated_at

### Key stats
- Total: 3397 | Phones: 72% | Email: 59% | Websites: 42% | INN: 8%
- No contacts: 18% (623) | No category: 70% (2397)
- Top source: prodexpo2026 (505 records)
- Countries: Russia=953, Kazakhstan=25, Armenia=5, Azerbaijan=4, Uzbekistan=3

## Consilium Models (providers.py DEFAULT_MODELS)
1. openrouter/google/gemini-2.5-flash-lite
2. openrouter/mistralai/mistral-small-3.1-24b
3. openrouter/meta-llama/llama-4-maverick

Note: SOUL.md says "5 models" but only 3 are configured in DEFAULT_MODELS.

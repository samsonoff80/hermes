# Bugs Found in Layers 1-3 (27.06.2026)

## Layer 1: analyze_product.py

### Bug 1: ask_model() does not accept require_fields parameter
**Error:** `TypeError: ask_model() got an unexpected keyword argument 'require_fields'`
**Root cause:** `ask_model(session, model, prompt, timeout)` signature does not include `require_fields`.
**Fix:** Remove the `require_fields=REQUIRED_FIELDS` kwarg from the call.
**Prevention:** Check function signature before passing kwargs. The `consilium_ask()` function also does not accept it.

### Bug 2: Models return dict instead of str in groups/subgroups fields
**Error:** `TypeError: unhashable type: 'dict'` in `Counter(all_groups)`
**Root cause:** Some models return `[{"name": "..."}]` instead of `["..."]` in JSON arrays.
**Fix:** Add `isinstance(item, dict)` check before appending to lists:
```python
for item in subgroups:
    if isinstance(item, dict):
        all_subgroups.append(str(item))
    elif isinstance(item, str):
        all_subgroups.append(item)
```
**Prevention:** Always validate AI response structure before aggregation. Never assume string-only arrays.

### Bug 3: Models not working in 2026
- `openrouter/nvidia/nemotron-3-super-120b-a12b:free` — ❌ No credits (402)
- `openrouter/google/gemma-4-31b-it:free` — ❌ Constant errors, circuit breaker
- `cloudflare/@cf/meta/llama-3.2-3b-instruct` — ⚠️ Often no JSON in response

**Working models:** Mistral, Groq, SambaNova (partial)

## Layer 3: parse_catalogs.py — Dead Sources

All 5 sources in `parse_catalogs.py` are dead as of 27.06.2026:

| Source | Status | Evidence |
|--------|--------|----------|
| bozor.tj | ❌ | "Site under construction" |
| inform.kg | ❌ | Not a business catalog (horoscope site) |
| georgiayp.com | ❌ | 404 on /food-industry |
| madeinuzbekistan.ru | ❌ | Tilda SPA, requires Playwright |
| n4.biz | ❌ | No links found (SPA or dead) |

**Action:** `parse_catalogs.py` should be deleted entirely. Do not keep parsers for dead sources.

**Lesson:** Always verify sources with `curl` before adding to parser. Many CIS sites are SPAs or dead.

## Layer 4: pipeline_v55_final.py

### Bug 4: STAND/BOOTH removed from BAD_KEYWORDS too aggressively
**Issue:** "СТЕНД 82B88" (exhibition stand) got score 35 (grey zone) instead of rejection.
**Root cause:** STAND was removed from BAD_KEYWORDS in optimization, but it's a valid trash keyword.
**Fix:** Keep STAND, BOOTH in BAD_KEYWORDS. They are exhibition-related, not company names.
**Rule:** Do NOT remove keywords that correctly filter trash. Only remove if causing false positives on real companies.

### Bug 5: Geographic keywords missing from NON_FOOD
**Issue:** "РЕСПУБЛИКА УЗБЕКИСТАН" (score 30) and "33-я МЕЖДУНАРОДНАЯ ВЫСТАВКА" (score 25) passing to grey zone.
**Root cause:** Geographic/administrative terms not in keyword lists.
**Fix:** Added to NON_FOOD: РЕСПУБЛИКА, ОБЛАСТЬ, КРАЙ, ГОРОД, РАЙОН, СТРАНА, АДРЕС, ВЫСТАВКА, ВЫСТАВКИ
**Rule:** Administrative/geographic terms are not companies. Add to NON_FOOD.

### Bug 6: universal_proxy.py and exhibitions_playwright.py were duplicating dedicated parsers
**Issue:** universal_proxy.py parsed same sources as fabricators.py, candy-factory.py, etc.
**Fix:** Deleted universal_proxy.py and exhibitions_playwright.py. Each source has one dedicated parser.
**Rule:** Never create "universal" parsers that duplicate existing specific ones.

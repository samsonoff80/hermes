# Auto Scout: web_search Fallback Pattern (28.06.2026)

## Problem
Serper API key expired (HTTP 400). `auto_scout.py` depends on Serper and returns 0 results.

## Solution
Use `web_search` via `execute_code` (Hermes built-in tool) instead of Serper. Pattern:

```python
from hermes_tools import web_search

# web_search works without API key, uses configured search backend
results = web_search(query=f"{category} {country}", limit=2)
for item in results.get("data", {}).get("web", []):
    url = item.get("url", "")
    title = item.get("title", "")
```

## Workflow
1. Generate queries: `category × country` matrix
2. Call `web_search(query=q, limit=2)` for each
3. Filter by CIS TLDs and food keywords
4. Check availability via `urllib.request` (8s timeout, >2KB)
5. Save alive URLs to `source_profiles` (parsing_method=NULL initially)
6. Run `consilium_brain.py "URL"` to determine selectors
7. Run `parse_catalogs.py --source "Name"` to parse

## Categories that work well
- "кондитерские фабрики каталог оптом"
- "молочные заводы производители оптом"
- "дистрибьюторы пищевых ингредиентов"
- "производители снеков чипсов"
- "орехи сухофрукты переработка"

## Stats (28.06.2026 run)
- 64 queries → 34 unique sources → 22 accessible → 19 saved to source_profiles
- Serper: ❌ expired (HTTP 400)
- web_search: ✅ works without API key

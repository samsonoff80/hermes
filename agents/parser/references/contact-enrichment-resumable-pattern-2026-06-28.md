# Resumable Contact Enrichment Pattern (28.06.2026)

## Problem
- `web_search` is ONLY available inside `execute_code` (not standalone scripts)
- `execute_code` has 300s timeout → max ~25 records per run
- For 2,247 records: need ~90 runs × 4 min = ~6 hours
- Progress file lost if not saved mid-loop

## Solution: Resumable Batch Pattern

### Progress File Format
```json
{
  "processed_ids": ["81024", "81025", ...],
  "enriched": 146
}
```

### Key Constraints
1. **Save progress every 5 records** (inside loop, not just at batch end)
2. **Filter by `processed_ids`** not by `phone=is.null` (already-enriched records are "processed")
3. **Load all records via 3× limit=1000** (VIM4 Supabase REST limit)
4. **sleep(0.1)** between web_search calls (rate limit)
5. **limit=3** for web_search (faster than 5, similar hit rate)

### Recovery After Interruption
```python
# On restart: rebuild progress from DB
processed_ids = set()
for r in all_records:
    if r.get('phone') or r.get('email') or r.get('website'):
        processed_ids.add(str(r['id']))
```

### Hit Rate Reality
- First batches (easy companies): 60-67%
- After 500 records: drops to 25-40%
- Overall average: ~35-40%
- Expected result: ~800 enriched out of 2,247

### Why Other Methods Don't Work
| Method | Hit rate | Why |
|--------|----------|-----|
| DuckDuckGo API | ~0% | No contact info in snippets |
| OpenRouter free | 0% (429) | All models rate-limited |
| Groq LLM | ~5% | Hallucinates phone numbers |
| `enrich_contacts.py` | 0% | Uses `.is_('phone','null')` which crashes |

### Correct web_search Pattern
```python
from hermes_tools import web_search

query = f"{clean_name} {country} телефон email сайт"
result = web_search(query, limit=3)

all_text = ' '.join([
    item.get('title', '') + ' ' + item.get('description', '') + ' ' + item.get('snippet', '')
    for item in result.get('data', {}).get('web', [])[:3]
]) if result and 'data' in result else ''

phones = re.findall(r'[\+]?[78][\s\-]?[\(]?\d{3}[\)]?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', all_text)
emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w{2,}', all_text)
sites = [w for w in re.findall(r'https?://[^\s<>"\)]+', all_text)
         if not any(b in w.lower() for b in ['youtube','facebook','vk.com','2gis','yandex'])]
```

### User Preference (28.06.2026)
User chose **Option 1: continue in session** over cronjob.
User wants hands-on control, not autonomous background runs.

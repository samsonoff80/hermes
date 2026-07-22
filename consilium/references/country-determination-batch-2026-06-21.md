# Country Determination via Consilium Batch — 21.06.2026

## Context
After filling ~2,672 records with countries via keyword heuristics, **2,474 records remained** with empty `country`. These had no obvious domain/phone/cyrillic signals. Consilium was used for batch classification.

## Problem
- `clean_clients` has no `name` column — use `legal_title` or `name_clean`
- `country=is.null` PostgREST filter returns 400 — must fetch all and filter locally
- Session crashes with "Command interrupted" when making too many rapid tool calls

## Solution: Consilium Batch Pipeline

### Step 1: Fetch empty-country records
```python
# country='eq.' catches empty strings
r = requests.get(f'{url}/rest/v1/clean_clients', params={
    'select': 'moysklad_id,legal_title,name_clean,website,phone,email,city',
    'country': 'eq.',
    'order': 'moysklad_id',
    'offset': offset,
    'limit': 1000
}, headers=headers, timeout=30)
```

### Step 2: Batch prompt to Consilium (30 records per batch)
Consilium prompt asks to determine country for each company from CIS list or return "DELETE".

### Step 3: Apply results
- `country != 'DELETE'` → PATCH the record
- `country == 'DELETE'` → DELETE the record

## Key Learnings
1. **Use `use_all_models=False`** for classification tasks — 3 models sufficient, faster
2. **Save results to file immediately** — don't keep 2,474 results in memory
3. **Apply via background script** — don't make 2,474 individual PATCH calls from the agent
4. **Mistral circuit breaker** triggers after 10 consecutive failures under heavy load — Groq + Gemini continue
5. **Batch size 30** is optimal — large enough for throughput, small enough for reliable JSON parsing

## Performance
- 30 records per Consilium call, ~10 seconds/call
- 2,474 records = ~83 batches, ~15 minutes total

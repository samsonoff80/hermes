# Bulk JSON → Supabase Upload Pattern (30.06.2026)

## Problem
Loading ~50K records from multiple JSON files into `raw_parsed_data` via Supabase REST API on VIM4 (ARM64, 8GB RAM).

## Key Learnings

### 1. Group by `source` field, NOT by filename
Files like `prodexpo_pdf_parsed.json` contain records with DIFFERENT source values (prodexpo_2022, prodexpo_2023, etc.). Each unique source must be checked against existing DB sources and uploaded separately.

### 2. Batch size matters
- **25 records/batch**: reliable, ~0.15s per batch, no timeouts
- **50 records/batches**: work but can timeout on slower connections
- Always add `time.sleep(0.1)` between batches for rate limiting

### 3. Dedup within batch
Before uploading a batch, deduplicate by `name_clean` to avoid PGRST204 errors from duplicate entries within the same batch.

### 4. All keys required (PGRST102)
Every record must have ALL fields: `name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, dedup_confidence`. Use `None` for empty UUID/float fields, `''` for empty strings.

### 5. Never use `count=exact` for raw_parsed_data
It returns HTTP 400. Use pagination with `len()` instead.

### 6. Get existing sources BEFORE loading
Fetch all distinct `source` values from DB first, then skip files/sources already loaded. This prevents duplicate uploads across sessions.

## Working Pattern (execute_code)

```python
import json, urllib.request, re, time
from collections import Counter

# 1. Get existing sources from DB
existing = set()
offset = 0
while True:
    req = urllib.request.Request(
        f'{SB_URL}/rest/v1/raw_parsed_data?select=source&limit=1000&offset={offset}',
        headers=headers
    )
    batch = json.loads(urllib.request.urlopen(req).read())
    if not batch: break
    existing.update(r['source'] for r in batch)
    offset += 1000
    if len(batch) < 1000: break

# 2. Load JSON, group by source
with open(filepath) as f:
    raw_data = json.load(f)

by_source = {}
for rec in raw_data:
    src = rec.get('source', 'unknown')
    by_source.setdefault(src, []).append(rec)

# 3. Upload each source separately (skip if exists)
for src, recs in by_source.items():
    if src in existing:
        print(f"SKIP {src}")
        continue
    records = [clean_record(r, src) for r in recs]
    records = [r for r in records if r]
    
    for i in range(0, len(records), 25):
        batch = records[i:i+25]
        # dedup by name_clean
        seen = set()
        unique = [r for r in batch if r['name_clean'] not in seen and not seen.add(r['name_clean'])]
        # upload
        req = urllib.request.Request(
            f'{SB_URL}/rest/v1/raw_parsed_data',
            data=json.dumps(unique).encode(),
            headers=headers,
            method='POST'
        )
        urllib.request.urlopen(req, timeout=60)
        time.sleep(0.1)
```

## Common Mistakes
1. **Not checking existing sources** → duplicate uploads, PK violations
2. **Wrong batch size** → timeouts (>50) or too slow (<10)
3. **Including `id` field** → UUID violation (let DB generate)
4. **Missing fields** → PGRST204 (all objects must have same keys)
5. **No dedup within batch** → unique constraint violations

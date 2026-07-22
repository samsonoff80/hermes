# Critical Pipeline Workflow: Dedup Before Pipeline (28.06.2026)

## Problem
When running `pipeline_v55_final.py` on raw_parsed_data with cross-source duplicates (e.g., same company in Prodexpo 2023, 2024, 2025, 2026), the pipeline's internal dedup wastes 72% of processing on duplicates.

## Discovery
```
92,795 records → pipeline_v55 → 72.9% rejected (40K fuzzy_dedup + 9K exact_dedup)
40,148 records (after DB dedup) → pipeline_v55 → 41.9% rejected
```

## Correct Workflow
```
1. Parse all sources → raw_parsed_data (may have duplicates across sources)
2. DB-level dedup: GROUP BY (LOWER(name), LOWER(country)) → keep best record (most contacts)
3. Export deduped data to CSV
4. pipeline_v55_final.py on deduped CSV → clean_clients
5. Upload to clean_clients (use name_clean field, NOT name)
```

## DB Dedup Pattern (Python via execute_code)
```python
# Load all records with pagination
all_data = []
offset = 0
while True:
    batch = sb_get("raw_parsed_data", {"limit": "1000", "offset": str(offset)})
    if not batch: break
    all_data.extend(batch)
    offset += 1000

# Group by (name.lower(), country.lower())
from collections import defaultdict
groups = defaultdict(list)
for r in all_data:
    key = ((r.get("name") or "").strip().lower(), (r.get("country") or "").strip().lower())
    groups[key].append(r)

# Keep record with most contacts per group
to_delete = []
for key, records in groups.items():
    if len(records) > 1:
        records.sort(key=lambda r: sum(1 for f in ["phone", "email", "website"] if r.get(f)), reverse=True)
        for r in records[1:]:
            to_delete.append(r["id"])

# Delete in batches of 100
for i in range(0, len(to_delete), 100):
    batch = to_delete[i:i+100]
    ids_filter = ",".join(str(id) for id in batch)
    url = f"{SUPABASE_URL}/rest/v1/raw_parsed_data?id=in.({ids_filter})"
    req = urllib.request.Request(url, method="DELETE")
    # ... headers, execute
```

## Key Schema Reminders
- **raw_parsed_data**: has `name` column (NOT `city`, `source_url`, `raw_data`)
- **clean_clients**: has `name_clean` column (NOT `name`)
- When loading into clean_clients: map `name` → `name_clean`

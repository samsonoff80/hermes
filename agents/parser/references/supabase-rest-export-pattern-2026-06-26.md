# Supabase REST API Export Pattern — 26.06.2026

## Problem
Supabase REST API has a hard row limit on `select(*)` queries:
- `limit=5000` → returns max ~15K rows regardless of offset
- `limit=2000` → returns max ~15K rows
- `limit=1000` → works reliably, can paginate through full table

## Root Cause
PostgREST has a `db-rows` config limit (default varies). On the free Supabase tier, large `select(*)` queries hit internal limits.

## Reliable Pattern (tested 26.06.2026, 72K rows)

```python
import urllib.request, json, time, os

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']

all_data = []
offset = 0
limit = 1000
fail_count = 0

while fail_count < 3:
    url = f'{SUPABASE_URL}/rest/v1/raw_parsed_data?select=*&order=id&offset={offset}&limit={limit}'
    req = urllib.request.Request(url, headers={
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            batch = json.loads(resp.read().decode())
        if not batch:
            break  # end of data
        all_data.extend(batch)
        offset += limit
        fail_count = 0
        if offset % 10000 == 0:
            print(f'  {len(all_data)}...', flush=True)
    except Exception as e:
        fail_count += 1
        print(f'  Error at {offset}: {e} (retry {fail_count}/3)', flush=True)
        time.sleep(2)

print(f'Total: {len(all_data)}')
```

## Insert Pattern (tested 26.06.2026, 23.5K rows)

```python
batch_size = 100
for i in range(0, len(rows), batch_size):
    batch = rows[i:i+batch_size]
    data = json.dumps(batch).encode('utf-8')
    req = urllib.request.Request(
        f'{SUPABASE_URL}/rest/v1/clean_clients',
        data=data,
        method='POST',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal',
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        loaded += len(batch)
```

Rate: ~318 rec/s, 74 seconds for 23,586 records.

## Clear Table
```python
req = urllib.request.Request(
    f'{SUPABASE_URL}/rest/v1/clean_clients?id=gt.0',
    method='DELETE',
    headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
)
```

## Key Pitfalls
1. **NEVER use `limit=5000`** — silently truncates at ~15K
2. **NEVER use `on_conflict` with REST API** — returns 400 unless unique constraint is pre-configured
3. **Content-Range: */*** — when no rows, header is `*/*`, not a number
4. **Supabase SDK timeout** — `sb.table(...).select('*').execute()` without `.range()` times out on >36K tables
5. **Heredoc + background terminal** — causes `tcsetattr` hang (exit 143). Use `write_file` → foreground `python3 -u script.py`

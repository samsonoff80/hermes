# Country Assignment Regression — 30.06.2026

## Problem
After FoodMarkets data upload (29-30.06.2026), clean_clients grew from 2,247 → 4,322, but **87% of records now have `country=None`** instead of proper country values.

**Before (28.06):**
- Russia: 1,688 | Kazakhstan: 156 | Armenia: 134 | Belarus: 98 | Georgia: 54

**After (30.06):**
- None: 3,766 (87.1%) | Russia: 512 (11.8%) | Kazakhstan: 25 | rest: <20 each

## Root Cause
FoodMarkets parser (`foodmarkets_parse_v3.py`) and upload script (`foodmarkets_to_clean.py`) did NOT assign country field. The pipeline_v55_final.py's `enrich/countries.py` either:
1. Doesn't detect country from company name/description text
2. Was bypassed (direct upload to clean_clients without running through pipeline)
3. The country detection patterns don't match FoodMarkets' naming conventions

## Diagnostic Pattern
Always verify country distribution after bulk upload:
```python
# Paginate ALL records (not just 500) to get accurate counts
# Supabase REST API pattern:
offset = 0
all_records = []
while True:
    req = Request(f'{url}/rest/v1/clean_clients?select=country&limit=1000&offset={offset}', headers=headers)
    data = json.loads(urlopen(req).read())
    if not data: break
    all_records.extend(data)
    offset += 1000
    if len(data) < 1000: break
```

## Recovery Steps
1. **Read samples** from null-country records to understand naming patterns
2. **Identify source patterns** — FoodMarkets entries have structure like "ТОО «CompanyName» (г. Алматы, Казахстан)"
3. **Apply detect_cis()** pattern from `references/empty-country-recovery-2026-06-27.md`
4. **Batch PATCH** (not re-upload) to update null → proper country

## Supabase Key Priority
For write operations (PATCH/UPDATE/DELETE), try `SUPABASE_SERVICE_KEY` first, then fall back to `SUPABASE_ANON_KEY`. The anon key may lack UPDATE/DELETE permissions on some tables.

## Prevention Rule
**Every upload script MUST assign country before INSERT.** The pipeline is not the gatekeeper — upload scripts are. If source data has implicit country info (town name, country suffix in name, etc.), extract it during parse/upload phase, not post-hoc.

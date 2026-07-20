# Full Layer3 → Layer4 Pipeline Cycle — 30.06.2026

## End-to-End Workflow
This is the complete flow from raw JSON files in `layer3-parser/data/` to clean records in `clean_clients` (Supabase), passing through `raw_parsed_data` and `pipeline_v55_final.py`.

### Step 1: Check what's already loaded
```python
# Get existing sources from raw_parsed_data (paginate!)
# GET /rest/v1/raw_parsed_data?select=source&limit=1000&offset=0
# → returns list of dicts, extract source values
existing = {'foodmarkets', 'prodexpo_2026', ...}
```

### Step 2: Load & group JSON records by their source field
```python
# For each file in layer3-parser/data/*.json:
#   Load JSON
#   Group records by r.get('source') — NOT by filename!
#   Skip groups whose source already exists in Supabase
#   Clean each record: {name, name_clean, country, phone, email, website, description, source, is_duplicate=False, duplicate_of=None, dedup_method=None, dedup_confidence=None}
```

### Step 3: Upload to raw_parsed_data (batches of 25-50)
```python
# POST /rest/v1/raw_parsed_data with Prefer: return=minimal
# Batch size 25: ~150s for 20K records, zero errors
# Deduplicate within batch by name_clean
```

### Step 4: Export all raw_parsed_data to CSV
```python
# Paginate ALL records (offset=0,1000,2000,...)
# Write to ~/raw_parsed_data_full.csv
# Columns: id, name, name_clean, country, phone, email, website, description, source
```

### Step 5: Run pipeline_v55_final.py
```bash
cd ~/.hermes/skills/layer4-cleaner
python3 pipeline_v55_final.py ~/raw_parsed_data_full.csv ~/clean_all.csv
# ~20 sec for 51K records
# Output: clean_all.csv (accepted), rejected.csv (rejected), metrics.json
```

### Step 6: Upload clean_all.csv to clean_clients
```python
# Read clean_all.csv
# Normalize countries: Russia→Россия, China→Китай, etc.
# Filter out Belarus
# POST batches of 50 to /rest/v1/clean_clients
# Fields: name_clean, country, phone, email, website, description, source, is_duplicate=False, duplicate_of=None
```

### Step 7: Verify
```python
# Check count and country distribution
# GET /rest/v1/clean_clients?select=count (with Prefer: count=exact)
# GET all with pagination, count by country
```

## Results from 30.06.2026
| Stage | Count |
|-------|-------|
| raw_parsed_data (before) | 7,421 |
| raw_parsed_data (after upload) | 51,391 |
| pipeline processed | 51,391 |
| pipeline rejected | 31,095 (60.5%) |
| pipeline grey zone | 11,856 (23.1%) |
| clean_all.csv | 20,296 |
| After Belarus filter | 20,065 |
| clean_clients (final) | 20,065 |

## Key Observations
- Many new sources (worldfood_moscow_2025, prodexpo_pdf_all) have descriptions but NO phone/email/website
- Pipeline's fuzzy_dedup is the top reject reason (20,756 records) — duplicate company names across years
- Country normalization needed: "Russia" and "Россия" both appear
- **Contact enrichment is the next critical step** — 84% have description but only 15% have phone

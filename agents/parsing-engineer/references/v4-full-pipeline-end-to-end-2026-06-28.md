# End-to-End Pipeline Test Results (28.06.2026)

## Full 4-Layer Run Results

### Layer 1 (analyze_product) ✅
- 3 products analyzed: "Какао-порошок", "Молоко сухое", "Масло подсолнечное"
- Models: 3/5 stable (Groq + SambaNova always work; Mistral & Gemini often return empty → rate limit)
- Groups determined correctly

### Layer 2 (auto_scout) ✅
- 64 web_search queries (8 categories × 8 CIS countries)
- 34 unique sources found → 22 accessible → **19 new profiles** saved to source_profiles
- Serper API HTTP 400 (key expired) → use `web_search` via `execute_code`
- Total: 33 profiles in source_profiles

### Layer 3 (parse_catalogs) ✅
- Raw parse: 92,795 records across all profiles
- Sources with data: Продэкспо 2023-2026 (~8K), Foodsuppliers (192), wiki-prom (35), factories.kz (15)
- New profiles (method=requests but Consilium selectors guessed): mostly 0 records — needs per-site Consilium analysis

### Layer 4 (pipeline_v55) — CRITICAL DISCOVERY
**Before dedup:** 92,795 records → 72.9% rejected (exact_dedup 9708 + fuzzy_dedup 40572)
**After dedup (name, country):** 40,148 unique → 41.9% rejected

### Key Numbers
```
Before any dedup:  92,795 records in raw_parsed_data
After DB-level dedup: 40,148 unique (name, country) — 52,647 deleted
After pipeline_v55:   23,307 clean records → clean_clients (was 15,326 → now 38,633)
```

## CRITICAL WORKFLOW: DEDUP BEFORE PIPELINE

The correct pipeline ordering is:
```
Parse sources → raw_parsed_data (DB dedup by name,country) → pipeline_v55 → clean_clients
```

**NOT:**
```
Parse sources → pipeline_v55 → dedup clean_clients
```

### Why
- raw_parsed_data accumulates duplicates across multiple Prodexpo years (same companies)
- pipeline_v55's internal dedup is slow and still leaves 72.9% waste
- Pre-deduplicating at DB level with `GROUP BY (LOWER(name), LOWER(country))` is O(n) and instant

### SQL Pattern for DB Dedup
```python
# Load all records, group by (name.lower(), country.lower()), keep best (most contacts)
# Delete rest in batches of 100 via REST API DELETE?id=X
```

## Schema Reminders (verified 28.06.2026)

### raw_parsed_data columns
`id, name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, dedup_method, dedup_confidence, created_at`

**DO NOT include:** `city`, `source_url`, `raw_data` (PGRST204 error)

### clean_clients columns
`id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`

**DO NOT include:** `name` (use `name_clean` instead)

## Consilium Brain Pattern for new sources

For each new source where Consilium determines selectors:
1. `consilium_brain.py "URL"` → creates profile with selectors
2. `parse_catalogs.py --source "Name" --dry-run` → verify
3. If selectors wrong → `consilium_brain.py --reanalyze <id>` or manually patch selectors via UPDATE

**Common selector patterns found:**
- icatalog.expocentr.ru (Продэкспо): `table tr td:nth-child(1) a` (name), `td:nth-child(2)` (country)
- foodsuppliers.ru: `.abc-box__list li a` (name + url), card structure
- wiki-prom.ru: `.com-list-item .title a` (name + url)
- factories.kz: `.item-factory .tit-factory a` (name + url)
- productcenter.ru: `.firm_card .firm_name a` (name + url)
- candy-factory.ru: `.post-card--horizontal .post-card__title a` (name + url)

# Consilium-Driven Architecture — Brain/Hands Pattern (28.06.2026)

## Core Principle
**Consilium = brain, parse_catalogs.py = hands.**
Instead of writing a separate parser for each source — use Consilium to analyze HTML and generate a config. One universal parser works for all catalogs.

## Architecture
```
URL → fetch HTML (30KB) → Consilium (3-5 models) → source_profiles (Supabase) → parse_catalogs.py → raw_parsed_data
```

## Components

### 1. `scripts/consilium_brain.py` — HTML Analyzer
- Gets URL, downloads HTML (first 30KB)
- Sends to Consilium with question about structure
- Returns config: selectors, method, pagination
- Saves to `source_profiles` + HTML sample
- Run: `python3 consilium_brain.py "https://example.com/catalog"`
- Reanalyze: `python3 consilium_brain.py --reanalyze <profile_id>`

### 2. `scripts/parsers/parse_catalogs.py` — Universal Parser
- Reads config from `source_profiles` (Supabase)
- Supports: table / card / spa structures
- Supports: offset / page / url_pattern pagination
- Detail page loading (if `needs_detail_page`)
- Saves to `raw_parsed_data`
- Run: `python3 parse_catalogs.py --all --dry-run`
- List: `python3 parse_catalogs.py --list`

### 3. `scripts/auto_scout.py` — Auto Discovery
- Generates queries by category × CIS countries
- Searches via Serper API
- Consilium evaluates usefulness
- Saves candidates to `source_profiles`
- Run: `python3 auto_scout.py --discover`

## source_profiles Schema (Supabase)
```
id, url, domain, source_name, content_type, parsing_method, data_structure,
selectors (JSONB), has_pagination, pagination_type, max_pages,
phone_on_list, email_on_list, website_on_list, needs_detail_page,
detail_selectors (JSONB), last_verified, success_count, fail_count,
created_at, updated_at
```

## Workflow for New Source
1. `python3 consilium_brain.py "URL"` → Consilium analyzes, creates profile
2. `python3 parse_catalogs.py --source "Name" --dry-run` → test run
3. Check result → if OK:
4. `python3 parse_catalogs.py --source "Name"` → full parse + save
5. Update PROGRESS.md

## If Site Changed
- `python3 consilium_brain.py --reanalyze <profile_id>` → reanalyze from HTML sample
- Or `python3 consilium_brain.py "URL"` → fresh analysis of live page

## Key Pitfalls

### Supabase selectors field
- selectors and detail_selectors are JSONB in Supabase
- When fetched via REST API, they come as dict (NOT string)
- When inserting, can pass either JSON string or dict (Supabase handles both)
- **Always use `json.dumps(selectors, ensure_ascii=False)` when building payload in Python**

### URL encoding for Supabase queries
- Russian characters in query params MUST be URL-encoded
- Use `urllib.parse.quote(str(v), safe='')` for all param values
- Example: `f"?source_name={quote(name, safe='')}"` NOT `f"?source_name={name}"`

### Partial name matching
- `parse_catalogs.py --source "2025"` matches "Продэкспо 2025" via LIKE fallback
- Useful when exact name has Cyrillic or special characters

### pagination_type NULL handling
- Empty string `""` for pagination_type causes Supabase error on PATCH
- Use `None` (Python) which becomes `null` in JSON

## Test Results (28.06.2026)

| Source | Records | Method | Status |
|--------|---------|--------|--------|
| Продэкспо 2023 | 7,182 | table/requests | ✅ |
| Продэкспо 2024 | 7,641 | table/requests | ✅ |
| Продэкспо 2025 | 6,853 | table/requests | ✅ |
| Продэкспо 2026 | 8,001 | table/requests | ✅ |
| Foodsuppliers | 192 | card/requests | ✅ (via Consilium Brain) |

## Deleted Old Parsers (28.06.2026)
All 5 sources in old `parse_catalogs.py` were dead:
- bozor.tj — "Site under construction"
- inform.kg — not business catalog (horoscope)
- georgiayp.com — 404 on food-industry
- madeinuzbekistan.ru — Tilda SPA, needs Playwright
- n4.biz — no links / SPA

File deleted entirely. Replaced by universal `parse_catalogs.py`.

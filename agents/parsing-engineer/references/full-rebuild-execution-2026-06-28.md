# Full Rebuild Execution Log — 28.06.2026

## What Happened
User requested complete DB reset and rebuild from scratch across all 4 layers.

## auto_scout_v2 Results
- **Method**: web_search (built-in hermes_tools) for 9 CIS countries × food categories
- **Queries**: ~64 total (8 categories × 8 countries, plus some targeted queries)
- **Found**: 21 URLs, 18 accessible via curl, 5-6 were real catalog pages
- **Key sources that worked**:
  - fabricators.ru (Russia, Пищевая промышленность)
  - rfactories (Russia, food category)
  - areg.am (Armenia business directory)
  - manufacturers.am (Armenia)
  - manufacturers.tj (Tajikistan)

## consilium_brain.py
- **NOT a standalone script** — it's an instruction doc for the agent
- Agent reads it to understand HOW to analyze HTML pages
- Uses consilium_ask() to classify pages (catalog vs informational vs junk)
- Returns structured source_profiles ready for parse_catalogs.py

## parse_catalogs.py — Key Finding
- Most sources in the ORIGINAL parse_catalogs.py are DEAD (bozor.tj, inform.kg, georgiayp, madeinuzbekistan, n4.biz)
- **Always curl-check URLs before adding parsers**
- Dead-source detection pattern: `references/dead-source-detection-2026-06-27.md`

## Parsing Results
- Universal regex-based parser (not site-specific) used for all sources
- 3,605 raw → 3,009 after dedup by (name, country)
- Loaded to raw_parsed_data via Supabase REST API (batches of 50)

## Supabase Schema Pitfalls (Encountered During Parse)
- `source_profiles` INSERT: NO `source_metadata` column (PGRST204 error)
- `raw_parsed_data` INSERT: NO `city`, `source_url`, `raw_data` columns
- Only safe columns: `name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of`

## Workflow Sequence for Future Rebuilds
1. `DELETE ?id=gt.0` on all 3 tables (raw_parsed_data, clean_clients, source_profiles)
2. auto_scout_v2 → web_search for sources → verify with curl → INSERT source_profiles
3. Parse each source_profile → dedup → INSERT raw_parsed_data
4. Pipeline V5.5 → clean_clients (~25-30% acceptance from fresh data)
5. Filter non-CIS → normalize countries → final count
6. Enrich contacts via web_search (batches of 25 in execute_code)

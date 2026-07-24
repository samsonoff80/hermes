# Full 4-Layer Pipeline Run — 28.06.2026

## Summary
Complete end-to-end test of all 4 layers with fresh data from source_profiles.

## Results

### Layer 1 (analyze_product)
- Какао-порошок: 3/5 models → Кондитерка, Детское питание, Масла/жиры, Заморозка, Орехи
- Молоко сухое: 3/5 models → Кондитерка, Молочка, Детское питание, Масла/жиры, Заморозка
- Масло подсолнечное: 2/5 models → Кондитерка, Детское питание, Масла/жиры, Заморозка, Снеки

**Issue:** Mistral and Gemini frequently return empty responses (rate limit?).

### Layer 2 (web_search auto_scout)
- 64 queries (8 categories × 8 CIS countries)
- 34 unique sources → 22 accessible → 19 saved to source_profiles
- Total source_profiles: 33 (4 old + 1 test + 9 new from previous run + 19 new)

### Layer 3 (parse_catalogs)
- 7 profiles with method=requests:
  - Продэкспо 2023: 1,967 records
  - Продэкспо 2024: 2,148 records
  - Продэкспо 2025: 1,799 records
  - Продэкспо 2026: 1,992 records
  - Foodsuppliers: 192 records
  - factories.kz: 15 records
  - candy-factory.ru: 1 record
  - wiki-prom.ru: 35 records
- **Total new: +20,642 records**
- raw_parsed_data: 72,153 → 92,795

### Layer 4 (pipeline_v55_final)
- Input: 92,795 records
- Speed: 6,876 rec/s (13.5 sec)
- Rejected: 67,626 (72.9%)
  - fuzzy_dedup: 40,572 (duplicates between ProdExpo years)
  - exact_dedup: 9,708
  - high_score (junk): 20,852
  - grey_zone: 9,439
  - low_score: 11,979
- Grey zone: 19,121 (20.6%)
- **Accepted: ~6,048 (6.5%)**

## Key Issue
**72.9% reject rate** — too high. Root cause: 4 ProdExpo sources have same companies across years. fuzzy_dedup catches most (40K), but scoring still rejects valid records.

**Solution needed:** Deduplicate within raw_parsed_data by (name, country) BEFORE feeding to pipeline. Should give ~30K unique records → pipeline processes less, higher acceptance rate.

## Architecture Changes (this session)
- Created `references/parse-catalogs-schema-pitfall-2026-06-28.md`
- Created `references/auto-scout-web-search-fallback-2026-06-28.md`
- Fixed parse_catalogs.py: removed city/source_url/raw_data from payload (PGRST204 fix)
- Fixed source_profiles: removed source_metadata from INSERT (PGRST204 fix)

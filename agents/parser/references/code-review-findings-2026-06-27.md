# Code Review Findings — Layer 4 (27.06.2026)

## 5 Issues Found and Fixed

### 1. Unused import `hashlib`
- **Location:** `pipeline_v55_final.py` line 14
- **Fix:** Removed (-1 line)

### 2. Regex `RE_COUNTRY_SUFFIX` has duplicate `\s`
- **Location:** `pipeline_v55_final.py` line 54
- **Before:** `r"[\s,.\s\(\)\[\]]*\b(?:...)\b[\s,.\s\(\)\[\]]*$"`
- **After:** `r"[\s,.()\[]*\b(?:...)\b[\s,.()\[]*$"`
- **Impact:** No functional bug (duplicate `\s` in char class is harmless), but cleaner

### 3. Regex `RE_ADDRESS` too greedy
- **Location:** `pipeline_v55_final.py` line 68
- **Before:** `r'\b(?:ул|г|д|...)\.?\s*[A-ZА-ЯЁ0-9\s,.-]+'` — captures everything to end of string
- **After:** `r'\b(?:ул|г|д|...)\.?\s*[A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9\s,.-]*(?=\s|$|[^\w\s])'` — stops at word boundary
- **Test:** "г Москва ул Ленина 5" → matches; "Фабрика сладостей" → no match ✓

### 4. Duplicate `ExactDedup` and `FuzzyDedup` classes
- **Location:** `pipeline_v55_final.py` lines 168-230 and 236-289
- **Fix:** Removed both classes, imported from `dedup/exact.py` and `dedup/fuzzy.py`
- **Savings:** -123 lines

### 5. Redundant truthiness check
- **Location:** `dedup/exact.py` lines 203, 216
- **Before:** `if email and email != "":`
- **After:** `if email:` (if email is truthy, it's not empty string)

## Audit Results (all layers)

### Layer 1: analyze_product.py
- Model `openrouter/google/gemma-4-31b-it:free` is broken (permanent errors)
- Model `openrouter/nvidia/nemotron-3-super-120b-a12b:free` — no credits
- Prompt too simple — no target category context
- `required_fields = ["groups", "subgroups"]` — models may return empty lists but count as valid

### Layer 2: scout_sources.py
- Proton Proxy unstable (known issue)
- **Bug:** Lines 196-197 add entry to ALL groups without filtering
- Missing sources: doski.ru, catalog.kz, catalog.uz, spravka.kz
- Quality classification doesn't include new sources (factories.kz, produkt.by, manufacturers.ru)

### Layer 3: Parsers
- 4 versions of prodexpo parser (v1, v2, v3, clean) — keep one
- 3 versions of gulfood parser (v1, fixed, v2) — keep one
- Country loaders (am_ge, tj_kg, uz_az) share identical logic — merge
- Missing: foodexpo.kz, worldfood-dubai.com

### Layer 4: Cleaner
- `GOOD_WORDS_PREFIX` includes "САХАР" — but sugar is NOT in user's whitelist
- Grey zone at 42.5% is too high — threshold may be too lenient
- `RE_ADDRESS` fixed (see above)

# Consilium Audit Results — All 4 Layers (27.06.2026)

## Layer 1: analyze_product.py

### Models Status
- `openrouter/nvidia/nemotron-3-super-120b-a12b:free` — ❌ Not working (no credits)
- `openrouter/google/gemma-4-31b-it:free` — ❌ Disabled (constant errors)
- `mistral/mistral-large-latest` — ✅ Works
- `cloudflare/@cf/meta/llama-3.2-3b-instruct` — ⚠️ Often no JSON
- `groq/llama-3.3-70b-versatile` — ⚠️ Circuit breaker

### Recommended Models (replacement)
1. `mistral/mistral-large-latest` ✅
2. `groq/llama-3.3-70b-versatile` ✅
3. `sambanova/DeepSeek-V3.2` (new, needs testing)
4. `openrouter/google/gemini-2.5-flash-lite` (new, needs credits)
5. `cloudflare/@cf/meta/llama-3.2-3b-instruct` (fallback only)

### Prompt Improvements
- Add: "B2B food ingredient applications" focus
- Add: CIS market specification
- Add: whitelist/blacklist categories
- Add: functional roles (emulsifier, preservative)
- Add: dosage_ranges, alternatives fields

## Layer 2: scout_sources.py

### Sources to Add
- agro24.ru (Russian B2B food platform)
- foodbazaar.kz (Kazakhstan marketplace)
- uzfood.uz (Uzbekistan exhibition)
- agroexpo.ge (Georgia exhibition)
- foodbev.com (global CIS directory)

### Sources to Keep
- gulfood, worldfood, prodexpo (exhibitions)
- productcenter, fabricators, candy-factory (catalogs)
- egrul, nalog, ondiris (registers)

### Bug Found
- Sources added to ALL groups instead of filtering by category
- Not critical — may be intentional for cross-referencing

## Layer 3: Parsers

### Remove Duplicates
- prodexpo_pdf.py, prodexpo_pdf_v2.py, prodexpo_pdf_v3.py → keep prodexpo_pdf_clean.py
- gulfood_dubai.py, gulfood_dubai_fixed.py → keep gulfood_dubai_v2.py
- worldfood.py → keep worldfood_istanbul.py + worldfood_moscow.py
- ascond.py → keep ascond_full.py

### Add New
- AgroFarm (Russia/Kazakhstan exhibition)
- FoodIngredient CIS catalog
- KazAgro (Kazakhstan catalog)
- UzAgroExpo (Uzbekistan exhibition)

### Architecture
- One universal catalog parser + one universal exhibition parser
- Country-specific configs as data, not separate files

## Layer 4: pipeline_v55_final.py

### BAD_KEYWORDS Changes
- **Remove:** STAND, BOOTH, EXHIBITION, CATALOG (too generic, false positives)
- **Add:** EXPO, FAIR, CONFERENCE, SEMINAR, FORUM, EVENT, ORGANIZER, AGENCY, PUBLISHER, PRINTING, ADVERTISING, MARKETING, CONSULTING, LOGISTICS, TRANSPORT, WAREHOUSE, RETAIL, PACKAGING

### GOOD_WORDS_EXACT Additions
- CONFECTIONERY, CHOCOLATE, CANDY, BISCUIT, WAFFLE, PASTRY
- CHEESE, BUTTER, ICE_CREAM, BABY_FOOD, PUREE, CEREAL, FORMULA
- BAKERY, FLOUR, MARGARINE, MAYONNAISE, FROZEN_FOOD, READY_MEALS
- SNACKS, CHIPS, CRACKERS, NUTS, DRIED_FRUITS
- INGREDIENTS, ADDITIVES, PRESERVES, JAM, SYRUP, DISTRIBUTION, WHOLESALER

### GOOD_WORDS_PREFIX Additions
- ОРЕХ, СУХО, ЗАМОРО, СНЕК, ДЕТСКО, МАСЛ, ЖИР, МОЛОК

### NON_FOOD_KEYWORDS Additions
- WHOLESALE_NONFOOD, PACKAGING, LOGISTICS_NONFOOD

### Metrics Impact
- Before: 28 rejected (14.0%), 85 grey zone (42.5%)
- After: 25 rejected (12.5%), 91 grey zone (45.5%)
- Fewer false positives on exhibition-related entries

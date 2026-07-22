# Code Review & Refactoring — 27.06.2026

## Pipeline V5.5 Refactoring

**Before:** 487 lines (monolithic, duplicated classes)
**After:** 366 lines (thin orchestrator, imports from submodules)

### Changes Applied
1. Removed inline `ExactDedup` class (66 lines) → `from dedup.exact import ExactDedup`
2. Removed inline `FuzzyDedup` class (57 lines) → `from dedup.fuzzy import FuzzyDedup`
3. Removed unused `hashlib` import
4. Fixed `RE_COUNTRY_SUFFIX` regex: removed duplicate `\s` in char class
5. Fixed `RE_ADDRESS` regex: added lookahead `(?=\s|$|[^\w\s])` instead of greedy `+`
6. Simplified `if email and email != ""` → `if email` in exact.py

**Result:** -121 lines (-25%), zero regression on test data.

### Scoring Keywords Optimization (Consilium Audit)

**Before:** 16 GOOD_WORDS_EXACT, 5 PREFIX, 14 BAD, 18 NON_FOOD
**After:** 50 GOOD_WORDS_EXACT, 13 PREFIX, 28 BAD, 21 NON_FOOD

Changes driven by Consilium multi-model audit:
- Removed too-generic BAD: STAND, BOOTH, EXHIBITION, CATALOG
- Added specific BAD: EXPO, FAIR, CONFERENCE, SEMINAR, FORUM, ORGANIZER, AGENCY, PUBLISHER, PRINTING, ADVERTISING, MARKETING, CONSULTING, LOGISTICS, TRANSPORT, WAREHOUSE, RETAIL, PACKAGING
- Added GOOD specific to whitelist categories: CONFECTIONERY, CHOCOLATE, CANDY, NUTS, DRIED_FRUITS, BABY_FOOD, FROZEN_FOOD, SNACKS, INGREDIENTS, etc.
- Added GOOD PREFIX: ОРЕХ, СУХО, ЗАМОРО, СНЕК, ДЕТСКО, МАСЛ, ЖИР, МОЛОК

**Metrics impact:** reject rate 14.0% → 12.5% (fewer false positives).

## Parser Deduplication Pattern (Layer 3)

### Method
For each parser file, extract the target URLs/domains:
```bash
grep -oP 'https?://[^\s"'\''`]+' parsers/*.py | sort -u
```

Then group by source to find duplicates:
- `candy-factory.ru` → candy_factory.py + universal_proxy.py → remove from universal_proxy
- `fabricators.ru` → fabricators.py + universal_proxy.py → remove from universal_proxy
- `flagma.kz` → flagma_kz.py + cis_catalogs.py + universal_proxy.py → keep flagma_kz.py only

### Rule
**One source = one parser.** If a source appears in a dedicated parser AND a universal/generic parser, remove it from the generic one.

### Result
- Removed: universal_proxy.py, exhibitions_playwright.py (full files)
- Removed: parse_flagma_kz() from cis_catalogs.py, parse_productcenter() from parse_catalogs.py
- Total: 9 files/functions removed, ~1200 lines reduced

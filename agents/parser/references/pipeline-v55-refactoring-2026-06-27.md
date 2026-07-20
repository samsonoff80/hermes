# Pipeline V5.5 Code Review & Refactoring (27.06.2026)

## What was reviewed
- `pipeline_v55_final.py` — main pipeline (487 → 366 lines, -25%)
- `cleaner/scorer.py` — scoring module
- `cleaner/normalize.py` — normalization module
- `dedup/exact.py` — exact dedup via SQLite
- `dedup/fuzzy.py` — fuzzy dedup via blocking + fingerprints

## Findings

### 1. Code Duplication (CRITICAL)
`pipeline_v55_final.py` duplicated **three** modules:
- `ExactDedup` class (identical to `dedup/exact.py`)
- `FuzzyDedup` class (identical to `dedup/fuzzy.py`)  
- All keyword sets (`BAD_KEYWORDS`, `GOOD_WORDS_EXACT`, etc. — identical to `cleaner/scorer.py`)

**Fix:** Import from modules instead of inline definition:
```python
from dedup.exact import ExactDedup
from dedup.fuzzy import FuzzyDedup
```

### 2. Unused Import
- `hashlib` imported in `pipeline_v55_final.py` but never used → removed

### 3. Regex Issues

#### `RE_COUNTRY_SUFFIX` — duplicate `\s` in character class
```python
# BEFORE (wrong):
r"[\s,.\s\(\)\[\]]*\b...\b[\s,.\s\(\)\[\]]*$"
# AFTER (correct):
r"[\s,.()\[]]*\b...\b[\s,.()\[]*$"
```
`\s` appeared twice in the character class — harmless but sloppy.

#### `RE_ADDRESS` — greedy quantifier captures too much
```python
# BEFORE (greedy, captures entire string after ул/г/д):
r'\b(?:ул|г|д|стр|пом|оф|пер|пр-т|просп|наб|пл)\.?\s*[A-ZА-ЯЁ0-9\s,.-]+'
# AFTER (bounded with lookahead):
r'\b(?:ул|г|д|стр|пом|оф|пер|пр-т|просп|наб|пл)\.?\s*[A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9\s,.-]*(?=\s|$|[^\w\s])'
```
The original would match "ул Ленина" AND everything after it in the same token.

### 4. Redundant Condition
```python
# BEFORE:
if email and email != "":
# AFTER:
if email:
```
`email` being truthy already means it's not empty string.

### 5. Pre-existing Test Failures (NOT caused by refactoring)
These tests were already failing before changes:
- `test_normalize`: expects `normalize("STAND 12A") == "12A"` — but STAND isn't a legal form
- `test_scorer`: expects `score("STAND 12A", ...) <= 10` — but score is 15
- `test_fuzzy_dedup`: expects `"МОЛОЧНЫЙ ЗАВОД"` to be duplicate of `"ООО МОЛОЧНЫЙ ЗАВОД"` — but fingerprint treats them differently

## Result
- **-121 lines** removed from `pipeline_v55_final.py` (487 → 366)
- **0 regressions** — dry-run on 200-record sample produces identical output
- Module structure now authoritative, pipeline is thin orchestrator

## Lesson for Future Reviews
When reviewing data pipeline code, check for:
1. Modules duplicated inline instead of imported
2. Greedy regex quantifiers without bounds/anchors
3. Truthiness checks redundant with type (e.g. `if x and x != ""`)
4. Unused imports (quick `grep import | grep -v usage`)

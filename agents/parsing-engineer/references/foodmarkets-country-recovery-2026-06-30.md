# FoodMarkets Country Recovery — 2026-06-30

## Context
FoodMarkets.ru parser (`foodmarkets_parse_v3.py`) was active 29.06.2026, processed 17 CIS towns. Upload via `foodmarkets_to_clean.py` loaded 3,766 records into `clean_clients` but country field was left empty for 87% of them.

## FoodMarkets Data Format
FoodMarkets entries include:
- Town name (often in URL path or extraction context)
- Company name with possible country/location suffix
- Phone (masked 1111111 = invalid, filtered)
- Email, website from detail pages
- Source always = `foodmarkets`

## Recovery Approach
Since foodmarkets_parse_v3.py processed by town (e.g., "алмату", "ташкент", "ереван"), the town→country mapping is implicit:

```python
FOODMARKETS_TOWN_COUNTRY = {
    'алмату': 'Казахстан',
    'астана': 'Казахстан', 
    'шымкент': 'Казахстан',
    'ташкент': 'Узбекистан',
    'самарканд': 'Узбекистан',
    'ереван': 'Армения',
    'баку': 'Азербайджан',
    'тбилиси': 'Грузия',
    'ашхабад': 'Туркменистан',
    'бишкек': 'Кыргызстан',
    'душанбе': 'Таджикистан',
    # Russian towns → Россия
}
```

### Step-by-step recovery
1. SELECT all source='foodmarkets' records with country=None
2. For each, check description for town name → map to country
3. If no town in description → detect_cis(name+description) fallback
4. PATCH with cleaned name + country

## Key Learning
**Parser/Upload contract**: country MUST be assigned at parse/upload time, not deferred to pipeline. The pipeline is for scoring/dedup, not for filling required fields.

## Files
- Parser: `~/.hermes/skills/layer3-parser/scripts/parsers/foodmarkets_parse_v3.py` (if exists) or in scripts/
- Upload: `~/.hermes/skills/layer3-parser/scripts/foodmarkets_to_clean.py` or foodmarkets_upload.py

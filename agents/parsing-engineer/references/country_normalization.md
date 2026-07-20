# COUNTRY NORMALIZATION FOR B2B PARSING

## Problem
- Prodexpo PDF data uses **Russian text** for countries (e.g., "Россия", "Казахстан").
- Supabase filtering and CIS aggregation require **ISO codes** (RU, KZ, BY).
- Manual mapping is error-prone and breaks CIS filtering.

## Solution
### Mapping Table
| Russian Name          | ISO Code | CIS? |
|-----------------------|----------|------|
| Россия                | RU       | ✅   |
| Казахстан             | KZ       | ✅   |
| Беларусь             | BY       | ✅   |
| Узбекистан            | UZ       | ✅   |
| Кыргызстан            | KG       | ✅   |
| Таджикистан           | TJ       | ✅   |
| Армения               | AM       | ✅   |
| Азербайджан           | AZ       | ✅   |
| Молдова               | MD       | ✅   |
| Туркменистан          | TM       | ✅   |

### Normalization Script
```python
# Add to scripts/normalize_countries.py
COUNTRY_MAP = {
    "Россия": "RU",
    "Казахстан": "KZ",
    "Беларусь": "BY",
    "Узбекистан": "UZ",
    "Кыргызстан": "KG",
    "Таджикистан": "TJ",
    "Армения": "AM",
    "Азербайджан": "AZ",
    "Молдова": "MD",
    "Туркменистан": "TM"
}

def normalize_country(record):
    country = record.get('country', '').strip()
    record['country_iso'] = COUNTRY_MAP.get(country, country)
    record['is_cis'] = record['country_iso'] in ['RU', 'KZ', 'BY', 'UZ', 'KG', 'TJ', 'AM', 'AZ', 'MD', 'TM']
    return record
```

### Usage
- Run **before upload** to Supabase:
  ```python
  data = [normalize_country(record) for record in data]
  ```
- Filter CIS companies:
  ```python
  cis_companies = [r for r in data if r.get('is_cis')]
  ```

## Pitfalls
- **Case Sensitivity**: Ensure `.strip()` and exact string matching.
- **Missing Countries**: Default to original value if not in `COUNTRY_MAP`.
- **Supabase Schema**: Add `country_iso` and `is_cis` columns if missing.

## Example
```json
{
  "name": "ООО АгроСнаб",
  "country": "Россия",
  "country_iso": "RU",
  "is_cis": true
}
```
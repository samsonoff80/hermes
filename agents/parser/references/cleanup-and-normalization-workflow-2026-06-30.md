# Cleanup & Normalization Workflow — 30.06.2026

## Scenario
After bulk-loading JSON files into raw_parsed_data and running pipeline_v55_final.py, clean_clients has:
- Mixed country formats (Russia/Россия, Türkiye/Турция)
- Non-target countries (USA, Serbia, Uganda, Китай, Турция, etc.)
- Empty/None countries that can be recovered from name/description
- Need to delete non-target, normalize the rest, then enrich

## 🚨 CRITICAL: Target Countries — ТОЛЬКО СНГ кроме Беларуси и Украины

**User explicitly corrected this twice on 30.06.2026:**
1. "Китай и Турция Иран... не в СНГ, Украина не нцжна"
2. "Украина тоже не нужна"

**NEVER expand this list without explicit user approval.**

```python
TARGET_COUNTRIES = {
    'Россия', 'Казахстан', 'Узбекистан', 'Армения', 'Грузия', 'Азербайджан',
    'Кыргыстан', 'Таджикистан', 'Туркменистан', 'Молдова',
}

EXCLUDED_COUNTRIES = {
    'Беларусь', 'Республика Беларусь', 'Belarus',
    'Украина', 'Ukraine',
    'Китай', 'China',
    'Турция', 'Turkey', 'Türkiye',
    'Индия', 'India',
    'Иран', 'Iran',
    # + any other country NOT in TARGET_COUNTRIES
}
```

**PITFALL:** Do NOT add countries like "they import our raw materials" or "lots of data from them". The list is strictly CIS minus Belarus and Ukraine. Anything else goes to DELETE.

## Workflow Steps

### Step 1: Normalize Countries (PATCH, not re-upload)
Apply COUNTRY_NORMALIZE mapping via batch PATCH:
```python
COUNTRY_NORMALIZE = {
    'Russia': 'Россия', 'Russian Federation': 'Россия', 'Россия / Russia': 'Россия',
    'Kazakhstan': 'Казахстан', 'Республика Казахстан': 'Казахстан',
    'Uzbekistan': 'Узбекистан', 'Республика Узбекистан': 'Узбекистан',
    'Armenia': 'Армения', 'Республика Армения': 'Армения',
    'Georgia': 'Грузия', 'Azerbaijan': 'Азербайджан', 'Азербайджан': 'Азербайджан',
    'Kyrgyzstan': 'Кыргызстан', 'Киргизская Республика': 'Кыргызстан',
    'Tajikistan': 'Таджикистан', 'Turkmenistan': 'Туркменистан', 'Турkmенистан': 'Туркменистан',
    'Moldova': 'Молдова',
    'Belarus': 'Беларусь', 'Республика Беларусь': 'Беларусь',
    'Ukraine': 'Украина',
    # Mapping to SELF for normalization check
    'Россия, г. Москва,': 'Россия', 'Россия, г. Москва': 'Россия',
}

for rid, new_country in normalize_pairs:
    payload = json.dumps({'country': new_country}).encode()
    req = Request(f'{SB_URL}/rest/v1/clean_clients?id=eq.{rid}',
                  data=payload, headers=headers, method='PATCH')
    urlopen(req)
```

### Step 2: Detect CIS Country from name/description (fallback)
For records where country is still empty/None:
```python
CIS_KEYWORDS = {
    'россия': 'Россия', 'российск': 'Россия', 'москва': 'Россия',
    'казахстан': 'Казахстан', 'алматы': 'Казахстан',
    'узбекистан': 'Узбекистан', 'ташкент': 'Узбекистан',
    'армения': 'Армения', 'ереван': 'Армения',
    'грузия': 'Грузия', 'тбилиси': 'Грузия',
    'азербайджан': 'Азербайджан', 'баку': 'Азербайджан',
    'киргизстан': 'Кыргызстан', 'бишкек': 'Кыргызстан',
    'таджикистан': 'Таджикистан', 'душанбе': 'Таджикистан',
    'туркменистан': 'Туркменистан', 'ашхабад': 'Туркменистан',
    'молдова': 'Молдова', 'кишинёв': 'Молдова',
}
```

### Step 3: Delete Non-Target Records
**Only TARGET_COUNTRIES survive. Everything else gets deleted.**

```python
TARGET_COUNTRIES = {
    'Россия', 'Казахстан', 'Узбекистан', 'Армения', 'Грузия', 'Азербайджан',
    'Кыргыстан', 'Таджикистан', 'Туркменистан', 'Молдова',
}

# DELETE by batch of IDs
to_delete_ids = [str(r['id']) for r in non_target_records]  # str() IMPORTANT
ids_filter = ','.join(batch)
req = Request(f'{SB_URL}/rest/v1/clean_clients?id=in.({ids_filter})',
              headers=headers, method='DELETE')
```

### Step 4: Re-upload from raw_parsed_data (after full cleanup cycle)
When re-populating clean_clients from raw_parsed_data:
1. Fetch ALL records from raw_parsed_data
2. Filter by TARGET_COUNTRIES only
3. Upload in batches of 50 to 200

### Step 5: Enrichment (post-cleanup)
For records without contacts, use web_search:
- Query: "{name} {country} контакты телефон email сайт"
- Extract: phone, email, website from search results
- PATCH each record individually

## Key Pitfalls

### ID type mismatch
When using `id=in.(...)` for DELETE, IDs must be **strings**, not ints:
```python
to_delete_ids = [str(r['id']) for r in records]  # IMPORTANT: str() wrapper
```

### Russian characters in URL query
Always use `urllib.parse.quote()` for Russian in filters:
```python
country_encoded = urllib.parse.quote('Украина')
url = f'{SB_URL}/rest/v1/clean_clients?country=eq.{country_encoded}'
```

### Incomplete DELETE (pagination)
Supabase returns max 1000 per request. Loop until batch is empty:
```python
while True:
    req = Request(f'{SB_URL}/rest/v1/clean_clients?select=id&limit=1000&order=id', ...)
    batch = json.loads(resp.read())
    if not batch: break
    # DELETE this batch
```

## Metrics to Verify After Each Step
```python
from collections import Counter
countries = Counter(r.get('country') or 'None' for r in all_records)

has_phone = sum(1 for r in records if r.get('phone'))
has_email = sum(1 for r in records if r.get('email'))
has_website = sum(1 for r in records if r.get('website'))
```

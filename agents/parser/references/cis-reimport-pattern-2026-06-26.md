# CIS Countries Reimport Pattern — 26.06.2026

## Problem
CIS countries (except Russia) were accidentally deleted during cleanup because:
1. Country detection script loaded only first 1000 records
2. English country names (Kazakhstan, Uzbekistan, Belarus) weren't in KEEP_COUNTRIES set
3. ~2000+ records deleted in one run

## Solution: Full Reimport Pipeline

### Step 1: Export from raw_parsed_data by country
```python
CIS_COUNTRIES = ['Казахстан', 'Kazakhstan', 'Republic of Kazakhstan',
                 'Узбекистан', 'Uzbekistan', 'Азербайджан', 'Azerbaijan',
                 'Армения', 'Armenia', 'Кыргызстан', 'Kyrgyzstan',
                 'Таджикистан', 'Tajikistan', 'Туркменистан', 'Turkmenistan',
                 'Грузия', 'Georgia', 'Беларусь', 'Belarus', 'Republic of Belarus']

for country in CIS_COUNTRIES:
    # Use pagination by 1000, NOT single query
    offset = 0
    while True:
        batch = sb_get('raw_parsed_data', 1000, offset, f'country=eq.{country}')
        if not batch: break
        all_data.extend(batch)
        offset += 1000
```

### Step 2: Merge with previously parsed JSON files
```python
for safe_name in ["kazakhstan","uzbekistan",...]:
    path = f"/home/khadas/parsed_{safe_name}.json"
    extra = json.load(open(path))
    # Dedup by name
    existing_names = {c['name'] for c in all_data}
    for r in extra:
        if r['name'] not in existing_names:
            all_data.append(r)
```

### Step 3: Normalize countries BEFORE filtering
```python
COUNTRY_NORM = {
    'Kazakhstan': 'Казахстан', 'Republic of Kazakhstan': 'Казахстан',
    'Uzbekistan': 'Узбекистан', 'Azerbaijan': 'Азербайджан',
    'Armenia': 'Армения', 'Kyrgyzstan': 'Кыргызстан',
    'Tajikistan': 'Таджикистан', 'Turkmenistan': 'Туркменистан',
    'Georgia': 'Грузия', 'Belarus': 'Беларусь', 'Republic of Belarus': 'Беларусь',
}
for r in all_data:
    if r.get('country') in COUNTRY_NORM:
        r['country'] = COUNTRY_NORM[r['country']]
```

### Step 4: Filter non-profile (blacklist keywords)
```python
BLACKLIST = ['алкогол', 'мяс', 'рыб', 'корм', 'сахар', 'мёд ', 'чай ', 'кофе',
             'напитк', 'овощ', 'фрукт', 'макарон', 'круп', 'табак', 'космет']
filtered = [r for r in all_data if not any(bw in (r.get('description','') + r.get('name','')).lower() for bw in BLACKLIST)]
```

### Step 5: Dedup by (normalized_name, country)
```python
def normalize(s):
    s = (s or '').upper().strip()
    for suffix in ['ООО','ОАО','ЗАО','ПАО','АО','ИП','ТОО','LTD','LLC','INC']:
        s = s.replace(suffix, '')
    return re.sub(r'\s+', ' ', re.sub(r'[,\.\-\"\'\/\\()]', ' ', s)).strip()

seen = {}
deduped = []
for r in filtered:
    key = (normalize(r['name']), r.get('country',''))
    if key not in seen:
        seen[key] = r
        deduped.append(r)
```

### Step 6: Upload to clean_clients (name → name_clean mapping!)
```python
target_fields = ['name_clean', 'country', 'phone', 'email', 'website', 'description', 'source']
for i in range(0, len(deduped), 50):
    batch = deduped[i:i+50]
    clean_batch = []
    for r in batch:
        record = {}
        for f in target_fields:
            val = r.get(f, '')
            if f == 'name_clean' and not val:
                val = r.get('name', '')  # MAP name → name_clean!
            record[f] = val if val else None
        clean_batch.append(record)
    # POST to Supabase REST API
```

## Key Rules
1. **ALWAYS normalize countries BEFORE filtering** — PATCH English names to Russian first
2. **NEVER sample for country detection** — load ALL records
3. **name → name_clean mapping** — `name` column does NOT exist in clean_clients
4. **Batch size 50-100** for uploads, 500-1000 for downloads on VIM4
5. **DaData only works for legal entities** — 0% success for generic names
6. **Serper API key in temp_keys.json** — NOT in .env, limited to 100/day

## Results 26.06.2026
- Reimported: 2156 CIS companies (from 8154 raw → filtered → deduped)
- Kazakhstan: 900 raw → 141 clean
- Uzbekistan: 5860 raw → 478 clean
- Belarus: 420 raw → 48 clean
- Armenia: 60 raw → 316 clean (from manufacturers.ru)
- clean_clients total: 18,442 → 24,447 (after also adding parsed JSON files)

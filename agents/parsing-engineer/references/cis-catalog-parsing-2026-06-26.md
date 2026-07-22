# CIS Catalog Parsing Patterns (26.06.2026)

## Working Static HTML Catalogs (requests+BS4)

### factories.kz (Казахстан)
- **URL pattern:** `https://factories.kz/producers/{category_slug}?page={N}`
- **Categories:** `molochnaya-promyshlennost`, `bakaleynoe-proizvodstvo`, `proizvodstvo-muki-i-muchnykh-izdeliy`, `plodoovoschnaya-promyshlennost`, `prochee-pischevoe-proizvodstvo`
- **Company links:** `re.findall(r'<a[^>]*href="(/producers/[^"?#]+)"[^>]*>([^<]+)</a>', html)`
- **Detail page:** `https://factories.kz/producers/{slug}` — contains phone, email, website in meta description AND in visible text
- **Phone pattern:** `\+7[\d\s\(\)-]{7,}`
- **Email pattern:** `[\w.+-]+@[\w.-]+\.\w+`
- **Rate limit:** 0.2s between requests

### factories.by (Беларусь)  
- Same structure as factories.kz
- **Categories:** `konditerskaya-promyshlennost`, `pischevaya-promyshlennost`, `molochnaya-promyshlennost`, `maslozhirovaya-promyshlennost`, `proizvodstvo-muki-i-muchnykh-izdeliy`
- **Quality:** A (best source for Belarus food companies)

### manufacturers.ru (Все СНГ)
- **URL pattern:** `https://manufacturers.ru/enterprises-list/{country_code}--{category}`
- **Country codes:** `am-armeniya`, `az-azerbaidzhan`, `ge-gruziya`, `kz-kazakhstan`, `kg-kyrgyzstan`, `tj-tadzhikistan`, `tm-turkmenistan`, `uz-uzbekistan`
- **Categories:** `konditerskaya-promyshlennost`, `molochnaya-promyshlennost`, `pishchevaya-promyshlennost`
- **Extraction:** `<a href="/enterprises/...">COMPANY NAME</a>` — name only, NO contacts in list
- **Quality:** B (names only, but broad coverage of 9 countries)

### iteca.kz iframe ( Kazakhstan exhibitions)
- **URL pattern:** `https://reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode={exhibition_encoded}`
- **Exhibition codes:** `FoodExpo%20Qazaqstan%202025`
- **Structure:** Single `<td>` per company with name, category, country, stand concatenated
- **Parsing:** Find country as separator → name is everything before country

## JS/SPA/Protected Sites (Cannot Parse Directly)

| Site | Country | Blocker | Workaround |
|------|---------|---------|------------|
| flagma.uz | Узбекистан | reCAPTCHA | web_search |
| osoo.kg | Кыргызстан | HTTP 403 | web_search |
| e-register.am | Армения | Radware CAPTCHA | web_search |
| openinfo.uz | Узбекистан | Next.js SPA | web_search |
| orginfo.uz | Узбекистан | Next.js SPA | web_search |
| taxes.gov.az | Азербайджан | Next.js + CSRF | web_search |
| napr.gov.ge | Грузия | Next.js SPA | web_search |

## Supabase Schema Notes (26.06.2026)

### clean_clients table
- **NO `name` column!** Only `name_clean` — use `name_clean` for all name data
- **Real columns:** `id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`
- **Upload via REST API:** urllib.request POST, batches of 50, `Prefer: return=minimal`

### raw_parsed_data table
- **Real columns:** `id, name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, dedup_method, dedup_confidence, created_at`
- **DO NOT include `id`** in insert records (auto-generated)
- **DO NOT include non-existent columns** (city, address, categories, etc.)

## Pipeline V5.5 Bug (26.06.2026)
- **Bug:** `reject_reasons` double-counts when fuzzy_dedup rejects — adds both `fuzzy_dedup` AND the score reason (e.g. `high_score:45`)
- **Impact:** reject_reasons counts are inflated; actual rejected count is correct
- **Fix needed:** Track whether fuzzy_dedup was the reason, don't add score reason in that case

## Upload Pattern (Working)
```python
import urllib.request, json

SUPABASE_URL = '...'
SUPABASE_KEY = '...'

target_fields = ['name_clean', 'country', 'phone', 'email', 'website', 'description', 'source']

for i in range(0, len(companies), 50):
    batch = companies[i:i+50]
    clean_batch = []
    for r in batch:
        record = {f: r.get(f, '') or None for f in target_fields}
        record['name_clean'] = r.get('name_clean', '') or r.get('name', '')
        clean_batch.append(record)
    
    data = json.dumps(clean_batch).encode('utf-8')
    req = urllib.request.Request(
        f'{SUPABASE_URL}/rest/v1/clean_clients',
        data=data, method='POST',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal',
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        loaded += len(batch)
```

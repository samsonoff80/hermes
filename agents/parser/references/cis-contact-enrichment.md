# CIS Contact Enrichment (26.06.2026)

## Problem
DaData only works for Russian legal entities (0% for CIS).
Serper API key expired (403).
web_search via execute_code is the working method for CIS countries.

## Solution: web_search via execute_code
**Use the built-in `web_search` tool** available in `execute_code` — works with DuckDuckGo/Bing.

## Algorithm
```python
from hermes_tools import web_search
import json, re, urllib.request, os

# For each record without contacts:
clean = re.sub(r'[,.]?\s*(ПАВ|ЗАЛ|СТЕНД|PAV|HALL|STAND).*', '', name, flags=re.I).strip()
query = f"{clean} {country} контакты телефон".strip()

result = web_search(query, limit=3-5)
items = result.get('data', {}).get('web', [])

name_words = [w for w in clean.lower().split() if len(w) > 2 and w not in ['ooo','тоо','ип','ltd','llc']]

found = {}
for item in items:
    title = item.get('title', '')
    if name_words and not any(w in title.lower() for w in name_words):
        continue
    # Extract phone/email/website from description
    phones = re.findall(r'\+?\d[\d\s\(\)-]{7,}', desc)
    for p in phones:
        d = re.sub(r'\D', '', p)
        if len(d) >= 10 and len(d) <= 13 and (p.startswith('+') or d.startswith('8')):
            found.setdefault('phone', p.strip()); break
    emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w+', desc)
    if emails: found.setdefault('email', emails[0])
    if url and not any(s in url for s in ['youtube','facebook','instagram','2gis.','yandex','google.','icatalog','ba.prg']):
        found.setdefault('website', url)
    if 'phone' in found and 'email' in found: break
```

## Key Validation Rules
- Phone: must start with `+` or `8`, 10-13 digits, NOT Kazakhstan BIN (12 digits without +)
- Email: standard regex validation
- Website: skip youtube/facebook/2gis/yandex/google/icatalog/ba.prg.kz
- Match: at least one significant word from company name must appear in result title

## Performance
- ~3 sec/record (search + extract + PATCH)
- ~49 tool calls per 50 records (each web_search = 1 tool call)
- Hit rate: ~60% for Kazakh companies, lower for others

## Source Quality by Country
| Country | Best Source | Hit Rate | Notes |
|---------|------------|----------|-------|
| Казахстан | web_search + factories.kz | ~60% | factories.kz directory works via requests |
| Армения | manufacturers.ru | Parsed separately | DaData 0% |
| Узбекистан | web_search | ~30% | JS-rendered sites, search is only option |
| Беларусь | web_search + factories.by | ~30% | Similar to Kazakhstan |
| Others | web_search | ~20-30% | Low web presence |

## Known Limitations
- Serper API KEY EXPIRED (403) — replaced by web_search
- DaData doesn't find CIS companies at all
- Many CIS food company sites use JS rendering (requests doesn't help)
- BIN/IIN numbers mistaken as phones: Kazakhstan BIN = 12 digits without +

## Automation Pattern
Use cron job to process in batches:
- 50 records per run
- Every 5 minutes
- Total: ~1500 records in 2.5 hours
- Each run: fetch 50 records, search, PATCH results

## Supabase Filter for Unenriched Records
```
?phone=is.null&email=is.null&website=is.null&limit=50&offset=0
```
Once records are updated, they disappear from this filter automatically — 
no need to track progress state.

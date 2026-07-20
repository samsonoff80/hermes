# Serper Mass Enrichment Script Pattern — 27.06.2026

## Контекст
`~/enrich_serper_mass.py` — массовое обогащение базы clean_clients через Serper API (поиск Google).

## Паттерн continuous-mode (batch loop)

```python
import os, json, urllib.request

BATCH = 500
offset = 0
while True:
    records = sb_get(f'?select=id,name_clean,country&phone=is.null&email=is.null&website=is.null&limit={BATCH}&offset={offset}')
    if not records:
        break
    
    for i, r in enumerate(records):
        name = r.get('name_clean', '')
        country = r.get('country', '') or ''
        
        # 1. Clean name — remove legal forms, hall/stand keywords
        clean = re.sub(r'[,.]?\s*(ПАВ|ЗАЛ|СТЕНД|PAV|HALL).*', '', name, flags=re.I).strip()
        for s in ['ТОО','ООО','АО','ИП','LTD','LLC']:
            clean = clean.replace(s, '').strip(' ,')
        if len(clean) < 3: continue
        
        # 2. Serper search
        query = f"{clean} {country} контакты телефон сайт"
        result = serper_search(query, 5)
        
        # 3. Extract contacts
        found = {}
        phones = re.findall(r'\+?\d[\d\s\(\)-]{7,}', snippet)
        emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w+', snippet)
        # website validation: skip youtube, facebook, yandex.ru etc
        
        # 4. PATCH back
        sb_patch(r['id'], found)
        
        # 5. Rate limit
        time.sleep(0.3)
    
    offset += BATCH

# Supabase REST API calls
def sb_get(path):
    req = urllib.request.Request(f'{SU}/rest/v1/clean_clients{path}',
        headers={'apikey': SK, 'Authorization': f'Bearer {SK}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def sb_patch(rid, data):
    req = urllib.request.Request(f'{SU}/rest/v1/clean_clients?id=eq.{rid}',
        data=json.dumps(data).encode(), method='PATCH',
        headers={'apikey': SK, 'Authorization': f'Bearer {SK}',
                 'Content-Type': 'application/json', 'Prefer': 'return=minimal'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status
```

## Результаты запуска (27.06.2026)
- 200-значный тест: 120/200 enriched (60%), phones=88, emails=50, websites=112
- Массовое обогащение запущено в фоне на 8,904 записях
- Ожидаемое: ~5,340 обогащённых (60% × 8,904)

## Пройденные страны
Подходит для всех СНГ стран (RU, KZ, UZ, AZ, KG, GE, TJ, TM, AM).

## ⚠️ Rate Limit Serper — критическое поведение (27.06.2026)

**Проблема:** Serper API возвращает 429 (Too Many Requests) после ~600 запросов при delay 0.3s.

**Симптомы:**
- Скрипт с `time.sleep(0.3)` → первые 200 записей OK, затем 429
- Скрипт уходит в бесконечный цикл ошибок (`Too many errors, stopping`)
- Все последующие батчи возвращают 0 enriched

**Решение — безопасный режим:**
```python
# Безопасная скорость: 1 запрос/сек
time.sleep(1.0)

# При 429 → exponential backoff
if '429' in str(e):
    for backoff in [30, 60, 90]:
        time.sleep(backoff)
        try:
            result = serper_search(query)
            break
        except:
            continue
    else:
        stop()  # Ключ исчерпан или лимит

# При >10 consecutive errors → останов (не спамить)
consecutive_errors = 0
for r in records:
    try:
        ...
        consecutive_errors = 0
    except:
        consecutive_errors += 1
        if consecutive_errors > 10:
            print("Too many errors, stopping.")
            break
```

**Рекомендуемый скрипт:** `~/enrich_serper_safe.py` — уже включает:
- `time.sleep(1.0)` между запросами
- Consecutive error counter (>10 → stop)
- 429 → exponential backoff (30s, 60s, 90s)

**Продуктивность при 1 req/sec:**
- ~60 записей/мин
- ~3,600 записей/час
- 10,000 записей ≈ 2.8 часа (без простоев)

**ПОСЛЕ исчерпания Serper ключа:**
Используй `web_search` через `execute_code` как fallback:
- Скорость: ~6 записей/мин (30 записей за ~177s)
- Hit rate: ~47%
- Таймаут execute_code: 300s → макс 30 записей за вызов
- Нельзя запускать через subagent (таймаут 600s)

## ⚠️ Очистка мусорных названий перед обогащением (27.06.2026)

PDF-каталоги (ProdExpo) часто парсят обрывки текста как "компании".
**822 мусорных записи** были найдены и удалены в этой сессии.

**Паттерны мусора:**
```python
GARBAGE_KEYWORDS = [
    "выпуская конкурентоспособную", "задачу обеспечения граждан",
    "размеру выставочной экспозиции", "ческих способов производства",
    "ленного комплекса россии", "водства «Продэкспо",
    "является", "представляет", "осуществляет", "производит",
    "который", "которая", "которые", "более", "менее", "также",
]
def is_junk_name(name):
    if len(name) < 5: return True
    if name[0].islower() and not name[0].isdigit(): return True
    nl = name.lower()
    return any(kw in nl for kw in GARBAGE_KEYWORDS)
```

**Правило:** Перед обогащением — всегда очищай мусорные имена. 822 удалённых записи = 822 сэкономленных Serper запроса.

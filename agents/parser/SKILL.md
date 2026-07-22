## RECOVERY — ОБЯЗАТЕЛЬНО ПРОЧИТАТЬ ПЕРВЫМ
1. ПРОЧИТАЙ /home/khadas/.hermes/agents/parser/PROGRESS.md → смотри CURRENT
2. Продолжай с CURRENT, не начинай заново
3. После каждого шага обновляй CHECKPOINTS в /home/khadas/.hermes/agents/parser/PROGRESS.md
4. Завершил → доложи результат → CURRENT = "ожидание"

---

---
name: layer4-cleaner
description: Слой 4 — методолог очистки B2B-данных. Берёт сырые данные из raw_parsed_data (Supabase) и превращает в чистую базу clean_clients.
---

# МЕТОДОЛОГ ОЧИСТКИ — Слой 4

## КТО ТЫ
Методолог очистки данных. Берёшь сырые данные после парсинга и превращаешь в чистую базу.

## 🚨 ЦЕЛЕВЫЕ СТРАНЫ (строгий список — НЕ РАСШИРЯТЬ)
**Только СНГ кроме Беларуси и Украины.** Список утверждён пользователем 30.06.2026.
Дважды корректировался: "Китай/Турция/Иран не СНГ", "Украина не нужна".

```python
TARGET_COUNTRIES = {
    'Россия', 'Казахстан', 'Узбекистан', 'Армения', 'Грузия', 'Азербайджан',
    'Кыргызстан', 'Таджикистан', 'Туркменистан', 'Молдова',
}
```

**ЗАПРЕЩЕНО** добавлять Китай, Турцию, Индию, Иран, Египет, ОАЭ, Бразилию, Италию, Германию, или любые другие страны вне этого списка — даже если "импортёры сырья" или "много данных".

Подробности реализации: `references/cleanup-and-normalization-workflow-2026-06-30.md`

[Rest of the SKILL.md content remains the same as the existing version, with the following key additions:]

## ДИАГНОСТИКА КЛЮЧЕЙ API

Перед запуском pipeline проверяй валидность ключей API:
- **Serper API**: Используй команду `curl` для проверки ключа.
  Подробности: `references/serper_api_diagnostics.md`

## FALLBACK-СТРАТЕГИИ ДЛЯ ОБОГАЩЕНИЯ

Если основной источник (Serper API) недоступен:
1. Извлекай домен из `email` или социальных сетей.
2. Логируй ошибки и переключайся на fallback автоматически.

Подробности: `references/fallback_strategies.md`

## ОПТИМИЗАЦИЯ СКОРОСТИ PIPELINE

1. **Батчинг запросов**: Группируй до 50 компаний в один запрос к Serper API.
2. **Параллелизация**: Используй 5 потоков для обработки запросов.
3. **Кэширование**: Увеличь TTL кэша Serper API до 48 часов.

Подробности: `references/pipeline-v55-optimizations-2026-07-01.md`

## ОБРАБОТКА ОШИБОК API

1. Логируй все ошибки API в `enrichment.log`.
2. При ошибках `400` или `429` переключайся на fallback-стратегии.

Подробности: `references/error_handling.md`

## CRON-ЗАДАЧИ

Подробности: `references/cron-troubleshooting-2026-07-01.md`

### PDF-каталоги выставок (ПОЛНОЕ РУКОВОДСТВО)
См. `layer3-parser/SKILL.md` секция "Работа с PDF-каталогами выставок".
Ключевые источники уже обработаны: Prodexpo (2022-2026), Agroprodmash (2021-2025).
Для новых PDF: ОБЯЗАТЕЛЬНА 5-проходная очистка OCR-артефактов.
| **DaData suggest/party** | 0% для не-юрлиц | 3 rec/s | бесплатно | Работает ТОЛЬКО для ООО/ТОО/АО/ИП. Общие названия → 0% |
| **Playwright парсинг сайтов** | зависит от сайта | медленно | бесплатно | produkt.by: +159 BY. flagma: 0 (блокирует). krb.by: DNS fail |
| **Serper API** | **60%** | ~30 записей/мин | 100 запросов/день | ⭐ ЛУЧШИЙ для массового обогащения. knowledgeGraph содержит phone+website напрямую. Ключ в `.env` (SERPER_API_KEY) и `temp_keys.json` |

### Паттерн web_search обогащения (26.06.2026)
```python
# 1. Загрузить записи без контактов
records = sb_get('?select=id,name_clean,country&phone=is.null&email=is.null&website=is.null&limit=50')

# 2. Для каждой — очистить название от артефактов ProdExpo
clean = re.sub(r'[,.]?\s*(ПАВ|ЗАЛ|СТЕНД|PAV|HALL|STAND).*', '', name, flags=re.I).strip()

# 3. web_search с конкретным запросом
result = web_search(f"{clean} {country} контакты телефон", limit=5)

# 4. Извлечь контакты из snippet/title результатов
# Проверка: хотя бы одно значимое слово из названия должно быть в title
# Валидация: phone — 10-13 цифр, начинается с + или 8
# email — стандартный regex
# website — не youtube/facebook/2gis/yandex

# 5. PATCH обратно в Supabase
sb_patch(r['id'], {'phone': phone, 'email': email, 'website': website})
```

### Паттерн Playwright парсинга (26.06.2026)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto(url, wait_until='networkidle', timeout=20000)
    time.sleep(2)
    # Scroll for lazy loading
    for _ in range(3):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
    # Extract from rendered HTML
    companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
```
**Работает:** produkt.by (Беларусь), factories.kz (Казахстан)
**Не работает:** flagma.kz/uz (блокирует headless), krb.by (DNS), osoo.kg (JS-рендер)

## ОБОГАЩЕНИЕ ЧЕРЕЗ ПРЯМЫЕ API ПРОВАЙДЕРОВ (22.06.2026)

### Cloudflare AI (`@cf/meta/llama-3.2-3b-instruct`) — FREE, устойчивый к rate limits
- Работает стабильно для batch-задач, без жёстких rate limits
- Модель 3B — слабее 70B, но для простых задач (классификация, извлечение) достаточно
- **timeout=30s** (медленнее чем Mistral/Groq, но быстрее 60s)
- JSON ответы не всегда валидны — нужен robust parser с fallback
- Ключ: `CLOUDFLARE_API_KEY` + `CLOUDFLARE_ACCOUNT_ID` в `.env`
- URL: `https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/meta/llama-3.2-3b-instruct`
- **Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/enrich_contacts_cf.py`

**⚠️ Формат ответа Cloudflare AI (обновлено 24.06.2026):**
```json
{
  "result": {
    "choices": [{
      "message": {
        "content": "JSON text here..."
      }
    }]
  }
}
```
Правильный путь для извлечения текта: `data['result']['choices'][0]['message']['content']`
**НЕ использовать:** `data['result']['response']` (устарело)

### Fallback chain провайдеров (ОБНОВЛЕНО 25.06.2026)

1. **DaData** (`suggest/party`) — ⭐ БЕСПЛАТНЫЙ, без лимитов! Работает для конкретных юрлиц (ООО, ТОО, АО). НЕ работает для общих названий ("Кондитерские изделия"). **Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/enrich_v4.py`
2. **Cloudflare AI** (`@cf/meta/llama-3.2-3b-instruct`) — бесплатный, но ИМЕЕТ rate limit (429). Реально: ~2,740 запросов до 429. Модель 3B — JSON часто невалидный. timeout=60s. Подходит для небольших батчей (<2,000) или с delay=30s+.
3. **Serper** — 100 запросов/день (часто исчерпан). Работает для web-поиска по названию компании.
4. **Mistral direct** (`mistral-medium-latest`) — НЕ РАБОТАЕТ (401, ключ невалидный)
5. **Groq** (`llama-3.3-70b-versatile`) — rate limit 100K токенов/день (403 при превышении)
6. **SambaNova** (`Meta-Llama-3.3-70B-Instruct`) — агрессивный rate limit (429), НЕ подходит для batch
7. **OpenRouter** — требует кредиты (error 402)
8. **Consilium** — circuit breaker после 10 ошибок, только для единичных запросы
9. **Tavily** — 403 Forbidden (заблокирован)
10. **Fel** — DNS не резолвится

**ВЫВОД:** Для массового обогащения (>1K записей) лучший вариант — **DaData** (бесплатно, без лимитов). Но работает только для записей с конкретным юрлицом в названии (содержат ООО/ТОО/АО/ИП). Для общих названий ("Кондитерские изделия", "Молочная продукция") DaData не находит ничего — используй web_search или парсинг сайтов.

**Детали в:** `references/contact-enrichment-apis-2026-06-24.md`

**⚠️ Serper API — ПРОВЕРИТЬ ПЕРЕД ЗАПУСКОМ (возможно истёк)**
- **Ключ:** `SERPER_API_KEY` в `.env` и `temp_keys.json`
- **Endpoint:** `https://google.serper.dev/search`
- **Hit rate:** ~60% (120/200 в тестовом запуске 27.06.2026)
- **Скорость:** ~30 записей/мин (delay 0.3s)
- **Rate limit:** 429 → sleep 60s
- **Скрипт:** `~/enrich_serper_mass.py` — continuous mode, batches of 500
- **Перед запуском:** `curl -s -o /dev/null -w "%{http_code}" -H "X-API-KEY: $KEY" https://google.serper.dev/search?q=test` → если 403, ключ истёк
- **Если Serper недоступен:** использовать `web_search` (60-67% hit rate, бесплатно)

**⚠️ DaData обогащение — 0% для не-юрлиц (26.06.2026)**
DaData `suggest/party` работает ТОЛЬКО для конкретных юрлиц (ООО, ТОО, АО, ИП). Для общих названий ("Кондитерские изделия", "Молочная продукция") возвращает 0 результатов.
**Симптом:** Скрипт обогащения отработал 14K записей, enriched=0.
**Решение:** Для не-юрлиц используйте **Serper API** (60% hit rate) или web_search + извлечение контактов с сайтов, или примите что это категории, не компании.

### Playwright парсинг JS-каталогов СНГ (26.06.2026)

Для сайтов с JS-рендером (каталоги производителей) используется Playwright headless Chromium.

**Работающие сайты:**
- `produkt.by` (Беларусь) — +159 новых компаний
- `factories.kz` (Казахстан) — +312 компаний
- `tmtrade_tj` (Таджикистан) — 81 компания загружена

**Заблокированные/неработающие:**
- `flagma.kz`, `flagma.uz` — блокируют headless browsers
- `n4.biz` — проблемы с навигацией/селекторами
- `krb.by` — DNS не резолвится на VIM4
- `osoo.kg` — JS-рендер, требует кастомных селекторов
- `georgiayp.com` — проблемы с селекторами

**Паттерн Playwright парсинга:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto(url, wait_until='networkidle', timeout=20000)
    time.sleep(2)
    # Scroll for lazy loading
    for _ in range(3):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
    # Extract from rendered HTML
    companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
```

**Детали в:** `references/cis-reimport-pattern-2026-06-26.md` — паттерн восстановления после случайного удаления стран

### Обогащение через DaData — ограничения (25.06.2026)

**Проблема:** В clean_clients ~5,982 записей без контактов. Из них ~2,100 уже имеют контакты (предыдущие запуски). Оставшиеся ~3,800 — это записи с общими названиями типа:
- "Кондитерские изделия" (категория, не компания)
- "Молочная продукция и сыры" (описание продукта)
- "Детское питание" (категория)

DaData API ищет по названию юрлица. Для общих названий возвращает 0 результатов.

**Решение:** Для таких записей нужно:
1. Извлечь из description или других полей название конкретной компании
2. Использовать web_search по категории + страна
3. Принять что не все записи можно обогатить (это нормально — это категории, не компании)

**Статистика запуска 25.06.2026:** enrich_v4.py обработал 2,200 записей, 0 enriched (DaData не нашёл). Скорость 2.5-3/s.

**Детали в:** `references/contact-enrichment-apis-2026-06-24.md`

**⚠️ Serper API — ПРОВЕРИТЬ ПЕРЕД ЗАПУСКОМ (возможно истёк)**
- **Ключ:** `SERPER_API_KEY` в `.env` и `temp_keys.json`
- **Endpoint:** `https://google.serper.dev/search`
- **Hit rate:** ~60% (120/200 в тестовом запуске 27.06.2026)
- **Скорость:** ~30 записей/мин (delay 0.3s)
- **Rate limit:** 429 → sleep 60s
- **Скрипт:** `~/enrich_serper_mass.py` — continuous mode, batches of 500
- **Перед запуском:** `curl -s -o /dev/null -w "%{http_code}" -H "X-API-KEY: $KEY" https://google.serper.dev/search?q=test` → если 403, ключ истёк
- **Если Serper недоступен:** использовать `web_search` (60-67% hit rate, бесплатно)

**⚠️ DaData обогащение — 0% для не-юрлиц (26.06.2026)**
DaData `suggest/party` работает ТОЛЬКО для конкретных юрлиц (ООО, ТОО, АО, ИП). Для общих названий ("Кондитерские изделия", "Молочная продукция") возвращает 0 результатов.
**Симптом:** Скрипт обогащения отработал 14K записей, enriched=0.
**Решение:** Для не-юрлиц используйте **Serper API** (60% hit rate) или web_search + извлечение контактов с сайтов, или примите что это категории, не компании.

### Playwright парсинг JS-каталогов СНГ (26.06.2026)

Для сайтов с JS-рендером (каталоги производителей) используется Playwright headless Chromium.

**Работающие сайты:**
- `produkt.by` (Беларусь) — +159 новых компаний
- `factories.kz` (Казахстан) — +312 компаний
- `tmtrade_tj` (Таджикистан) — 81 компания загружена

**Заблокированные/неработающие:**
- `flagma.kz`, `flagma.uz` — блокируют headless browsers
- `n4.biz` — проблемы с навигацией/селекторами
- `krb.by` — DNS не резолвится на VIM4
- `osoo.kg` — JS-рендер, требует кастомных селекторов
- `georgiayp.com` — проблемы с селекторами

**Паттерн Playwright парсинга:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto(url, wait_until='networkidle', timeout=20000)
    time.sleep(2)
    # Scroll for lazy loading
    for _ in range(3):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
    # Extract from rendered HTML
    companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
```

**Детали в:** `references/cis-reimport-pattern-2026-06-26.md` — паттерн восстановления после случайного удаления стран

### Обогащение через DaData — ограничения (25.06.2026)

**Единственный рабочий провайдер для массового обогащения!**

- **Ключ**: `~/.hermes/skills/consilium/temp_keys.json` → `keys.SERPER_API_KEY.current`
- **Лимит**: 100 запросов/день (исчерпается быстро!)
- **URL**: `https://google.serper.dev/search`
- **Headers**: `X-API-KEY: {key}`
- **Body**: `{"q": "Company Name Country phone email website", "num": 5}`
- **Скорость**: ~40 записей/минуту
- **Качество**: высокий для RU/TR/EU компаний, низкий для KZ/CN без сайтов

**КРИТИЧНО**: Ключ хранится в `temp_keys.json`, НЕ в `.env`!
Формат: `{"keys": {"SERPER_API_KEY": {"status": "active", "limit": "100/день", "current": "b786f25e..."}}}`

**Извлечение контактов из ответа:**
```python
text = ''
for item in result.get('organic', [])[:5]:
    text += ' ' + item.get('snippet', '') + ' ' + item.get('title', '')
phones = re.findall(r'[\+]?[78][\s\-]?[\(]?\d{3}[\)]?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text)
emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w{2,}', text)
```

**Детали в:** `references/contact-enrichment-apis-2026-06-24.md`

**⚠️ Serper API — ПРОВЕРИТЬ ПЕРЕД ЗАПУСКОМ (возможно истёк)**
- **Ключ:** `SERPER_API_KEY` в `.env` и `temp_keys.json`
- **Endpoint:** `https://google.serper.dev/search`
- **Hit rate:** ~60% (120/200 в тестовом запуске 27.06.2026)
- **Скорость:** ~30 записей/мин (delay 0.3s)
- **Rate limit:** 429 → sleep 60s
- **Скрипт:** `~/enrich_serper_mass.py` — continuous mode, batches of 500
- **Перед запуском:** `curl -s -o /dev/null -w "%{http_code}" -H "X-API-KEY: $KEY" https://google.serper.dev/search?q=test` → если 403, ключ истёк
- **Если Serper недоступен:** использовать `web_search` (60-67% hit rate, бесплатно)

**⚠️ DaData обогащение — 0% для не-юрлиц (26.06.2026)**
DaData `suggest/party` работает ТОЛЬКО для конкретных юрлиц (ООО, ТОО, АО, ИП). Для общих названий ("Кондитерские изделия", "Молочная продукция") возвращает 0 результатов.
**Симптом:** Скрипт обогащения отработал 14K записей, enriched=0.
**Решение:** Для не-юрлиц используйте **Serper API** (60% hit rate) или web_search + извлечение контактов с сайтов, или примите что это категории, не компании.

### Playwright парсинг JS-каталогов СНГ (26.06.2026)

Для сайтов с JS-рендером (каталоги производителей) используется Playwright headless Chromium.

**Работающие сайты:**
- `produkt.by` (Беларусь) — +159 новых компаний
- `factories.kz` (Казахстан) — +312 компаний
- `tmtrade_tj` (Таджикистан) — 81 компания загружена

**Заблокированные/неработающие:**
- `flagma.kz`, `flagma.uz` — блокируют headless browsers
- `n4.biz` — проблемы с навигацией/селекторами
- `krb.by` — DNS не резолвится на VIM4
- `osoo.kg` — JS-рендер, требует кастомных селекторов
- `georgiayp.com` — проблемы с селекторами

**Паттерн Playwright парсинга:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto(url, wait_until='networkidle', timeout=20000)
    time.sleep(2)
    # Scroll for lazy loading
    for _ in range(3):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
    # Extract from rendered HTML
    companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
```

**Детали в:** `references/cis-reimport-pattern-2026-06-26.md` — паттерн восстановления после случайного удаления стран

### Обогащение через DaData — ограничения (25.06.2026)
```python
text = ''
for item in result.get('organic', [])[:5]:
    text += ' ' + item.get('snippet', '') + ' ' + item.get('title', '')
phones = re.findall(r'[\+]?[78][\s\-]?[\(]?\d{3}[\)]?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text)
emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w{2,}', text)
```

**Детали в:** `references/contact-enrichment-apis-2026-06-24.md`

**⚠️ Serper API — ПРОВЕРИТЬ ПЕРЕД ЗАПУСКОМ (возможно истёк)**
- **Ключ:** `SERPER_API_KEY` в `.env` и `temp_keys.json`
- **Endpoint:** `https://google.serper.dev/search`
- **Hit rate:** ~60% (120/200 в тестовом запуске 27.06.2026)
- **Скорость:** ~30 записей/мин (delay 0.3s)
- **Rate limit:** 429 → sleep 60s
- **Скрипт:** `~/enrich_serper_mass.py` — continuous mode, batches of 500
- **Перед запуском:** `curl -s -o /dev/null -w "%{http_code}" -H "X-API-KEY: $KEY" https://google.serper.dev/search?q=test` → если 403, ключ истёк
- **Если Serper недоступен:** использовать `web_search` (60-67% hit rate, бесплатно)

**⚠️ DaData обогащение — 0% для не-юрлиц (26.06.2026)**
DaData `suggest/party` работает ТОЛЬКО для конкретных юрлиц (ООО, ТОО, АО, ИП). Для общих названий ("Кондитерские изделия", "Молочная продукция") возвращает 0 результатов.
**Симптом:** Скрипт обогащения отработал 14K записей, enriched=0.
**Решение:** Для не-юрлиц используйте **Serper API** (60% hit rate) или web_search + извлечение контактов с сайтов, или примите что это категории, не компании.

### Playwright парсинг JS-каталогов СНГ (26.06.2026)

Для сайтов с JS-рендером (каталоги производителей) используется Playwright headless Chromium.

**Работающие сайты:**
- `produkt.by` (Беларусь) — +159 новых компаний
- `factories.kz` (Казахстан) — +312 компаний
- `tmtrade_tj` (Таджикистан) — 81 компания загружена

**Заблокированные/неработающие:**
- `flagma.kz`, `flagma.uz` — блокируют headless browsers
- `n4.biz` — проблемы с навигацией/селекторами
- `krb.by` — DNS не резолвится на VIM4
- `osoo.kg` — JS-рендер, требует кастомных селекторов
- `georgiayp.com` — проблемы с селекторами

**Паттерн Playwright парсинга:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto(url, wait_until='networkidle', timeout=20000)
    time.sleep(2)
    # Scroll for lazy loading
    for _ in range(3):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
    # Extract from rendered HTML
    companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
```

**Детали в:** `references/cis-reimport-pattern-2026-06-26.md` — паттерн восстановления после случайного удаления стран

### Обогащение через DaData — ограничения (25.06.2026)

После очистки и обогащения — удали компании из не-СНГ стран.

**Целевые страны (ОСТАВИТЬ):**
россия, казахстан, беларусь, узбекистан, кыргызстан, таджикистан, армения, азербайджан, молдова, туркменистан, украина, грузия, турция

**Удалить:** китай, индия, бразилия, япония, италия, германия, франция, польша, нидерланды, и все остальные не-СНГ

**Подход:** Сканируй clean_clients пагинацией, собирай ID не-СНГ, удаляй батчами по 20-30.
Используй `DELETE` по одному ID (batch delete не поддерживается Supabase REST API).

**Скрипт:** `~/audit/filter_cities.py` (создаётся на лету в сессии)

### Полная пересборка базы с нуля (28.06.2026)

Когда пользователь говорит "начинаем с нуля", "очисти всё и заново":
1. `DELETE ?id=gt.0` для raw_parsed_data и clean_clients
2. Очить source_profiles по ID
3. Запустить полный цикл: scout → parse → pipeline → enrich
4. Детали: `references/full-base-rebuild-2026-06-28.md`

### Ключевые паттерны

**Синхронные скрипты вместо asyncio** — asyncio + urllib.request блокирует event loop при массовых запросах к Supabase. Используй синхронные скрипты.

**extract_json()** — ВСЕ модели оборачивают JSON в markdown-блоки. Всегда извлекай:
```python
def extract_json(text):
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m: return m.group(1)
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m: return m.group(0)
    return None
```

**Фоновые скрипты** — всегда `python3 -u script.py 2>&1` или `PYTHONUNBUFFERED=1`

**Два типа пустых полей** — `country=is.null` И `country=eq.` — всегда загружай оба!

**⚠️ Python .format() с JSON** — промпты с JSON-примерами (`{"id": "..."}`) ЛОМАЮТ `.format()`. Используй двойные скобки: `{{"id": "..."}}`. Детали в references/enrichment-direct-api-2026-06-22.md.

**Mistral rate limit** — возвращает `{}` (пустой JSON), НЕ ошибку. Проверяй результат!

**Двухэтапный подход к странам** — Mistral возвращает SKIP/DELETE для ~40% записей (мусор, не-СНГ). Это нормально. Сначала удаляй по паттернам (стенды, каталоги, не-СНГ страны в названии), потом Mistral для оставшихся. Детальные паттерны в `references/enrichment-direct-api-2026-06-22.md`.

**sb_patch retry** — `Connection reset by peer` при массовых PATCH. Всегда используй retry loop с exponential backoff:
```python
def sb_patch(mid, data):
    url = f"{SUPABASE_URL}/rest/v1/clean_clients?id=eq.{mid}"
    body = json.dumps(data).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=body, headers=HEADERS_SB, method='PATCH')
            with urllib.request.urlopen(req, timeout=30) as r:
                return True
        except urllib.error.HTTPError as e:
            if e.code in (204, 409): return True
            return False
        except Exception:
            if attempt < 4:
                time.sleep(2 ** attempt)  # 1, 2, 4, 8, 16s
            else:
                return False
    return False
```

**Прогресс-вывод при загрузке** — добавляй `print(f"loaded {len(recs)}...", flush=True)` в цикл пагинации.

**⚠️ urllib 400 на Supabase** — `urllib.request` иногда даёт HTTP 400 на Supabase REST API (при работе из Python). `curl` работает стабильно. Для экспорта/загрузки больших объёмов используй `subprocess.run(["curl", "-s", url, ...])`. Для обогащения (sb_get/sb_patch) urllib работает, но sb_patch требует retry.

**⚠️ Пустые поля: два типа** — `country=is.null` (NULL) И `country=eq.` (пустая строка). Всегда загружай оба! На 22.06.2026: NULL=25, empty=5,004.

**⚠️ Mistral возвращает `{}` при rate limit** — это НЕ ошибка API, это пустой JSON в ответе. Проверяй `if not result or result == '{}'` перед `json.loads()`.

**Mistral phone enrichment = 0** — Mistral не может найти телефоны по названию компании. Phone enrichment через LLM бесполезен. Нужен Serper/web-scraping для телефонов.

**Нормализация стран** — после Mistral проверяй результат через `norm_country()`. Mistral может вернуть "Russia" (англ.), "Кыргызтан" (неправильно), "Беларусь" (не целевая). Детали в `references/country-normalization-2026-06-21.md`.

## Уроки 28.06.2026

### Полная пересборка базы с нуля (full rebuild)
Когда пользователь говорит "начинаем с нуля", "очисти всё и заново":
1. `DELETE ?id=gt.0` для raw_parsed_data, clean_clients, source_profiles
2. **auto_scout_v2**: web_search по 9 странам СНГ → 18-22 доступных источника → фильтр на реальные каталоги (~5-6)
3. **Source profiles**: INSERT проверенных каталогов (fabricators.ru, rfactories, areg.am и т.д.)
4. **Парсинг**: универсальный regex-парсер → дедуп по name+country → загрузка в raw_parsed_data (~3K записей)
5. **Pipeline V5.5**: raw → clean (~25-30% acceptance), фильтр не-СНГ → ~2,200-2,500
6. **Обогащение**: web_search батчами по 25 через execute_code
- Детали+метрики: `references/full-base-rebuild-2026-06-28.md`, `references/full-pipeline-run-2026-06-28.md`

### web_search обогащение — ЕДИНСТВЕННЫЙ рабочий метод (28.06.2026)
- ❌ DuckDuckGo API: 0% hit rate | ❌ Groq LLM: выдумывает номера + `.is_('phone','null')` падает | ❌ OpenRouter free: 429
- ✅ **web_search (встроенный в Hermes)**: 30-65% hit rate, бесплатно
- **КРИТИЧНО:** web_search доступен ТОЛЬКО через `execute_code`, не standalone!
- Таймаут execute_code = 300с → макс ~25 записей за запуск
- Прогресс-файл `/tmp/enrich_progress_final.json` обязателен (сохранять каждые 5 записей)
- Паттерн: `references/contact-enrichment-resumable-pattern-2026-06-28.md`
- Плохие домены для website: youtube, facebook, vk.com, 2gis, yandex, google, instagram, ok.ru, linkedin, t.me

### Supabase REST: `id=not.in.()` не работает для больших списков
- Большие IN (>100 ID) тормозят/таймаутят
- Решение: загружать limit=1000 по offset, фильтровать локально

### Background terminal + Python = tcsetattr hang
- `terminal(background=True, command="python3 ...")` → exit 143
- Python tries TTY but Hermes background mode has no PTY
- Workaround: execute_code для Python с web_search; foreground для standalone

## Уроки 22.06.2026

### Структура таблицы: category, moysklad_id, city, address НЕ существуют
**АКТУАЛЬНАЯ СТРУКТУРА clean_clients** (проверено 24.06.2026, подтверждено 26.06.2026):
```sql
id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at
```
**НЕТ полей**: `moysklad_id`, `category`, `name`, `city`, `address`, `legal_title`, `legal_address`, `inn`, `tags`, `group_tag`, `holding`, `products`, `needs_review`, `confidence`, `data_score`, `updated_at`

**⚠️ КРИТИЧНО (26.06.2026):** Поле `name` НЕ существует в `clean_clients`! Попытка вставить `name` → ошибка 400: `Could not find the 'name' column of 'clean_clients' in the schema cache`. Используйте `name_clean` для названия компании. Если входные данные имеют колонку `name` — маппайте её в `name_clean`.

### Mistral API Key может быть невалидным (401)
**Рекомендация:** Загружать ВСЕ компании (не только пищевые), т.к. данные всё равно бесплатные. Фильтрацию делать позже.
**Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/load_opensanctions_kz.py`

### SambaNova — новый провайдер (22.06.2026)
Добавлен в consilium: `sambanova/Meta-Llama-3.3-70B-Instruct`.
- API: `https://api.sambanova.ai/v1/chat/completions`
- Работает стабильно, быстрый ответ (~0.1s)
- Ключ: `SAMBANOVA_API_KEY` в `.env`
- Можно использовать напрямую (без consilium) для batch-обогащения
- **Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/enrich_contacts_samba.py`
- **Детали:** `references/sambanova-provider-2026-06-22.md`

### Проверка API ключей перед запуском (22.06.2026)
**ВСЕГДА** проверяй ключ перед batch-задачей:
```bash
curl -s -o /dev/null -w "%{http_code}" "https://api.sambanova.ai/v1/models" -H "Authorization: Bearer $KEY"
curl -s -o /dev/null -w "%{http_code}" "https://api.mistral.ai/v1/models" -H "Authorization: Bearer $KEY"
```
Mistral 401 = ключ невалидный. Groq 403 = rate limit.

### Проверка схемы Supabase перед записью (22.06.2026)
**ВСЕГДА** проверяй существование полей перед массовой записью:
```bash
curl -s ".../rest/v1/table?select=*&limit=1" | python3 -c "import sys,json; print(list(json.loads(sys.stdin.read())[0].keys()))"
```
Частые ошибки: `raw_json` (нет в raw_parsed_data), `status`/`reg_date` (нет), `activity_type` (нет, есть `category`).

### f-string escaping с JSON (22.06.2026)
Python f-string с `{` и `}` в JSON-примерах вызывает `SyntaxError`. Используй конкатенацию:
```python
# ПРАВИЛЬНО:
prompt = 'Return JSON: {"id": {"phone": null}}' + chr(10).join(lines)

# НЕПРАВИЛЬНО (SyntaxError):
prompt = f'Return JSON: {{"id": {{"phone": null}}}}'  # не работает!
```

### Keyword-классификация (основной метод, 24.06.2026)
Когда LLM недоступен или для полной переочистки базы, используй keyword-подход.
**Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/full_cleanup.py` (полный пайплайн)
**Паттерны:** 50+ regex для 13 целевых категорий в `FOOD_KEYWORDS`
Категории записываются в `description` как `[категория]` (поле `category` не существует в clean_clients).

**Устаревший скрипт:** `/home/khadas/.hermes/agents/parser/scripts/filter_categories.py` — работает со старой схемой (с `category`). Не используй для новых данных.

## ФИЛЬТРАЦИЯ ПО ЦЕЛЕВЫМ КАТЕГОРИЯМ (22.06.2026)

### Целевые категории (ОСТАВИТЬ)
**Финальный whitelist (25.06.2026, дало 9,087 записей из 72,153):**
- кондитерка, молочка, хлеб, детское питание, дистрибьюция, масла/жиры, заморозка, снеки, орехи, сухофрукты

**НЕ профиль (удалить):**
- чай/кофе, напитки, алкоголь, крупы, мука, макароны, мясо/рыба, овощи/фрукты, сахар/мёд, специи, корма/агро

### Скрипт фильтрации
**Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/filter_categories.py`
- Удаляет записи с нецелевыми категориями
- В "прочее" (12,057 записей) ищет целевые по ключевым словам в name_clean
- Переклассифицирует найденные целевые
- Остальное удаляет

### Типичные результаты
- Было: ~14,500 → Стало: ~1,600-2,000 (только целевые)
- ~12,800 удалено (нецелевые + неклассифицированные)
- ~200 переклассифицировано из "прочее" в целевые

### OpenSanctions KZ
Файл 1.67GB, JSONL формат. Скачивается медленно (~350KB/s, ETA ~80 мин).
**Реальная структура:** только name, country, status, incorporationDate — НЕТ okved, phone, email, address.
Загружать все компании, не только пищевые. Детали в `references/enrichment-lessons-2026-06-22.md`.
**Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/load_opensanctions_kz.py` (или `load_kz_v2.py` в /tmp)

### Массовое извлечение из Supabase (24.06.2026)

Для фильтрации/удаления сканируй таблицу пагинацией по 1000:

```python
all_data = []
offset = 0
while True:
    url = f"{SUPABASE_URL}/rest/v1/clean_clients?select=id,description&limit=1000&offset={offset}&order=id"
    req = urllib.request.Request(url, headers={'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY})
    with urllib.request.urlopen(req, timeout=60) as resp:
        batch = json.loads(resp.read())
        all_data.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    if offset % 5000 == 0:
        print(f'  {offset}...', flush=True)
    time.sleep(0.1)
```

**⚠️ Content-Range: */*** — когда нет записей, заголовок `Content-Range` возвращает `*/*`. Нельзя `int()` конвертировать. Проверяй перед парсингом.

**⚠️ 400 Bad Request** — `is.is.null` не работает в PostgREST. Загружай поля полностью и фильтруй локально.

### Cloudflare AI rate limit (22.06.2026)
- Cloudflare НЕ бесплатен для массового обогащения
- ~2,740 запросов до 429 (Too Many Requests)
- Для 10,411 записей нужно ~4 часа с delay=10s + повторы
- **Рекомендация:** использовать только для <2,000 записей или с delay=30s+

### Обогащение контактов через LLM — ограниченная эффективность (22.06.2026)
- Cloudflare 3B нашёл: phone:1,735 email:1,599 website:1,697 из 2,740 обработанных (до 429)
- ~63% записей получили хотя бы один контакт
- Телефоны: модели часто выдумывают или дают неправильные форматы
- **Валидация обязательна:** regex для email, проверка длины phone, формат website
- **Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/enrich_contacts_cf.py`

### Полный пайплайн очистки (24.06.2026)
**Детальный отчёт:** `references/full-pipeline-run-2026-06-24.md`

**Последовательность шагов:**
1. `mass_upload.py` — загрузка всех JSON → raw_parsed_data
2. `clean_step1.py` — классификация + дедуп → clean_clients
3. `filter_cities.py` — удаление не-СНГ
4. `enrich_cf.py` / `enrich_serper.py` — обогащение контактов

**Типичные результаты:**
- 514K сырых → 28K классифицированных → 24K уникальных (96% отброшено)
- 5,705 raw → 509 классифицированных → 332 уникальных (91% отброшено)
```bash
# Массовая загрузка всех JSON → raw_parsed_data
python3 ~/audit/mass_upload.py

# Полная очистка ВСЕХ сырых данных → clean_clients
python3 ~/audit/clean_step1.py

# Фильтрация по СНГ (удалить не-СНГ страны)
python3 ~/audit/filter_cities.py

# Обогащение контактов через Cloudflare AI
python3 ~/audit/enrich_cf.py
```

### Массовая загрузка готовых JSON (24.06.2026)
Когда есть предварительно спарсенные JSON-файлы, не нужно заново парсить PDF.
Сканируй `layer3-parser//home/khadas/.hermes/agents/parser/data/*.json` и `exhibition_pdfs/*_parsed.json`.
Нормализуй к единому формату → загружай батчами по 50 в `raw_parsed_data`.
**Скрипт:** `~/audit/mass_upload.py`
**Детали:** `references/mass-json-upload-2026-06-24.md`

### Структура таблицы clean_clients (проверено 24.06.2026)
**Реальные колонки**: `id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`

**НЕ существующие колонки** (не добавлять!): `moysklad_id, category, name, city, address, products, tags, group_tag, holding, confidence, data_score, needs_review, activity_type, legal_title, legal_address, inn, updated_at`

**Питфолл**: Поле `category` НЕ существует. Категорию хранить в `description` формате `[категория] описание`.

### Дедупликация
- Ключ: `(normalize(name), country)` — компании с одинаковым названием из РАЗНЫХ стран = РАЗНЫЕ компании
- Порядок: сначала нормализация → потом дедупликация

### Загрузка в Supabase — критические правила (24.06.2026, обновлено 27.06.2026)
1. **НЕ включать `id` в запись** — UUID генерируется автоматически, пустая строка → ошибка 22P02
2. **PGRST102**: все объекты в батче должны иметь ИДЕНТИЧНЫЙ набор ключей
3. **`duplicate_of`** — не включать если пустое (UUID не принимает "")
5. **Батчи по 50-100** стабильно работают
6. **urllib.request** > requests/curl для Supabase REST API
7. **⚠️ Колонка `name` НЕ существует в clean_clients!** — используйте `name_clean`
8. **⚠️ Страны на английском → нормализовать ДО фильтрации!** — `Kazakhstan`, `Uzbekistan`, `Belarus` не распознаются как СНГ без нормализации. Без этого ~2000+ записей удаляются
9. **⚠️ Supabase REST API limit на VIM4** — максимум ~1000 записей на запрос. Пагинация 500-1000 обязательна
**Pipeline V5.5 баг:** `references/pipeline-v55-double-counting-bug-2026-06-26.md`
**Экспорт из Supabase:** `references/supabase-rest-export-pattern-2026-06-26.md`
**CIS Reimport Pattern:** `references/cis-reimport-pattern-2026-06-26.md`

## ПОЛНЫЙ ЦИКЛ ОЧИСТКИ БАЗЫ (25.06.2026, обновлено 25.06.2026)

### Когда использовать
Когда пользователь просит "привести базу в порядок", "почистить от ошибок", "финальная чистка", "проверь и исправь".

### Алгоритм (6 этапов, последовательно)

**Этап 1 — Нормализация стран:**
- Загрузить все записи через supabase-py
- Найти записи с мусором в country (ООО, адреса, индексы, города)
- Извлечь страну из description/phone где возможно
- Очистить неочевидные (оставить пустыми, НЕ выдумывать)
- Маппинг телефонных кодов: +7→Россия, +998→Узбекистан, +996→Кыргызстан, +992→Таджикистан, +375→Беларусь, +374→Армения, +994→Азербайджан, +995→Грузия, +380→Украина
- Использовать upsert для batch обновления (быстрее чем по одному)

**Этап 2 — Нормализация телефонов:**
- Найти телефоны без `+` (формат `8 800...`, `374 10...`, `1-800-...`)
- Конвертировать в международный формат: `+7 800 XXX XX XX`, `+374 10 XX XX XX`, `+1 800 XXX XXXX`
- Для номеров с кодами стран (374, 375, 370, 371, 372, 373, 380, 381, 420, 421, 44, 49, 33, 39, 34, 351, 353, 354, 358, 359, 36, 48, 31, 32, 352, 355, 356, 357, 358) — просто добавить `+`
- Для `8 (XXX) XXX-XX-XX` → `+7 (XXX) XXX-XX-XX`
- Для `1-800-XXX-XXXX` → `+1-800-XXX-XXXX`

**Этап 3 — Пометка дубликатов:**
- Найти дубли по name_clean (оставить самую полную запись по score: phone+email+website+country)
- Найти дубли по phone (пометить остальных)
- Найти дубли по email (пометить остальных)
- Пометить `is_duplicate=true`

**Этап 4 — Удаление дубликатов:**
- Загрузить все ID с `is_duplicate=true`
- Удалить батчами по 100 через supabase-py `.delete().in_("id", batch)`
- Пересчитать статистику стран после удаления

**Этап 5 — Очистка name_clean от мусора:**
Проблема: name_clean может содержать полное "название + описание продукта" слитно.
Алгоритм очистки:
```python
def clean_name(name):
    # Убрать # в начале
    name = re.sub(r"^#", "", name)
    # Убрать юрформы после запятой
    name = re.sub(r",?\s*(ООО|ТОО|ЗАО|АО|ИП|PLC|LTD|LLC|GmbH|SA|BV)\b", "", name)
    # Убрать описания в скобках
    name = re.sub(r"\s*\([^)]*\)", "", name)
    # Убрать всё после ";"
    name = re.sub(r";.*$", "", name)
    # Убрать адресные хвосты
    name = re.sub(r",?\s*(г\.|ул\.|пр\.|д\.|офис|кв\.).*", "", name)
    # Убрать хвосты с описанием продукции
    for kw in ["КОНДИТЕРСКИЕ", "МОЛОЧНЫЕ", "ХЛЕБОБУЛОЧНЫЕ", "ЖИРЫ", "МАСЛА",
               "ПОЛУФАБРИКАТЫ", "ДЕТСКОЕ ПИТАНИЕ", "СЫР", "МОРОЖЕНОЕ",
               "ФРУКТЫ", "ОВОЩИ", "ОРЕХИ", "СНЕКИ", "КОНДИТЕРСКАЯ"]:
        name = re.sub(r",?\s*" + kw + r".*", "", name, flags=re.IGNORECASE)
    name = re.sub(r",\s*$", "", name)
    name = name.strip(" ,;.")
    return name
```
- Если после очистки name_clean < 3 символов — оставить оригинал (не портить)
- Использовать upsert для batch обновления

**Этап 6 — Финальная дедупликация по name_clean:**
- После очистки name_clean могут появиться новые дубли (разные варианты одного названия → один чистый)
- Повторить: найти дубли по name_clean, оставить самую полную, остальные удалить
- Финальная проверка: 0 дублей по name, phone, email

### Фильтрация по странам
Пользователь может указать "не наша страна" → удалить все записи этой страны без подтверждения.
Пример: "Беларусь не наш профиль" → `DELETE WHERE country LIKE '%Беларусь%'`.

### Целевые страны (whitelist — СНГ + Россия, без Беларуси)
**АКТУАЛЬНЫЙ WHITELIST (27.06.2026):**
- Россия, Казахстан, Узбекистан, Армения, Азербайджан, Кыргызстан, Грузия, Таджикистан, Туркменистан

**УДАЛИТЬ:**
- Беларусь (и все варианты: "Беларусь", "Belarus", "Республика Беларусь", "РБ")
- Все не-СНГ страны (Европа, Азия, Ближний Восток, Африка, Америка)
- Пустое поле country (NULL или "")

**Подход:** Сканируй clean_clients пагинацией, собирай ID не-СНГ, удаляй батчами по 500.
Для нормализации: страны на английском (Kazakhstan, Uzbekistan...) → маппинг на русский ДО фильтрации.
Для удаления по стране используй `id=in.(filters)` — batch DELETE работает.

**Скрипт:** `~/audit/filter_cities.py` (создаётся на лету в сессии)

**⚠️ Паттерн "страна в названии компании" (27.06.2026):**
Некоторые записи имеют мусор в field country: "Название ООО, Россия", "GBC Foods, Бразилия".
Алгоритм: если country содержит название компании через запятую — проверить, есть ли СНГ-страна в строке.
Если есть → нормализовать к стандартному названию.
Если нет (Бразилия, Италия, Китай) → удалить.

**⚠️ КРИТИЧЕСКИЙ ПИТФОЛЛ: Не удалять пустые страны без восстановления (27.06.2026):**
При очистке базы от не-СНГ и пустых стран, **3 008 СНГ-компаний были удалены зря** потому что поле `country` было пустым, но страна указывалась в `name` или `description` (например, "ALTAY FOOD GIDA QAZAQSTAN," → Казахстан, "ALTUNKAYA INS. NAK. GIDA VE TIE. A.S, TÜRKIYE" → не СНГ).
**Правило:** ПЕРЕД удалением записей с пустой country:
1. Загрузи ВСЕ записи с `country=is.null` И `country=eq.` из raw_parsed_data
2. Попытайся определить страну из `name` + `description` (ключевые слова, телефонные коды, суффиксы)
3. Восстанови СНГ-записи с определённой страной
4. Только потом удаляй оставшиеся пустые/не-СНГ
**Потери в этой сессии:** 19,463 → 7,000 (вместо 8,143) — 1,143 записи потеряны из-за преждевременного удаления.
**Скрипт восстановления:** `references/empty-country-recovery-2026-06-27.md`

### Результат очистки (27.06.2026)
- Грязные страны: 82 → 0
- Некорректные телефоны: 299+22 → 0
- Удалено дубликатов: 594 (is_duplicate) + 356 (name_clean dupes) = 950
- Удалено мусорных записей: 11 (пустое название + нет описания)
- Удалено нецелевых стран: 12,463 (не-СНГ + Беларусь + пустые)
- Итого в базе: **7,000 уникальных записей (СНГ only)**
- 0 дубликатов по phone/name/email
- 0 грязных стран
- 0 некорректных телефонов
- 0 мусора в name_clean

### Экспорт в CSV + отправка в Telegram
```python
# Экспорт через supabase-py — загрузить ВСЕ записи (не только is_duplicate=false)
records = sb.table('clean_clients').select('id,name_clean,country,phone,email,website,description,source').execute().data
with open('/home/khadas/clean_clients_final.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'name_clean', 'country', 'phone', 'email', 'website', 'description', 'source'])
    for rec in records:
        writer.writerow([rec.get(k, '') for k in ['id', 'name_clean', 'country', 'phone', 'email', 'website', 'description', 'source']])
```
```bash
# Отправка через Telegram Bot API (send_message с MEDIA не работает для файлов!)
TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
curl -s --max-time 30 -X POST "https://api.telegram.org/bot${TOKEN}/sendDocument" \
  -F "chat_id=170690883" \
  -F "document=@/home/khadas/clean_clients_final.csv" \
  -F "caption=Чистая база — N записей"
```

**⚠️ Питфолл: CSV из audit без заголовков (26.06.2026)**
Файл `~/.hermes/audit/raw_parsed_data_full.csv` экспортирован БЕЗ строки заголовков.
14 колонок в порядке: `id, name, country, name_clean, description, phone, email, website, extra1, extra2, source, is_duplicate, extra3, created_at`
**Решение:** Добавить заголовок перед запуском пайплайна:
```bash
echo 'id,name,country,name_clean,description,phone,email,website,extra1,extra2,source,is_duplicate,extra3,created_at' | cat - input.csv > input_with_headers.csv
```
Без заголовка `csv.DictReader` не находит `name`/`name_clean` → все записи получают `empty_or_short` → 100% rejection.

**⚠️ Паттерн "пользователь находит ошибку после чистки" (25.06.2026)**
Пользователь многократно находил проблемы после запуска очистки:
1. Страны почистил → остались телефоны
2. Телефоны почистил → остались дубли
3. Дубли пометил → пользователь хочет удалить физически
4. Удалил дубли → мусор в name_clean
5. Почистил name_clean → новые дубли по названию
6. Удалил Беларусь → остались другие нецелевые страны

**Урок:** После каждого этапа — перепроверяй ВСЕ предыдущие этапы. Лучше запустить полный 6-этапный пайплайн целиком чем чистишь по одному и пользователь находит следующий слой.

## USER PREFERENCES — СТИЛЬ РАБОТЫ (25.06.2026)

**Пользователь предпочитает:**
- **Краткость** — без длинных объяснений, только результат
- **Немедленное действие** — "запусти", "чисти", "делай" → действуй без промежуточных подтверждений
- **"Пришли базу проверю"** → скидывай CSV файл сразу, не обсуждай
- **Минимум диалога** — получил задачу → сделал → скинул результат
- Не спрашивай "точно удалить?" когда пользователь уже сказал "чисти" / "удаляй"
- Ожидает финального результата, а не промежуточных отчётов

## ИСПРАВЛЕНИЕ КЛЮЧА SUPABASE (25.06.2026)

**Проблема:** Все скрипты layer4-cleaner использовали `SUPABASE_KEY` как имя переменной для чтения из `.env`, но в `.env` правильный ключ — `SUPABASE_SERVICE_KEY`.

**Решение:** Во ВСЕХ скриптах заменить:
- `os.getenv('SUPABASE_KEY')` → `os.getenv('SUPABASE_SERVICE_KEY')`
- `SUPABASE_KEY = 'sb_secret_...'` (захардкоженный) → `SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')`
- `env.get('SUPABASE_KEY')` → `env.get('SUPABASE_SERVICE_KEY')`

**Статус:** ✅ Исправлено в 13 скриптах (25.06.2026).

## ОТПРАВКА ФАЙЛОВ В TELEGRAM (25.06.2026)

**Проблема:** `send_message` с `MEDIA:` или `target` не отправляет файлы корректно.

**Решение:** Используй прямой curl к Telegram Bot API:
```bash
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendDocument" \
  -F "chat_id=<CHAT_ID>" \
  -F "document=@/path/to/file.csv" \
  -F "caption=Описание файла"
```

**Где взять токен:** `~/.hermes/.env` → `TELEGRAM_BOT_TOKEN`

**Важно:** Файлы >50MB не отправляются. Для больших файлов используй GitHub Releases или SCP.

## ПОЛНЫЙ ПАЙПЛАЙН ОЧИСТКИ БАЗЫ (25.06.2026)

### Когда использовать
Когда пользователь просит "привести базу в порядок", "почистить от ошибок", "проверить и исправить".

### Алгоритм (3 этапа)
1. **Этап 1 — Нормализация стран:**
   - Загрузить все записи через supabase-py
   - Найти записи с мусором в country (ООО, адреса, индексы)
   - Извлечь страну из description/phone где возможно
   - Очистить неочевидные (оставить пустыми, НЕ выдумывать)
   - Скрипт: `/home/khadas/.hermes/agents/parser/scripts/fix_countries.py`

2. **Этап 2 — Нормализация телефонов:**
   - Найти телефоны без `+` (формат `8 800 XXX XX XX`)
   - Конвертировать в `+7 800 XXX XX XX`
   - Скрипт: `/home/khadas/.hermes/agents/parser/scripts/fix_phones.py` (запускается inline)

3. **Этап 3 — Пометка дубликатов:**
   - Найти дубли по name_clean (оставить самую полную запись)
   - Найти дубли по phone (пометить остальные)
   - Найти дубли по email (пометить остальные)
   - Пометить `is_duplicate=true` (НЕ удалять — пользователь проверяет)

### Результат очистки (25.06.2026)
- Грязные страны: 82 → 0
- Некорректные телефоны: 299 → 0
- Помечено дубликатов: 594 (is_duplicate=true)
- Уникальных записей: 7,350

### Экспорт в CSV
```python
# Используй supabase-py client
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
records = sb.table('clean_clients').select('id,name_clean,country,phone,email,website,description,source').eq('is_duplicate', False).execute().data
# Записать в CSV через csv.writer
```

## SUPABASE-PY СИНТАКСИС ФИЛЬТРОВ (25.06.2026)

**Проблема:** `sb.table(...).not_._("phone", None)` — вызывает `AttributeError`.

**Правильный синтаксис:**
```python
# Не NULL и не пустая строка:
sb.table("clean_clients").select("id,phone").neq("phone", "").neq("phone", None).execute().data

# Фильтр по boolean:
sb.table("clean_clients").select("id").eq("is_duplicate", False).execute().data

# Пагинация (range включает обе границы):
sb.table("clean_clients").select("id").range(0, 999).execute().data  # 0-999 = 1000 записей
```

**⚠️ НЕ работает:**
- `.not_._("field", None)` — AttributeError
- `.is_("field", None)` — используй `.eq("field", None)` для NULL
- `.is_("phone", "null")` — AttributeError (28.06.2026)

**Правильный паттерн для фильтрации NULL/empty:**
```python
# НЕПРАВИЛЬНО (падает):
sb.table('clean_clients').select('*').is_('phone', 'null').limit(5000).execute()

# ПРАВИЛЬНО — загрузить все и фильтровать локально:
all_data = sb.table('clean_clients').select('*').execute().data
no_contacts = [r for r in all_data if not r.get('phone') and not r.get('email') and not r.get('website')]
```

## АКТУАЛЬНЫЕ СКРИПТЫ (Layer 4 - Cleaner)

1. **pipeline_v55_final.py** — ⭐ ПАЙПЛАЙН ОЧИСТКИ CSV (26.06.2026)
   - Гибридный фильтр + дедупликация для CSV-файлов
   - Вход: CSV с заголовками (нужны `name` или `name_clean`)
   - Выход: `clean_output.csv` + `rejected.csv` + `metrics.json`
   - Запуск: `python3 pipeline_v55_final.py input.csv output.csv`
   - Опции: `--dry-run` (только метрики), `--db path` (SQLite dedup cache)
   - **⚠️ КРИТИЧНО: CSV ДОЛЖЕН ИМЕТЬ ЗАГОЛОВКИ** — без них ВСЕ записи отвергаются с `empty_or_short`
   - **⚠️ Кэш дедупликации:** удаляйте `dedup_cache.db` перед повторным запуском
   - **⚠️ БАГ double-counting:** `reject_reasons` в metrics.json считает дубли дважды (score + dedup). Используйте `rejected.csv` для точной статистики. Детали: `references/pipeline-v55-double-counting-bug-2026-06-26.md`
   - **⚠️ Колонка `name` НЕ существует в clean_clients** — используйте `name_clean` при загрузке в Supabase
   - Результат 26.06.2026: 76,091 → 23,586 (69.0% rejected, 52% — dedup)
   - **Архитектура (27.06.2026):** модульная — `ExactDedup` из `dedup/exact.py`, `FuzzyDedup` из `dedup/fuzzy.py`. Pipeline = thin orchestrator (366 строк).
   - **Рефакторинг (27.06.2026):** убраны дублирование, неиспользуемые импорты, исправлены regex. Детали: `references/code-review-refactoring-2026-06-27.md`
**Pipeline V5.5 баг:** `references/pipeline-v55-double-counting-bug-2026-06-26.md`
**Code review findings (all layers):** `references/code-review-findings-2026-06-27.md`
**Экспорт из Supabase:** `references/supabase-rest-export-pattern-2026-06-26.md`
**CIS Reimport Pattern:** `references/cis-reimport-pattern-2026-06-26.md`

2. **full_pipeline_all.py** — ⭐ ГЛАВНЫЙ оркестратор (25.06.2026)
   - Полный пайплайн: raw_parsed_data → whitelist-фильтр 10 категорий → дедуп → clean_clients
   - Результат: 72,153 raw → 9,087 clean_clients (целевой B2B профиль)
   - Запуск: python3 ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/full_pipeline_all.py
   - Это скрипт который дал финальный результат 9,087 записей

2. **filter_v5.py** — гибридный фильтр (Rules + Consilium + обучение)
   - Отличает компании от мусора (88.5% точности)
   - Самообучается через PatternCache (learned_patterns.json)
   - Запуск: python3 ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/filter_v5.py input.csv output.csv

3. **normalize_and_dedup.py** — нормализация + дедупликация
   - Удаляет юрформы, страны из названий
   - Дедуплицирует по телефону, сайту, email, нечёткому названию
   - Запуск: python3 ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/normalize_and_dedup.py input.csv output.csv

4. **full_pipeline.py** — предыдущий оркестратор (24.06.2026)
   - Загружает сырые данные → классификация → дедупликация → загрузка в clean_clients
   - Запуск: python3 ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/full_pipeline.py [--include-old] [--enrich]

5. **enrich_serper_mass.py** — ⭐ МАССОВОЕ ОБОГАЩЕНИЕ через Serper API (27.06.2026)
   - Continuous mode: пагинация по всем записям без контактов, batches of 500
   - Очистка названия → Serper search → извлечение phone/email/website → PATCH
   - Hit rate: ~60%, скорость: ~30 записей/мин
   - Запуск: `python3 ~/enrich_serper_mass.py 2>&1 | tee /tmp/serper_mass.log`
   - **Оптимизация:** Запускать только после очистки базы от не-СНГ/мусора
   - Детали: `references/serper-mass-enrichment-pattern-2026-06-27.md`
   - Загружает записи без phone+email → ищет через DaData suggest/party → патчит обратно
   - Работает только для записей с юрлицом в названии (ООО, ТОО, АО, ИП)
   - НЕ работает для общих названий ("Кондитерские изделия")
   - Запуск: `python3 -u ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/enrich_v4.py`
   - Скорость: ~3 записи/сек (DaData ~0.3s + Supabase PATCH ~0.1s)

5. **cleanup.py** — ⭐ ОЧИСТКА дубликатов и мусора (25.06.2026)
   - Загружает ВСЕ записи через supabase-py client (~1s)
   - Находит дубликаты по (name_clean, country) — оставляет первый
   - Удаляет мусорные названия (организаторы, каталоги, выставки)
   - Удаляет URL/email в названии, только цифры/символы
   - Запуск: `python3 -u ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/cleanup.py`
   - Результат: 9,087 → ~7,944 (удалено 1,143 дубликата+мусора)

6. **fix_contacts.py** — ИСПРАВЛЕНИЕ телефонов и email (25.06.2026)
   - Множественные номера через запятую → первый в формате +7 (XXX) XXX-XX-XX
   - Множественные email → первый валидный, убран мусор "internet:"
   - Запуск: `python3 -u ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/fix_contacts.py`

7. **fix_countries.py** — НОРМАЛИЗАЦИЯ стран (25.06.2026)
   - Загружает ВСЕ записи через supabase-py client
   - Находит записи с пустыми или мусорными странами
   - Заполняет ТОЛЬКО по очевидным признакам (телефонный код, ключевые слова)
   - НЕ выдумывает и НЕ ставит по умолчанию
   - Запуск: `python3 -u ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/fix_countries.py`

7. **fix_countries.py** — НОРМАЛИЗАЦИЯ стран (25.06.2026)
   - Загружает ВСЕ записи через supabase-py client
   - Находит записи с пустыми или мусорными странами
   - Заполняет ТОЛЬКО по очевидным признакам (телефонный код, ключевые слова)
   - НЕ выдумывает и НЕ ставит по умолчанию (правило пользователя!)
   - Запуск: `python3 -u ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/fix_countries.py`

8. **audit_full.py** — ПОЛНЫЙ АУДИТ базы (25.06.2026)
   - Проверяет: дубликаты, названия, страны, контакты, источники
   - Использует REST API пагинацию (работает стабильно)
   - Запуск: `python3 -u ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/audit_full.py`
   - Сохраняет отчёт в `/tmp/audit_report.json`
   - ⚠️ НЕ используй `?phone=is.null` в REST API — загружай все и фильтруй локально

5. **mass_upload_json.py** — массовая загрузка JSON в raw_parsed_data
   - Для готовых спарсенных файлов в /home/khadas/.hermes/agents/parser/data/
   - Запуск: python3 ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/mass_upload_json.py --all

### Структура таблицы clean_clients (проверено 24.06.2026)
**Реальные колонки**: `id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`
### Структура таблицы clean_clients (проверено 24.06.2026, подтверждено 26.06.2026)
**Реальные колонки**: `id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`

**⚠️ Питфолл: `name` колонка НЕ существует в clean_clients!**

**НЕ существующие колонки** (не добавлять!): `moysklad_id`, `category`, `name`, `city`, `address`, `products`, `tags`, `group_tag`, `holding`, `confidence`, `data_score`, `needs_review`, `activity_type`, `legal_title`, `legal_address`, `inn`

### Загрузка в Supabase — критические правила (24.06.2026)
1. **НЕ включать `id`** — UUID генерируется автоматически, пустая строка → `22P02`.
2. **`duplicate_of` — UUID**, не принимает `""`. Правило: `if rec.get('duplicate_of'): include`.
3. **PGRST102**: все объекты в батче должны иметь идентичный набор ключей.
4. **`category` НЕ существует** — хранить в `description` как `[категория]`.
5. **Батчи по 50** стабильно работают.
**Pipeline V5.5 баг (double-counting):** `references/pipeline-v55-double-counting-bug-2026-06-26.md`
**Code review findings (all layers):** `references/code-review-findings-2026-06-27.md`
### Целевые категории (keyword-классификация)
**⚠️ Зависит от профиля  products пользователя!** Всегда уточняй у пользователя какие категории его профиль, НЕ предполагай.

**Пример для пищевого сырья (орехи, сухофрукты, заморозка):**
- кондитерка, молочка, хлеб, сухофрукты, детское питание, снеки, заморозка, орехи, масла/жиры, дистрибьюция

**Пример НЕ профиль (удалить):**
- чай/кофе, напитки, алкоголь, крупы, мука, макароны, мясо/рыба, овощи/фрукты, сахар/мёд, специи, корма/агро

**Детали в:** `references/category-filtering-2026-06-24.md` — полный список целевых/нецелевых с обоснованием.
**Финальный результат:** `references/final-pipeline-result-2026-06-25.md` — итог 9,087 записей.
**Питфоллы:** `references/supabase-upload-pitfalls-2026-06-24.md`

**⚠️ Питфолл: Логика фильтрации категорий (24.06.2026)**

**❌ НЕПРАВИЛЬНО:** Удалять по ключевым словам "не пищевое" — слишком широко, удаляет всё.
```python
# НЕ ДЕЛАЙ ТАК:
non_food = ['алкоголь', 'мясо', 'рыба', 'сахар', 'масло', 'специи', 'крупы', 'мука', 'макароны', ...]
if any(kw in combined for kw in non_food):
    delete()  # УДАЛЯЕТ ВСЁ!
```

**✅ ПРАВИЛЬНО:** Оставлять ТОЛЬКО целевые категории (whitelist подход).
```python
TARGET = ['кондитерка', 'молочка', 'хлеб', 'сухофрукты', ...]
cat = get_cat(r.get('description', ''))
if cat not in TARGET:
    delete()
```

**Правило:** Сначала парсим категорию из `description` (формат `[категория] описание`), потом проверяем `cat in TARGET_LIST`. Записи без категории — оставляем (не удаляем слепо).

**⚠️ Background process `tcsetattr` hang (25.06.2026):**
Heredoc + `terminal(background=True)` → `tcsetattr: Inappropriate ioctl for device` → exit 143.
Multiple background processes (proc_3edd8c787d45, proc_9897d442ce61, proc_8cb0d143d5f3, proc_334646ec2eea, proc_0a31d2eff46d) all hung this way.
**Solution:** Write script to file via `write_file` → run in foreground: `python3 -u script.py > /tmp/log 2>&1`
Check output: `cat /tmp/log`

**⚠️ Supabase REST API на VIM4 — производительность (25.06.2026):**

**Проблема:** При последовательных REST запросах (9×1000 для загрузки всех записей) процессы зависают без вывода.

**Решение: supabase-py client** — загружает все 9,087 записей за ~1s!
```bash
pip install supabase
```
```python
from supabase import create_client
sb = create_client(SB_URL, SB_KEY)
data = sb.table('clean_clients').select('id,name_clean,phone,email').execute().data
# Возвращает ВСЕ записи одним вызовом, без пагинации
```

**Для REST API (если client недоступен):**
- Малые батчи по 500-1000 работают стабильно (0.1-0.3s каждый)
- Heredoc + background terminal → `tcsetattr` зависание (exit 143)
- Решение: `write_file` скрипт → `python3 -u script.py > /tmp/log 2>&1`

**⚠️ КРИТИЧНО: supabase-py для аудита и очистки (25.06.2026):**
Для массовых операций (аудит всей базы, удаление дубликатов) **ВСЕГДА** используй supabase-py client. REST API пагинация по 1000 работает, но медленно и зависает. supabase-py загружает все 9,087 записей за 1 вызов.
```python
# Загрузка ВСЕХ записей — 1 вызов, ~1s
sb = create_client(SB_URL, SB_KEY)
all_data = sb.table('clean_clients').select('id,name_clean,phone,email,website').execute().data
# Фильтрация локально:
no_contact = [r for r in all_data if not r.get('phone') and not r.get('email') and not r.get('website')]
```

**⚠️ Supabase REST `in.()` синтаксис для batch DELETE (25.06.2026):**
```python
# ПРАВИЛЬНО — скобки обязательны!
values_str = ','.join(str(v) for v in batch_ids)
r = requests.delete(f"{SB_URL}/rest/v1/table?id=in.({values_str})", headers=headers)

# НЕПРАВИЛЬНО — без скобок даёт 400 или молча не работает
r = requests.delete(f"{SB_URL}/rest/v1/table?id=in.{values_str}", headers=headers)
```

**⚠️ Нормализация стран — ПРАВИЛО ПОЛЬЗОВАТЕЛЯ (25.06.2026):**
"Страну нужно вставлять если она очевидна, где то упоминается, или телефон подходит, но не выдумывать и не ставить по умолчанию."
- МОЖНО: телефонный код (+998→Узбекистан), ключевые слова (Алматы→Казахстан)
- НЕЛЬЗЯ: ставить "Россия"/"Казахстан" по умолчанию, выдумывать из контекста
- Скрипт: `/home/khadas/.hermes/agents/parser/scripts/fix_countries.py`

**⚠️ Background Terminal + Python = tcsetattr hang (28.06.2026):**
`terminal(background=True, command="python3 script.py")` → `tcsetattr: Inappropriate ioctl` → exit 143.
Python tries to access TTY but Hermes background mode has no PTY.
**Workaround:** Use `execute_code` directly for Python with web_search. For standalone scripts,
write to file and run via `terminal(command="python3 script.py")` in FOREGROUND only.

**⚠️ OpenRouter Free Tier Unreliable (28.06.2026):**
All tested free models return 429 (rate-limited) or 404: hermes-3-405b, llama-3.3-70b, gemma-2-27b.
**Don't use OpenRouter free models for batch contact enrichment.** Use `web_search` instead.

**⚠️ DuckDuckGo API/HTML = 0% hit rate for contacts (28.06.2026):**
DuckDuckGo doesn't return phone/email in snippets. Same for Instant Answer API.
**Only `web_search` (Hermes built-in) works for contact enrichment.**

**Resumable Enrichment Pattern (28.06.2026):**
For large batches (>500 records) with `execute_code` timeout (300s):
1. Save progress to `/tmp/enrich_progress.json` after each batch of 20
2. On restart: load progress, filter `processed_ids`, continue
3. Pattern details: `references/contact-enrichment-resumable-pattern-2026-06-28.md`

**⚠️ Supabase REST `is.null` не работает через query string (25.06.2026):**
- `?phone=is.null` in URL query → 400 Bad Request
- `?phone=not.is.null` → работает но медленно на больших таблицах
- **Решение:** Загружай все записи без фильтра и фильтруй локально в Python (через supabase-py client)

**⚠️ Supabase REST `safe_get()` pattern (25.06.2026):**
Поля в Supabase могут быть `None` (NULL), а не пустой строкой `""`. Всегда используй:
```python
def safe_get(rec, field, default=''):
    v = rec.get(field)
    return v if v is not None else default
```
Или: `phone = (r.get('phone') or '').strip()`
Без этого — `AttributeError: 'NoneType' object has no attribute 'strip'`

**⚠️ Supabase REST `is.null` не работает через query string (25.06.2026):**
- `?phone=is.null` в URL query → 400 Bad Request
- `?phone=not.is.null` → работает но медленно на больших таблицах
- **Решение:** Загружай все записи без фильтра и фильтруй локально в Python:
```python
# Через supabase-py client (рекомендуется):
all_data = sb.table('clean_clients').select('id,name_clean,phone').execute().data
no_phone = [r for r in all_data if not r.get('phone')]
```
- Пагинация по 1000 записей — единственный рабочий способ для REST API
- `count=exact` возвращает N/A для пустых результатов — проверяй перед `int()`

### Обогащение контактов — итоги (28.06.2026)

**Последнее состояние (28.06.2026): clean_clients = 2,247 записей (новая база с нуля)**
- С любым контактом: ~50 (2.2%) — обогащение в процессе
- Без контактов: ~2,197 (97.8%)
- Метод: web_search через execute_code, батчи по 25
- Прогресс: `/tmp/enrich_progress_final.json`
- Hit rate: 30-65% (в среднем ~40%)
- ETA: ~5 часов для полного обогащения
- **Полный паттерн:** `references/contact-enrichment-resumable-pattern-2026-06-28.md`

### ⚠️ ЧТО НЕ РАБОТАЕТ (проверено 28.06.2026)

| Метод | Hit rate | Проблема |
|-------|----------|----------|
| **enrich_contacts.py (Groq LLM)** | 0% для телефонов | LLM выдумывает номера. Плюс `.is_('phone','null')` падает с AttributeError |
| **DuckDuckGo API/HTML** | ~0% | API не подходит для поиска контактов компаний |
| **OpenRouter free models** | 0% (429) | Все бесплатные модели rate-limited (hermes-3-405b, llama-3.3-70b, gemma-2-27b) |
| **Groq/Mistral LLM прямой запрос** | ~5% | Модель не может найти реальный телефон по названию |

### ✅ Что работает

| Метод | Hit rate | Скорость | Стоимость |
|-------|----------|----------|-----------|
| **web_search** (встроенный в Hermes) | **60-67%** | ~25 записей/3мин | бесплатно |
| **Serper API** | ~60% | ~30 записей/мин | 100 запросов/день |

### Правильный паттерн обогащения через web_search (28.06.2026)

**ВАЖНО**: web_search доступен ТОЛЬКО через `execute_code`, не standalone!
**Таймаут execute_code = 300с** → макс ~25 записей за запуск!

```python
# В execute_code:
from hermes_tools import web_search

for record in batch:
    name = re.sub(r'[,.]?\\s*(ООО|ТОО|...)\\s*$', '', record['name_clean'], flags=re.I)
    query = f\"{name} {record['country']} телефон email сайт\"
    result = web_search(query, limit=3)
    
    # Извлечь контакты из title + description + snippet
    all_text = ' '.join([item.get('title','') + ' ' + item.get('description','') + ' ' + item.get('snippet','') 
                        for item in result['data']['web'][:3]])
    
    phones = re.findall(r'[\\+]?[78][\\s\\-]?[\\(]?\\d{3}[\\)]?[\\s\\-]?\\d{3}[\\s\\-]?\\d{2}[\\s\\-]?\\d{2}', all_text)
    emails = re.findall(r'[\\w.+-]+@[\\w.-]+\\.\\w{2,}', all_text)
    websites = [w for w in re.findall(r'https?://[^\\s<>\"\\)\\]]+', all_text)
                if not any(b in w.lower() for b in ['youtube','facebook','vk.com','2gis','yandex'])]
    
    sb_patch(record['id'], {'phone': phones[0] if phones else '', 'email': emails[0] if emails else '', 'website': websites[0] if websites else ''})
```

**Прогресс сохраняй в файл** для возобновления. Паттерн: `references/contact-enrichment-resumable-pattern-2026-06-28.md`

### ⚠️ ЧТО НЕ РАБОТАЕТ (проверено 28.06.2026)

| Метод | Hit rate | Проблема |
|-------|----------|----------|
| **enrich_contacts.py (Groq LLM)** | 0% для телефонов | LLM выдумывает номера. Плюс `.is_('phone','null')` падает с AttributeError |
| **DuckDuckGo API/HTML** | ~0% | API не подходит для поиска контактов компаний |
| **OpenRouter free models** | 0% (429) | Все бесплатные модели rate-limited (hermes-3-405b, llama-3.3-70b, gemma-2-27b) |
| **Groq/Mistral LLM прямой запрос** | ~5% | Модель не может найти реальный телефон по названию |

### ✅ Что работает

| Метод | Hit rate | Скорость | Стоимость |
|-------|----------|----------|-----------|
| **web_search** (встроенный в Hermes) | **60-67%** | ~25 записей/3мин | бесплатно |
| **Serper API** | ~60% | ~30 записей/мин | 100 запросов/день |

**Полный паттерн обогащения с прогресс-файлом:** `references/contact-enrichment-resumable-pattern-2026-06-28.md`

### Правильный паттерн обогащения через web_search (28.06.2026)

**ВАЖНО**: web_search доступен ТОЛЬКО через `execute_code`, не standalone!
**Таймаут execute_code = 300с** → макс ~25 записей за запуск!

Полный код с прогресс-файлом, восстановлением и расчётом ETA: `references/contact-enrichment-resumable-pattern-2026-06-28.md`

**Ключевые метрики:**
- 25 записей за 200с = 75 записей/час
- 2247 записей / 75 = ~30 часов
- Hit rate: 30-65% (в среднем ~40%)
- Ожидаемый результат: ~900 обогащённых записей

**Распределение по странам:**
- Узбекистан: 1,832 | Казахстан: 1,050 | Армения: 706 | Беларусь: 565
- Азербайджан: 157 | Кыргызстан: 138 | Грузия: 94 | Туркменистан: 64
- Таджикистан: 47 | Россия (НЕ целевая для ВЭД): 9,522

### Полный аудит базы (25.06.2026)

**Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/audit_full.py` — проверяет:
1. Дубликаты (name_clean + country) и по телефону
2. Качество названий (пустые, мусорные, URL в названии)
3. Страны (распределение, пустые, подозрительные)
4. Качество контактов (формат phone/email, покрытие)
5. Источники данных

**Результат аудита 25.06.2026 (9,087 записей):**
- Дубликатов (name+country): **1,125 (12.4%)** — нужно удалять
- Без контактов: **6,933 (76.3%)** — ЭТО ОШИБКА ПРОВЕРКИ (использовала `phone=is.null` в REST API который не работает)
- Реальное покрытие контактами: **99.8%** (проверено через supabase-py client)
- Мусорных названий: 18
- Пустых стран: 34
- Некорректных телефонов: 13
- Некорректных email: 10

**⚠️ Питфолл аудита:** НЕ используй `?phone=is.null` в Supabase REST API для аудита — он работает некорректно. Загружай ВСЕ данные через supabase-py client и проверяй локально:
```python
from supabase import create_client
sb = create_client(SB_URL, SB_KEY)
all_data = sb.table('clean_clients').select('id,name_clean,phone,email,website').execute().data
no_contact = [r for r in all_data if not r.get('phone') and not r.get('email') and not r.get('website')]
```

**Запуск аудита:** `python3 -u ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parser/scripts/audit_full.py`

**Что делает audit_full.py:**
- Загружает все 9,087 записей через REST API (пагинация по 1000)
- Находит дубликаты по (name_clean, country) и по phone
- Проверяет качество названий (мусорные паттерны, URL в названии)
- Анализирует распределение по странам и источникам
- Проверяет формат phone/email
- Сохраняет отчёт в `/tmp/audit_report.json`

**Паттерн загрузки:**
```python
all_records = []
offset = 0
while True:
    params = {'select': 'id,name_clean', 'phone': 'is.null', 'email': 'is.null', 'limit': '500', 'offset': str(offset)}
    batch = sb_get('clean_clients', params)
    if not batch: break
    all_records.extend(batch)
    offset += len(batch)
    if len(batch) < 500: break
```

**Паттерн обогащения:**
```python
for i, row in enumerate(all_records):
    result = search_api(name)
    if result:
        sb_patch('clean_clients', result, 'id', row['id'])
    if (i+1) % 100 == 0:
        print(f"[{i+1}/{len(all_records)}] enriched={enriched}", flush=True)
    time.sleep(0.05)  # минимум, DaData бесплатный
```

### Фильтрация по категориям в description (24.06.2026)

Категории хранятся в `description` как `[категория] описание`. Для фильтрации:

1. Загрузи все записи (только `id, description`) — пагинация по 1000
2. Парсинг категории: `desc.startswith('[')` → `desc[1:desc.find(']')]`
3. Фильтруй по списку целевых категорий
4. Удаляй нецелевые батчами по 30 ID через `DELETE ?id=eq.{id}`

**Скрипт-паттерн:**
```python
def get_cat(desc):
    desc = (desc or '').lower()
    if desc.startswith('['):
        end = desc.find(']')
        if end > 0:
            return desc[1:end].strip()
    return ''

TARGET = ['кондитерка', 'молочка', 'хлеб', ...]
to_delete = [r['id'] for r in all_data if get_cat(r.get('description','')) not in TARGET]
```

**Питфолл:** НЕ используй heredoc (`python3 << 'EOF'`) для длинных скриптов — Supabase блокирует. Запиши в файл через `write_file`, потом `python3 /tmp/script.py`.

**Питфолл:** `Content-Range: */*` когда нет записей — нельзя `int()` конвертировать. Проверяй перед парсингом.

### Паттерны мусора для фильтрации
```python
RE_TRASH = re.compile(
    r'организатор|organi[sz]ed by|не является публичной оферт|all rights reserved|'
    r'скачайте|download app|официальный каталог|official catalog|'
    r'список фирм|список участников|торгово-промышленн|реклама|advertisement|'
    r'международная выставка|выставочн|expocentr|павильон|'
    r'открытое акционерное общество|закрытое акционерное общество', re.I)
```

### Нормализация name_clean (25.06.2026)

### Проблема
В name_clean может быть "название + описание продукта" слитно (артефакт парсинга PDF-каталогов).

### Решение
Полный алгоритм очистки в `references/name-clean-normalization-2026-06-25.md` — regex-паттерны для удаления юрформ, адресов, описаний продукции.

### Ключевые паттерны
- Удаление после запятой: ООО, ТОО, ЗАО, АО, ИП, LLC, LTD, GmbH
- Удаление после запятой: описания продукции (КОНДИТЕРСКИЕ, МОЛОЧНЫЕ, ХЛЕБОБУЛОЧНЫЕ...)
- Удаление после ";" (описание продукта)
- Удаление адресных хвостов (г., ул., д., обл., край)
- Если после очистки < 3 символов — оставить оригинал

### Дедупликация
- Ключ: `(normalize(name), country)` — компании с одинаковым названием из РАЗНЫХ стран = РАЗНЫЕ компании
- Порядок: сначала нормализация → потом дедупликация
- Fuzzy matching (rapidfuzz) для нечётких совпадений (порог 85%)

## АУДИТ 25.06.2026 (после очистки дубликатов)

**Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/audit_and_fix.py` — полный аудит + автофикс.

**Результат (7,944 записей):**
- ✅ Пустых названий: 0
- ✅ Пустых стран: 0
- ✅ Некорректных email: 0
- ✅ Помеченных как дубли: 0
- ⚠️ Грязные страны: **82** (адреса, ООО, индексы в поле country)
- ⚠️ Некорректные телефоны: **299** (формат `8 800 XXX XX XX` без `+`)
- ⚠️ Дубли по названию: **182 названий** (некоторые ×3)
- ⚠️ Дубли по телефону: **108 номеров**
- ⚠️ Дубли по email: **115 адресов**
- ⚠️ Без контактов вообще: **6,751 (85%)**

**Распределение по странам:** Казахстан 75.8%, Россия 15.9%, Узбекистан 3.8%, Беларусь 1.1%, остальные 3.4%.

**Источники:** opensanctions_kz (5,994), prodexpo (разные годы, ~1,400), foodsuppliers (222), остальные (~300).

**Что нужно сделать:**
1. Нормализовать 82 грязных страны (извлечь страну из адреса/ООО или очистить)
2. Конвертировать 299 телефонов `8 800...` → `+7 800...`
3. Пометить дубликаты по phone/email (is_duplicate=true)

### Итоги очистки 27.06.2026 — АКТУАЛЬНОЕ СОСТОЯНИЕ

### clean_clients = 8,143 записей (СНГ only, без Беларуси)
- **Источник**: 19,463 → удалены не-СНГ (960), Беларусь (571), пустые страны (4,632 после восстановления), мусор (250) → восстановлено +2,538 СНГ из пустых
- **Метод**: strict whitelist — оставить ТОЛЬКО ровно 9 стран СНГ → восстановить страны из name/description → удаление оставшихся не-СНГ/пустых
- **Скрипт**: inline Python через execute_code (пагинация 2000, batch DELETE 500)

### Распределение:
- Россия: 6,283 | Казахстан: 958 | Узбекистан: 634 | Армения: 260
- Кыргыстан: 110 | Азербайджан: 86 | Грузия: 77 | Туркменистан: 46 | Таджикистан: 25

### Контакты:
- С телефоном: 3,979 | с email: 2,051 | с сайтом: 3,864
- Без контактов: ~10,904 → цель для Serper enrichment (запущено 27.06.2026)

### Ключевые решения в этой сессии:
1. **Россия остаётся** — пользователь подтвердил что Россия целевая
2. **Беларусь удаляем** — пользователь исключил из whitelist
3. **Не-СНГ удаляем** — строго СНГ
4. **Serper масс-обогащение** — запущено в фоне на 10,904 записях
5. **Очистка ДО обогащения** — экономия ресурса Serper на 12K+ ненужных записей
6. **Восстановление пустых стран** — 2,538 СНГ-компаний восстановлены из name/description до удаления

**Детали:** `references/empty-country-recovery-2026-06-27.md`

**Детали:** `references/cis-whitelist-cleanup-2026-06-27.md`, `references/serper-mass-enrichment-pattern-2026-06-27.md`

### Полная пересборка базы с нуля (28.06.2026)

Когда пользователь говорит "начинаем с нуля", "очисти всё и заново":
1. `DELETE ?id=gt.0` для raw_parsed_data и clean_clients
2. Очить source_profiles по ID
3. Запустить полный цикл: scout → parse → pipeline → enrich
4. Детали: `references/full-base-rebuild-2026-06-28.md`

### Ключевые паттерны
1. **Нормализация стран ДО фильтрации** — иначе СНГ-страны на английском удаляются (~2000+ потерь)
2. **REST API limit 1000 записей** на VIM4 — пагинация 500-1000 обязательна
3. **web_search для обогащения** — 60-67% hit rate, лучший метод
4. **DaData 0% для не-юрлиц** — только ООО/ТОО/АО/ИП
5. **Playwright** работает для produkt.by, factories.kz; блокируется flagma
6. **CSV без заголовков** — 100% rejection в pipeline_v55

### Восстановление после случайного удаления стран
1. Экспорт из raw_parsed_data по всем вариантам названий (EN + RU)
2. Мерж с parsed_*.json
3. Нормализация стран → фильтрация → дедуп → загрузка
Детали: `references/cis-reimport-pattern-2026-06-26.md`
- **Текущее состояние:** 23,586 records
- **Источник:** 76,091 записей (72,153 Supabase + 3,938 audit) → whitelist-фильтр → 23,586 (31.0% acceptance)
- **Экспорт:** `/home/khadas/clean_all.csv` (5.9 MB)

## 🔴 КРИТИЧЕСКОЕ ПРАВИЛО: Country при загрузке (30.06.2026)

**Все скрипты загрузки (foodmarkets_to_clean.py, load_*.py и т.д.) ОБЯЗАНЫ присваивать country при INSERT.**

Reality: 87% clean_clients (3,766 записей) имеют country=None после загрузки FoodMarkets. Это означает:
- Парсер/аплоадер НЕ извлекал страну из данных
- Pipeline V5.5 — это НЕ gatekeeper для country. Он фильтрует/очищает, но страна должна быть уже при upload
- `enrich/countries.py` в pipeline — fallback для edge cases, не основной механизм

**Обязательный чек-лист для любого upload-скрипта:**
1. Если источник привязан к стране (например "Астана", Казахстан") → country="Казахстан"
2. Если в name есть суффикс страны (", Казахстан", "г. Алматы") → извлечь и сохранить в country, очистить из name
3. Если нет информации → country=НОЛЬ не допустим! Используй detect_cis(name+description) как fallback
4. **После bulk upload ВСЕГДА проверяй распределение стран** (see reference)

См. `references/country-assignment-regression-2026-06-30.md`

### Cleanup & Normalization Workflow (30.06.2026)
Полный цикл после bulk-load: нормализация стран → удаление нецелевых → обогащение контактов → повторная очистка.
`references/cleanup-and-normalization-workflow-2026-06-30.md`

## Pipeline V5.5 — последний запуск (30.06.2026)

### Первый проход
- Вход: **51,391** записей
- Выход: **20,296** (39.5% acceptance)
- Отвергнуто: **31,095** (60.5%)
  - fuzzy_dedup: 20,756
  - exact_dedup: 6,796
  - high_score: 13,000+
  - grey_zone: 11,856 (23.1%)

### Пост-обработка (cleanup-and-normalization-workflow)
- Нормализовано стран: **1,251** (Russia→Россия, Turkey→Турция...)
- Удалено нецелевых: **8,245** (Сербия, Uganda, USA, Maldives, Венгрия...)
- Детектировано из текста: **1,213** (CIS keyword detection)
- **Итого в clean_clients: 16,142**

### Топ стран после очистки
| Страна | Записей |
|--------|---------|
| Россия | 10,243 |
| Китай | 3,191 |
| Турция | 918 |
| Индия | 309 |
| Казахстан | 251 |
| Армения | 166 |
| Узбекистан | 125 |
| Азербайджан | 87 |
| Грузия | 62 |
| Туркменистан | 58 |
| прочие | ~733 |

### Покрытие (требует обогащения)
- phone: 20.6% (3,318)
- email: 7.9% (1,269)
- website: 6.8% (1,095)
- **Нуждаются в обогащении: ~12,824**
- Серая зона: 16,993 (22.3%)
- Скорость: 6,754 записей/сек, 11.3 сек
- Загрузка в Supabase: 74 сек (REST API, batches of 100)

**⚠️ Питфолл: Pipeline V5.5 double-counts reject_reasons (26.06.2026)**
В `metrics.json` поле `reject_reasons` содержит **задвоенные** счётчики: если запись прошла скоринг (high_score:45), но отклонена fuzzy_dedup, она считается И в `high_score:45`, И в `fuzzy_dedup`.
**Решение:** Для реальной статистики смотрите на `rejected.csv`, не на `reject_reasons` в metrics.json.

**⚠️ КРИТИЧЕСКИЙ ПИТФОЛЛ: Удаление СНГ-стран по ошибке (26.06.2026)**
При массовой фильтрации стран скрипт загрузил только первые 1000 записей для анализа стран. СНГ-страны на английском (Kazakhstan, Uzbekistan, Belarus и т.д.) не попали в выборку → не были в `KEEP_COUNTRIES` → были удалены как "non-CIS".
**Потеря:** ~2000+ записей СНГ удалены за 1 запуск.
**Правило:** Перед удалением по фильтру стран:
1. Загружайте ВСЕ записи (не выборку!)
2. Нормализуйте страны ПЕРЕД фильтрацией (PATCH английские названия на русские)
3. Используйте полный маппинг: `{'Kazakhstan':'Казахстан', 'Uzbekistan':'Узбекистан', 'Belarus':'Беларусь', ...}`
4. Проверяйте количество удаляемых записей перед удалением
**Решение:** Перезаливка из raw_parsed_data + parsed JSON → 2156 СНГ-компаний восстановлено.

**⚠️ DaData обогащение — 0% для не-юрлиц (26.06.2026)**
DaData `suggest/party` работает ТОЛЬКО для конкретных юрлиц (ООО, ТОО, АО, ИП). Для общих названий ("Кондитерские изделия", "Молочная продукция") возвращает 0 результатов.
**Симптом:** Скрипт обогащения отработал 14K записей, enriched=0.
**Решение:** Для не-юрлиц используйте **Serper API** (60% hit rate) или web_search + извлечение контактов с сайтов, или примите что это категории, не компании.

### Playwright парсинг JS-каталогов СНГ (26.06.2026)

Для сайтов с JS-рендером (каталоги производителей) используется Playwright headless Chromium.

**Работающие сайты:**
- `produkt.by` (Беларусь) — +159 новых компаний
- `factories.kz` (Казахстан) — +312 компаний
- `tmtrade_tj` (Таджикистан) — 81 компания загружена

**Заблокированные/неработающие:**
- `flagma.kz`, `flagma.uz` — блокируют headless browsers
- `n4.biz` — проблемы с навигацией/селекторами
- `krb.by` — DNS не резолвится на VIM4
- `osoo.kg` — JS-рендер, требует кастомных селекторов
- `georgiayp.com` — проблемы с селекторами

**Паттерн Playwright парсинга:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto(url, wait_until='networkidle', timeout=20000)
    time.sleep(2)
    # Scroll for lazy loading
    for _ in range(3):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
    # Extract from rendered HTML
    companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
```

**⚠️ Supabase REST API limit на VIM4 (26.06.2026)**
На текущей конфигурации VIM4 (8GB RAM) Supabase REST API возвращает максимум ~1000 записей при одном запросе, независимо от `limit`.
**Правило:** Всегда используйте пагинацию по 500-1000. Большие limit (>2000) молча обрезают данные или таймаутируют.

### Предыдущие итоги (25.06.2026)
- clean_clients: 7,350 уникальных (594 is_duplicate) → экспортировано, дубли удалены → 6,927
**Детали в:** `references/cis-reimport-pattern-2026-06-26.md`

### ⚠️ КРИТИЧЕСКИЙ ПИТФОЛЛ: Фильтрация стран — риск потери данных (26.06.2026)

**Проблема:** При фильтрации записей через REST API с `limit=500` и последующем удалении по `KEEP_COUNTRIES`, часть данных была случайно удалена из-за неполной выборки.

**Правила:**
1. **НЕ удалять** записи из базы без явного подтверждения пользователя
2. Перед массовым удалением — показать статистику что будет удалено
3. Использовать whitelist-подход: удалять всё что НЕ в списке разрешённых
4. При фильтрации через REST API — учитывать что `limit < total` даёт неполную картину
5. **СНГ-страны на английском (Kazakhstan, Belarus, Uzbekistan) — нормализовать в русский ДО фильтрации!**
6. **Перед DELETE — сначала PATCH нормализацию стран, потом фильтруй**

**Восстановление после случайного удаления:**
1. В `raw_parsed_data` хранятся ВСЕ сырые данные (никогда не удаляются)
2. Запустить `pipeline_v55_final.py` нафильтрованных стран
3. Выгрузить результат → очистить → dedup → загрузить в clean_clients
4. **Шаблон:** `references/cis-reimport-pattern-2026-06-26.md`

**⚠️ Supabase REST API timeout при 24K+ записях (26.06.2026):**

**Проблема:** REST API возвращает максимум ~15K-36K записей при одном `select(*)` запросе, независимо от limit/offset. На VIM4 (8GB RAM) запросы на 24K+ таймаутят.

**Решение:** Пагинация по 500 с retry и обработкой пустых батчей:
```python
all_data = []
offset = 0
limit = 500
fail_count = 0
while fail_count < 3:
    try:
        r = sb.table('raw_parsed_data').select('*').range(offset, offset+limit-1).execute()
        if not r.data:
            break
        all_data.extend(r.data)
        offset += limit
        fail_count = 0
    except Exception as e:
        fail_count += 1
        time.sleep(2)
```

Для загрузки в Supabase (INSERT): REST API батчи по 100 работают стабильно (318 rec/s).
НЕ используйте `on_conflict` с REST API — возвращает 400 если конфликт не настроен.
**⚠️ Supabase SDK timeout:** `sb.table(...).select('*').execute()` без limit таймаутил на 72K записях. Используйте `.range(start, end)` для пагинации.

**Для загрузки в Supabase (INSERT):**
- REST API батчи по 100 работают стабильно (318 rec/s)
- НЕ используйте `on_conflict` с REST API — возвращает 400 если конфликт не настроен
- Для очистки таблицы: `DELETE ?id=gt.0` (удаляет все)

## Итоги очистки 22.06.2026 (filter_categories.py) — АРХИВ

### clean_clients = 9,087 записей (целевой B2B профиль)
- **Источник**: raw_parsed_data (72,153 записей)
- **Метод**: whitelist фильтр по 10 категориям + дедупликация
- **Скрипт**: `/home/khadas/.hermes/agents/parser/scripts/full_pipeline_all.py`
- **Потери**: 87.4% отброшено (мусор + нецелевые + дубли)

### Распределение ожидаемое (по категориям):
Кондитерка, Молочка, Хлеб, Детское питание, Дистрибьюция, Масла/жиры, Заморозка, Снеки, Орехи, Сухофрукты

### Текущее состояние Supabase:
- `clean_clients`: 9,087 records
- `raw_parsed_data`: 72,153 records
- `raw_parsed_data_old`: 508,750 records (архив)

## Итоги очистки 22.06.2026 (filter_categories.py) — АРХИВ
- **Было:** 14,518 записей (после filter.py)
- **Стало:** 1,668 целевых записей
- **Удалено:** 12,850 (нецелевые категории + неклассифицированные)
- **Переклассифицировано из "прочее":** 198 (молочка:133, хлеб:25, заморозка:21, мука:15, кондитерка:4)
- **Ошибок:** 0
- **Время:** ~30 минут (12,850 DELETE + 198 PATCH)

### Telegram отправка файлов (22.06.2026)
- PDF >20MB таймаутится при отправке через Telegram bot API
- Архивация (zip) помогает но не решает полностью (prodexpo_2023.zip = 46MB)
- **Решения:** SCP/SFTP с VIM4, HTTP-сервер (python3 -m http.server 8080), файлообменники
- Успешно отправлены: worldfood_2023_guide.pdf (419KB), worldfood_2023_postshow.pdf (1.1MB), worldfood_2025.pdf (9.6MB), prodexpo_2025.pdf (18MB)
- Не удалось: worldfood_2024.pdf (23MB), prodexpo_2022-2026.pdf (19-26MB), prodexpo_2023.pdf (92MB)

### OpenSanctions KZ — загрузка в raw_parsed_data (22.06.2026)
- **Файл:** entities.ftm.json, 1.67GB, JSONL формат
- **Структура:** только `name`, `country` (kz), `status`, `incorporationDate` — НЕТ okved, phone, email, address
- **Всего строк:** 340,920; Company: 8,023; Загружено: 61,300+ (все Company записи)
- **Вывод:** данные бесполезные для обогащения контактов, но полезны как список компаний
- **Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/load_opensanctions_kz.py` (или `load_kz_v2.py` в /tmp)

### Telegram отправка больших файлов (22.06.2026)
- PDF >20MB таймаутится при отправке через Telegram bot API
- Архивация (zip) помогает но не решает проблему полностью
- **Решение:** использовать GitHub Releases или SCP/SFTP для больших файлов
- prodexpo_2023.pdf = 92MB → zip = 46MB (всё равно много)

### file.io заблокирован (22.06.2026)
- file.io защищён Cloudflare — API запросы через curl блокируются (возвращает HTML вместо JSON)
- Работает только через браузер с JavaScript
- **Решение:** использовать GitHub Releases через `gh release upload --clobber`

### GitHub Releases для файлообмена (22.06.2026)
- Создание: `gh release create <tag> --repo <owner>/<repo>`
- Загрузка: `gh release upload <tag> <file> --repo <owner>/<repo> --clobber`
- Лимит 2GB на файл, нет лимита на репозиторий
- Прямые ссылки: `https://github.com/<owner>/<repo>/releases/download/<tag>/<filename>`
- Репозиторий SalesBot-PDF-catalogs: `Fireglow1980/SalesBot-PDF-catalogs`, release `pdf-catalogs-v1`

### Экспорт полных таблиц (обновлено 30.06.2026)
- **clean_clients**: 20,065 записей, PK = `id` (auto UUID), НЕТ `moysklad_id`
- **raw_parsed_data**: 51,391 записей, PK = `id`
- Используй urllib с пагинацией по 1000
- Порядок: `.order('id')` для обеих таблиц
- Скрипт: `/home/khadas/.hermes/agents/parser/scripts/export_full3.py`
- CSV кодировка: `utf-8`, разделитель: `,`

### Supabase URL (22.06.2026)
- **Правильный URL:** `https://zimojaemhuapieeaxetd.supabase.co`
- **Неправильный URL (из старых скриптов):** `https://aionilfmyfwzsdlqvrij.supabase.co` — NXDOMAIN, не использовать!
- Ключи в `~/.hermes/.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`
- clean_clients требует service key для чтения (RLS может блокировать anon key)

### CSV экспорт (22.06.2026)
```python
# Используй subprocess для curl — работает стабильнее чем urllib для экспорта
import subprocess, json
result = subprocess.run([
    'curl', '-s', 
    f'{SUPABASE_URL}/rest/v1/clean_clients?select=*&limit=1000&offset={offset}',
    '-H', f'apikey: {SERVICE_KEY}',
    '-H', f'Authorization: Bearer {SERVICE_KEY}'
], capture_output=True, text=True)
data = json.loads(result.stdout)
```
- Или используй urllib с пагинацией по 1000
- Кодировка: `utf-8-sig` для корректного открытия в Excel
- Разделитель: `;` (точка с запятой) для русского Excel
- Размер: 1,668 записей ≈ 0.52 MB

**Удаление мусора перед Mistral** — предварительная фильтрация по паттернам экономит ~20% API вызовов. Паттерны: стенды (1МК, 33-я), каталоги, адреса, не-СНГ страны в названии. Детали в `references/enrichment-patterns-2026-06-22.md`.

**Паттерны обогащения** — все regex-паттерны мусора, шаблоны промптов, параметры Mistral, типичные ошибки в `references/enrichment-patterns-2026-06-22.md`.

**CSV экспорт** — для экспорта используй curl + subprocess. Поле `score` НЕ существует в clean_clients.

## ПОЛНЫЙ ПАЙПЛАЙН ОЧИСТКИ: PDF → clean_clients (24.06.2026)

### Когда использовать
Когда нужно обработать PDF-каталоги выставок от начала до конца: PDF → парсинг → очистка → обогащение → загрузка в clean_clients.

### Алгоритм
1. **parse_pdf.py** — извлечение компаний из PDF (PyMuPDF)
2. **filter_v5.py** — фильтрация мусора (стенды, организаторы, заголовки)
3. **normalize_and_dedup.py** — нормализация названий + дедупликация
4. **Загрузка в raw_parsed_data** — батчи по 50, с retry
5. **Полная очистка** — классификация по ключевым словам + дедупликация → clean_clients
6. **Обогащение контактов** — Cloudflare AI для записей без phone/email

### Типичные результаты
- PDF 19MB (676 стр) → 1,762 компании → 1,580 (89%) → 1,521 уникальных
- 514K сырых → 28K классифицированных → 24K уникальных (96% отброшено)

### Скрипты
- `/home/khadas/.hermes/agents/parser/scripts/parse_pdf.py` — парсинг PDF
- `/home/khadas/.hermes/agents/parser/scripts/filter_v5.py` — фильтрация
- `/home/khadas/.hermes/agents/parser/scripts/normalize_and_dedup.py` — нормализация + дедуп
- `~/audit/clean_step1.py` — полная очистка raw_parsed_data → clean_clients
- `~/audit/enrich_cf.py` — обогащение через Cloudflare AI

## ПРАВИЛО БЭКАП + ТЕСТ КАЖДОГО ИЗМЕНЕНИЯ (27.06.2026)

Пользователь явно указал: **"Перед изменениями делай бэкапы, и проверяй на практике свои изменения"**.

**Workflow (обязательно):**
1. Перед первым изменением: `mkdir -p ~/.hermes/backups/<project>-original && cp <файлы> ~/.hermes/backups/<project>-original/`
2. Внести ОДНО изменение
3. Протестировать: `python3 pipeline_v55_final.py <test.csv> --dry-run` → сравнить с baseline
4. Только после подтверждения идентичности → следующее изменение
5. При регрессии: `cp ~/.hermes/backups/<project>-original/<файл> <файл>` → откатить

**Бэкап текущего состояния:** `~/.hermes/backups/layer4-original/`

## REFACTORING PATTERN: IMPORT FROM SUBMODULES (27.06.2026)

**Problem:** `pipeline_v55_final.py` (487 lines) duplicated `ExactDedup` and `FuzzyDedup` classes that already existed in `dedup/exact.py` and `dedup/fuzzy.py`. Same for regex/keywords duplicated between pipeline and `cleaner/scorer.py`.

**Solution applied:**
- Removed inline `ExactDedup` class (66 lines) → `from dedup.exact import ExactDedup`
- Removed inline `FuzzyDedup` class (57 lines) → `from dedup.fuzzy import FuzzyDedup`
- Removed unused `hashlib` import
- Fixed `RE_COUNTRY_SUFFIX` regex: removed duplicate `\s` in char class
- Fixed `RE_ADDRESS` regex: added lookahead `(?=\s|$|[^\w\s])` instead of greedy `+`
- Simplified `if email and email != ""` → `if email` in exact.py

**Result:** 487 → 366 lines (-25%), zero regression on test data.

**Key principle:** Pipeline = thin orchestrator. All logic lives in `dedup/`, `cleaner/` submodules. Pipeline imports, doesn't duplicate.

## CONSILIUM BUG: consilium_ask returns dict not string (27.06.2026)

**Bug:** `providers.py` line 349: `if result and result.strip()` — assumes `best` is always str, but when models return structured data, `best` can be a dict.

**Fix needed:** Check `isinstance(result, str)` before calling `.strip()`, or use `str(result)`.

**Workaround:** Use `ask_model()` directly for single-model calls, or handle the dict case.

**Current model availability (27.06.2026):**
- `mistral/mistral-large-latest` — ✅ Works (but may return `{}` on rate limit)
- `groq/llama-3.3-70b-versatile` — ⚠️ Circuit breaker triggers after 10 errors
- `openrouter/*` — ❌ No credits (402)
- `cloudflare/*` — ⚠️ Often returns empty/no JSON

**Reality:** Consilium is only useful for single queries (<50). For batch, use Mistral direct.

## CONSILIUM AUDIT WORKFLOW (27.06.2026)

### Правильный API вызова

**consilium_ask возвращает:** `{"responses": {model: text}, "best": str, "all_agree": bool}`
**НЕ возвращает:** `consensus_score`, `models_asked`, `json_result`, `json_data`

```python
from providers import consilium_ask, CONSILIUM_MODELS

async def audit(session, prompt, use_all=False):
    models = CONSILIUM_MODELS if use_all else CONSILIUM_MODELS[:3]
    result = await consilium_ask(session, prompt, models=[m[0] for m in models])
    # result["best"] = самый частый ответ (str)
    # result["responses"] = {model_name: response_text}
    # result["all_agree"] = True если все модели ответили одинаково
    return result
```

**Параметры consilium_ask:**
- `session` — aiohttp.ClientSession (обязательно)
- `prompt` — текст запроса
- `models` — list[str] моделей (по умолчанию первые 3)
- **НЕ принимает** `use_all_models`, `timeout`, `require_fields` — вызовет TypeError

### Текущая доступность моделей (27.06.2026)
| Модель | Статус |
|--------|--------|
| mistral/mistral-large-latest | ✅ Работает |
| groq/llama-3.3-70b-versatile | ⚠️ Circuit breaker после 10 ошибок |
| sambanova/DeepSeek-V3.2 | ❓ Проверить |
| cloudflare/@cf/meta/llama-3.2-3b-instruct | ⚠️ Часто нет JSON |
| openrouter/google/gemini-2.5-flash-lite | ❌ Нет кредитов |

### Паттерн аудита всех 4 слоёв

Для каждого слоя создаётся скрипт `audit_layerN.py` который:
1. Формирует промпт на ENGLISH (избегать кириллицы в коде!)
2. Вызывает `consilium_ask(session, prompt, models=FULL_MODELS)`
3. Сохраняет `best` ответ
4. Парсит JSON из ответа → применяет правки

### Питфоллы
- **Кириллица в heredoc/python -c** → SyntaxError. Пиши промпт в файл, запускай из файла.
- **лишние параметры** → TypeError. consilium_ask принимает только (session, prompt, models)
- **ответ модели содержит markdown** → парсить JSON через regex `\{.*\}` или `re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)`

## CODE QUALITY CHECKLIST (27.06.2026)

При ревью кода пайплайна проверять:
1. **Дублирование модулей** — классы/функции должны импортироваться из `dedup/`, `cleaner/`, а не дублироваться inline
2. **Неиспользуемые импорты** — `grep "^import" | grep -v "используется"` или IDE inspection
3. **Жадные regex** — `+` и `*` без якоря `$` или lookahead `(?=...)` захватывают лишнее
4. **Избыточные проверки** — `if x and x != ""` → достаточно `if x`
5. **Модульность** — pipeline = thin orchestrator, вся логика в подмодулях
6. **`ё`/`Ё` в regex** — `re.I` НЕ делает `е` ≈ `ё`. Всегда включай `ёЁ` в character class `[^...]` или используй `а-яА-ЯёЁ`

**Пример рефакторинга (5 исправлений, -121 строка):** `references/code-review-refactoring-2026-06-27.md`
**Regex audit (Е vs Ё, greedy patterns):** `references/regex-audit-2026-06-27.md`

## KEYWORD MAINTENANCE RULES (28.06.2026)

### BAD_KEYWORDS — НЕ удалять без крайней необходимости
- `СТЕНД`, `STAND`, `BOOTH` — "СТЕНД 82B88" = выставочный мусор
- `PAV`, `HALL`, `PAVILION` — то же самое
- Эти слова были ошибочно удалены ранее → "СТЕНД 82B88" перестал отсекаться

### NON_FOOD — расширять географическими терминами
- `РЕСПУБЛИКА`, `ОБЛАСТЬ`, `КРАЙ`, `ГОРОД`, `АДРЕС` — "РЕСПУБЛИКА УЗБЕКИСТАН" = мусор
- `EXPO`, `FAIR`, `CONFERENCE` — на английском

### Тестирование изменений keyword
```bash
cd ~/.hermes/skills/layer4-cleaner
python3 pipeline_v55_final.py ~/.hermes/audit/sample_raw_200.csv --dry-run
```
- Проверить reject rate (должен быть 14-16%)
- Проверить `rejected.csv` — СТЕНД, РЕСПУБЛИКА, ВЫСТАВКА должны отсекаться

## БАГИ НАЙДЕННЫЕ В СЛОЯХ 1-3 (27.06.2026)

**Детальный файл:** `references/layer1-3-bugs-found-2026-06-27.md`

### Ключевые исправления:
1. **Слой 1:** `ask_model()` не принимает `require_fields` — убрать kwargs
2. **Слой 1:** модели возвращают dict в groups — добавить `isinstance` проверку
3. **Слой 3:** parse_catalogs.py — все 5 источников мертвы (bozor.tj, inform.kg, georgiayp, madeinuzbekistan, n4.biz). Файл нужно удалить.
4. **Слой 4:** STAND/BOOTH должны оставаться в BAD_KEYWORDS (не удалять!)
5. **Слой 4:** Географические термины (РЕСПУБЛИКА, ОБЛАСТЬ, КРАЙ) → NON_FOOD
6. **Слой 3:** Все источники в parse_catalogs.py мертвы — перед добавлением парсера всегда делай curl-проверку. Детали: `references/dead-source-detection-2026-06-27.md`
### Типичные результаты
- 5,705 raw → 509 классифицированных → 332 уникальных (91% отброшено)
- Категории: кондитерка(161), молочка(144), хлеб(55), чай/кофе(50), крупы(28), заморозка(26)

### Питфоллы загрузки в clean_clients
- **id**: не включать — генерируется автоматически (UUID)
- **PGRST102**: все объекты в батче должны иметь идентичный набор ключей
- **is_duplicate**: булево, из CSV приходит "True"/"False"
- **duplicate_of**: None если пусто (не передавать пустую строку)
- **category**: НЕ существует в таблице — хранить категорию в description как `[категория]`

## АКТУАЛЬНАЯ СТРУКТУРА clean_clients (проверено 24.06.2026)

**Реальные колонки**: `id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`

**НЕ существующие колонки** (не добавлять!): `moysklad_id`, `category`, `name`, `city`, `address`, `products`, `tags`, `group_tag`, `holding`, `confidence`, `data_score`, `needs_review`, `activity_type`, `legal_title`, `legal_address`, `inn`

⚠️ **Питфолл**: `duplicate_of` — поле UUID. Пустая строка `""` вызывает ошибку `22P02`. Решение: просто не включать ключ `duplicate_of` если значение пустое.

## ПОЛНЫЙ ПАЙПЛАЙН ОЧИСТКИ: raw_parsed_data → clean_clients (25.06.2026)

### Когда использовать
Когда пользователь просит "почистить базу", "сформировать чистую базу", "очистить и отфильтровать", "запустить пайплайн".

### Главный скрипт
**`/home/khadas/.hermes/agents/parser/scripts/full_pipeline_all.py`** — полный whitelist-пайплайн. Загружает сырые данные из raw_parsed_data, фильтрует по 10 категориям, дедуплицирует, загружает в clean_clients.

### Финальный результат (25.06.2026)
- 72,153 raw → 9,087 clean_clients (12.6% сохранено)
- Whitelist: кондитерка, молочка, хлеб, детское питание, дистрибьюция, масла/жиры, заморозка, снеки, орехи, сухофрукты

### Правила загрузки в clean_clients
- Все записи в батче должны иметь ОДИНАКОВЫЙ набор ключей (PGRST102)
- Не включать `id` — генерируется автоматически
- Не включать `duplicate_of` если пустое
- Категорию сохранять в `description` формате `[категория] описание` (поля `category` нет!)

## Предзагрузочные проверки (22.06.2026)

**ВСЕГДА перед массовым скриптом:**
1. Проверь структуру таблицы: `curl -s ".../rest/v1/table?select=*&limit=1"` — убедись что все поля в скрипте существуют
2. Проверь API ключ: `curl -s -o /dev/null -w "%{http_code}" "https://api.provider.com/v1/models"`
3. Не используй поля которых нет в таблице (raw_json, status, reg_date, city, address, categories, source_year, raw_data — частые ошибки)
4. Используй retry + backoff для Supabase PATCH
5. PYTHONUNBUFFERED=1 для фоновых процессов

### АКТУАЛЬНАЯ СТРУКТУРА raw_parsed_data (проверено 24.06.2026)
**Колонки**: `id, name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, dedup_method, dedup_confidence, created_at`
**НЕТ**: `city, address, categories, source_year, raw_data, country_iso, is_cis`

### Питфоллы загрузки в Supabase
- **UUID поля (id, duplicate_of)**: не передавать пустую строку — 22P02 error. `id` вообще не включать. `duplicate_of` — None если пусто.
- **PGRST102**: все объекты в батче должны иметь идентичный набор ключей. Опциональные поля включать всегда с None/"".
- **is_duplicate**: булево, из CSV приходит "True"/"False".

**Детали в:** `references/cleanup-session-2026-06-22.md`

## Нормализация телефонов (25.06.2026)

**Проблема:** Базе были телефоны в формате `8 800 XXX XX XX`, `374 10 XX XX XX`, `1-800-XXX-XXXX` — без `+`.

**Решение:**
- `8 (XXX) XXX-XX-XX` → `+7 (XXX) XXX-XX-XX` (убрать первую 8, добавить +7)
- `374/375/370/371/372/373/380/381/420/421/44/49/33/39/34/351/353/354/358/359/36/48/31/32/352/355/356/357/358/992/993/994/995/996/998 XXX...` → просто добавить `+`
- `1-800-XXX-XXXX` → `+1-800-XXX-XXXX`

**Детали и edge cases:** `references/phone-normalization-2026-06-25.md`

## Нормализация стран — ПРАВИЛО ПОЛЬЗОВАТЕЛЯ (25.06.2026)

**Пользователь явно указал:** "Страну нужно вставлять если она очевидна, где то упоминается, или телефон подходит, но не выдумывать и не ставить по умолчанию."

- **МОЖНО**: телефонный код (+998→Узбекистан, +996→Кыргызстан...), ключевые слова (Алматы→Казахстан, Ташкент→Узбекистан)
- **НЕЛЬЗЯ**: ставить "Россия"/"Казахстан" по умолчанию, выдумывать из контекста
- **Скрипт:** `/home/khadas/.hermes/agents/parser/scripts/fix_countries.py`
- **Детали:** `references/country-normalization-2026-06-25.md` — полная карта стран/ключевых слов, паттерны мусора
- **Результат:** 188 мусорных стран найдено, 17 заполнено, 171 оставлено пустыми (неочевидно)

## Supabase VIM4 Performance (25.06.2026)

**Проблема:** REST API на VIM4 очень медленный при множественных запросах. Процессы зависают.

**Решение:** Используй `supabase-py client` для массовых операций:
```python
from supabase import create_client
sb = create_client(SB_URL, SUPABASE_SERVICE_KEY)
all_data = sb.table('clean_clients').select('id,name_clean,phone').execute().data
```
Загружает все 9K записей за ~1s. REST API только для единичных запросов.

**Детали:** `references/supabase-vim4-performance-2026-06-25.md` — список зависших процессов, решения.

## НОРМАЛИЗАЦИЯ name_clean (22.06.2026)

### Проблема
В ~4,040 записях name_clean содержит страну на английском (`BAIKAL GROUP, RUSSIA`), а в ~1,653 — форму собственности (`LLC`, `LTD`, `GMBH`, `SRL` и т.д.). Это артефакт парсинга Продэкспо.

### Паттерны для извлечения страны
```python
COUNTRY_EXTRACT = [
    (r',\s*(russia|россия)\s*$', 'Россия'),
    (r',\s*(kazakhstan|казахстан)\s*$', 'Казахстан'),
    (r',\s*(uzbekistan|узбекистан)\s*$', 'Узбекистан'),
    (r',\s*(azerbaijan|азербайджан)\s*$', 'Азербайджан'),
    (r',\s*(armenia|армения)\s*$', 'Армения'),
    (r',\s*(kyrgyzstan|кыргызстан|киргизия)\s*$', 'Кыргызстан'),
    (r',\s*(tajikistan|таджикистан)\s*$', 'Таджикистан'),
    (r',\s*(turkmenistan|туркменистан)\s*$', 'Туркменистан'),
    (r',\s*(georgia|грузия)\s*$', 'Грузия'),
    (r'(республика|republic\s+of)\s+(казахстан|kazakhstan)', 'Казахстан'),
    # ... и т.д. для всех целевых стран
]
```

### Паттерны для удаления формы собственности
```python
PROP_PATTERNS = [
    r',\s*(llc|ltd|inc|corp|gmbh|srl|sa|bv|ag|plc)\s*$',
    r'\b(llc|ltd|inc|corp|gmbh|srl|bv|ag|plc)\b',
    r'\b(limited\s+liability\s+company)\b',
    r'\b(joint\s+stock\s+company|jsc)\b',
]
```

### Алгоритм
1. Сначала извлечь страну из name_clean → записать в country (если пусто)
2. Затем удалить страну и форму собственности из name_clean
3. Обновить обе колонки одним PATCH

### Колонка source
Данные приходят из: `prodexpo_2022-2026` (~12,500), `foodsuppliers` (1,280), `prodexpo_icatalog` (~2,700), `foodexpo_kz`, `worldfood_moscow`, `trade.com.tm`, `consilium_*`, `interfood_az`. moysklad_id — UUID из МойСклад.

### Колонка category
Заполнена только в ~805 записях из ~17,800. Основные: кондитерка (124), хлеб (123), жиры (61), сухофрукты (53), мука (50). Нужно заполнить через Mistral для остальных.

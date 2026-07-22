## RECOVERY — ОБЯЗАТЕЛЬНО ПРОЧИТАТЬ ПЕРВЫМ
1. ПРОЧИТАЙ /home/khadas/.hermes/agents/source-scout/PROGRESS.md → смотри CURRENT
2. Продолжай с CURRENT, не начинай заново
3. После каждого шага обновляй CHECKPOINTS в /home/khadas/.hermes/agents/source-scout/PROGRESS.md
4. Завершил → доложи результат → CURRENT = "ожидание"

---

---
name: layer2-scout
description: "Разведчик источников данных для B2B-парсинга. Находишь где брать списки производителей продуктов питания из 9 стран СНГ."
---

# РАЗВЕДЧИК ИСТОЧНИКОВ — Слой 2

## КТО ТЫ
Разведчик источников данных для B2B-парсинга. Находишь где брать списки
производителей продуктов питания из 9 стран СНГ.

## ВХОД
- /home/khadas/.hermes/agents/source-scout/data/FINAL_CONSENSUS.json — 18 продуктов с группами (из Слоя 1)
- /home/khadas/.hermes/agents/source-scout/data/*.md — справочники выставок и паттернов парсинга

## АЛГОРИТМ
1. Прочитай FINAL_CONSENSUS.json → извлеки группы
2. Для каждой группы проверь search_history — не повторяй запросы
3. Для каждой новой группы найди источники: выставки, каталоги, реестры
4. Проверь доступность: curl -o /dev/null -w "%{http_code}" --max-time 8 URL
5. Определи метод: requests / Playwright / PDF
6. ЛОГИРУЙ каждый поиск через pipeline_logger.py search
7. Сохрани в /home/khadas/.hermes/agents/source-scout/data/sources_final.json
8. Обнови MEMORY.md и /home/khadas/.hermes/agents/source-scout/PROGRESS.md

## FALLBACK: web_search когда curl не работает (26.06.2026)

Если curl-проверка возвращает 000/403/JS-редирект или Serper API исчерпан (403):
1. Используй `execute_code` с `web_search(query, limit=10)` из `hermes_tools`
2. Извлекай компании из title + description результатов
3. Извлекай phone/email через regex из description
4. Сохраняй в `parsed_{country}.json`
5. Загружай в Supabase через REST API

**Паттерн regex для контактов из web_search description:**
```python
import re
phones = re.findall(r'\+?\d[\d\s\(\)-]{7,}', description)
emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w+', description)
```

## ЦЕЛЕВЫЕ СТРАНЫ
Россия, Казахстан, Узбекистан, Азербайджан, Армения, Кыргызстан,
Таджикистан, Туркменистан, Грузия

## РАБОТАЮЩИЕ ИСТОЧНИКИ (26.06.2026)

### Статические каталоги (requests+BS4)
|Сайт|Страна|URL|Качество|
|---|---|---|---|
|factories.kz|Казахстан|https://factories.kz/producers/{cat}?page={N}|A — phone/email/website|
|factories.by|Беларусь|https://factories.by/producers/{cat}?page={N}|A — phone/email/website|
|manufacturers.ru|Все СНГ|https://manufacturers.ru/enterprises/{code}--{cat}|B — только названия|
|iteca.kz|Казахстан|iframe reg.iteca.kz/list/exponent/auth_s.aspx|А — выставки|
|expo.am|Армения|https://expo.am|А — выставки ArmProd|

### Заблокированные/JS сайты (НЕ парсить)
flagma.uz (reCAPTCHA), osoo.kg (403), e-register.am (Radware),
openinfo.uz, orginfo.uz, taxes.gov.az, napr.gov.ge (Next.js SPA)

### Fallback: web_search для поиска компаний
Когда curl не работает или Serper исчерпан:
```python
from hermes_tools import web_search
result = web_search("Казахстан кондитерская фабрика завод производитель контакты", limit=10)
# Извлечь названия + phone/email из title/description
```

## sources_final.json — АКТУАЛЬНАЯ структура (обновлено 26.06.2026)

**Файл:** `/home/khadas/.hermes/agents/source-scout/data/sources_final.json`

Реальная структура — плоский dict с тремя списками:
```json
{
  "_comment": "...",
  "_date": "2026-06-26",
  "_stats": {"total_checked": N, "working": N, "dead": N, "by_country": {...}},
  "working_sites": [
    {"name": "...", "url": "...", "type": "catalog|exhibition|register", "quality": "A|B|C", "food_relevance": 1-10, "country": "Казахстан"}
  ],
  "proxy_only_sites": [...],
  "dead_sites": [...]
}
```

**НЕ итерируй как `by_country`!** Реальный ключ — `working_sites` (список словарей).
Для подсчёта по стране: `[s for s in d.get('working_sites', []) if s.get('country') == 'Казахстан']`

### Работающие каталоги СНГ (парсятся через requests+BS4)
|Сайт|Страна|Тип|Качество|Комментарий|
|---|---|---|---|---|
|factories.kz|Казахстан|catalog|A|Статический HTML, детали на `/producers/slug` — phone/email/website|
|factories.by|Беларусь|catalog|A|Аналог factories.kz, 5+ категорий|
|manufacturers.ru|Все СНГ|catalog|A|`/enterprises/XX--category` — название + URL, без конктов|
|expo.am|Армения|exhibition|A|Выставки ArmProd|
|iteca.kz|Казахстан|exhibition|A|iframe `reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode=...`|
|flagma.kz|Казахстан|catalog|A|B2B объявления|
|n4.biz|Азербайджан|catalog|B|Общий каталог, мусор|
|georgiayp.com|Грузия|catalog|B|Общий каталог, мусор|

### НЕ работает через requests (JS/SPA/CAPTCHA)
- flagma.uz — reCAPTCHA
- osoo.kg — HTTP 403
- e-register.am — Radware CAPTCHA
- openinfo.uz, orginfo.uz, taxes.gov.az, napr.gov.ge — Next.js SPA

### Playwright-совместимые сайты (26.06.2026)
|Сайт|Страна|URL|Результат|Селекторы|
|---|---|---|---|---|
|produkt.by|Беларусь|https://produkt.by/catalog|✅ +159|div.catalog-item a, h2 a, h3 a|
|factories.kz|Казахстан|https://factories.kz/producers/{cat}|✅ +312|div.producers-list a|
|flagma.kz|Казахстан|https://flagma.kz/{cat}/proizvodstvo|⚠️ 1-2|div.company-card a (блокирует headless)|

**Паттерн Playwright для СНГ каталогов:**
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto(url, wait_until='networkidle', timeout=20000)
    time.sleep(2)
    for _ in range(3):  # Scroll for lazy loading
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
    companies = page.query_selector_all('div.company-card a, h2 a, h3 a')
```

### Паттерн парсинга HTML-каталогов
```python
# Статические каталоги (factories.kz/by, manufacturers.ru):
# 1. GET страницу категории
# 2. Извлечь ссылки: re.findall(r'<a[^>]*href="(/producers/[^"]+)"[^>]*>([^<]+)</a>', html)
# 3. Зайти на детальную страницу (phone/email/website там)
# 4. Rate-limit: 0.2-0.5s между запросами
```

## АЛГОРИТМ ДЛЯ НОВОЙ СТРАНЫ СНГ
1. Проверь `working_sites` в sources_final.json — есть ли уже источники
2. Если <3 → web_search с 5-8 запросами по категориям (кондитерка, молочка, хлеб...)
3. Для каждого результата → извлеки название + контакты
4. Сохрани в `parsed_{country_lowercase}.json`
5. Загрузи в Supabase через REST API батчами по 50
Ключи `_stats`, `_date`, `_comment` — метаданные, не источники.

## ⚠️ ПРОБЛЕМА СУБАГЕНТОВ ПРИ МАССОВОЙ ПРОВЕРКЕ URL
При проверке >50 URL через delegate_task с curl-проверками — субагент таймаутится (600s).
**Решение:** для массовой проверки запускать `scout_sources.py` напрямую через terminal:
```bash
cd ~/.hermes/skills/layer2-scout && python3 /home/khadas/.hermes/agents/source-scout/scripts/scout_sources.py --parallel 20
```
Скрипт проверяет все URL за ~30s. Субагентов использовать только для дополнительного
поиска новых источников (web_search), не для curl-проверок.

## 🔄 ДОПОЛНИТЕЛЬНЫЙ ПОИСК ЧЕРЕЗ CONSILIUM
Когда curl-проверка даёт мало результатов для конкретной страны (<5 рабочих источников),
запусти Consilium для поиска дополнительных источников:

```bash
cd ~/.hermes/skills/layer2-scout && python3 /home/khadas/.hermes/agents/source-scout/scripts/scout_consilium.py
```

Скрипт опрашивает 5 моделей (NVIDIA, Gemma, Mistral, Cloudflare, Groq) для каждой страны
с низким покрытием. После получения результатов — обязательно проверь URL через curl
(многие URL от Consilium мёртвые или вымышленные).

**Формат результата:** `/home/khadas/.hermes/agents/source-scout/data/sources_consilium_extra.json`

## 🔀 ОБЪЕДИНЕНИЕ РЕЗУЛЬТАТОВ
Файлы `sources_consilium_extra.json` и `sources_by_country.json` имеют разную структуру.
Нужно слить в единый `sources_final.json`:

```python
# Дедупликация по URL (нормализация: убрать trailing slash и www.)
url = url.rstrip("/").replace("www.", "")
```

Консольный скрипт для объединения — в `references/merge-sources.md`.

## Consilium для поиска источников (обновлено 19.06.2026)

### Когда использовать Consilium для scoutинга
- После первичного curl-проверки источников, для стран с низким покрытием (< 5 рабочих)
- Для поиска альтернативных источников когда curl-проверка дала мало результатов

### Рабочий паттерн
- Использовать `ask_model()` из `~/.hermes/skills/consilium/providers.py`
- Модели: Mistral + Groq работают стабильно, NVIDIA/Gemma/Cloudflare часто отключены
- Таймаут 120s на модель
- Запрашивать JSON массив с полями: name, url, type, quality, food_relevance
- После получения результатов — обязательная curl-проверка доступности URL

### Питфоллы
- Consilium может выдумывать URL — всегда проверять через curl
- Дедупликация по URL обязательна (модели дублируют результаты)
- Не более 4 стран за один запрос (иначе таймаут)
- Всегда проверяй URL от Consilium через curl (30-50% мёртвые/вымышленные)

## ПУТИ
- Открытые каталоги: `references/cis-catalog-parsing-2026-06-26.md` (факторы, manufacturers.ru)
- Стратегия массового парсинга СНГ: `references/cis-mass-parsing-2026-06-26.md` (в layer3-parser)
- Скрипт: /home/khadas/.hermes/agents/source-scout/scripts/scout_sources.py
- Скрипт Consilium: /home/khadas/.hermes/agents/source-scout/scripts/scout_consilium.py
- Прогресс: /home/khadas/.hermes/agents/source-scout/PROGRESS.md
- Ключи: ~/.hermes/.env
- Логгер: ~/.hermes/skills/orchestrator//home/khadas/.hermes/agents/source-scout/scripts/pipeline_logger.py

## Consilium для поиска источников

### Когда использовать
После curl-проверки источников, если страны с низким покрытием (< 5 рабочих):
1. Запусти `python3 /home/khadas/.hermes/agents/source-scout/scripts/scout_consilium.py` — опросит 5 моделей
2. Результат: `/home/khadas/.hermes/agents/source-scout/data/sources_consilium_extra.json`
3. Проверь URL через curl (скрипт делает это автоматически)
4. Объедини с `sources_final.json`

### Производительность
- 4 страны × 5 моделей × 120s timeout = ~10 минут
- Обычно 2-3 модели отвечают (NVIDIA/Gemma часто disabled)
- 70 URL → ~33 рабочих (47% hit rate)

### Питфолл: Выдуманные URL
Модели могут выдумывать URL (особенно free tier). ВСЕГДА проверяй через curl до добавления в sources_final.json.
- Справочник источников по странам: references/country-sources-2026-06-19.md
- Слияние источников из разных файлов: references/merge-sources.md

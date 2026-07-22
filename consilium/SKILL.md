---
name: consilium
description: "Consilium Pipeline — мульти-ИИ поиск и обогащение B2B-клиентов (5 моделей голосуют)"
---

# Consilium Pipeline — поиск и обогащение B2B-клиентов

## Назначение
Автоматический поиск, обогащение и очистка клиентов для продаж глазури.
Использует мульти-ИИ консилиум (3-5 моделей голосуют) на каждом этапе.

## Этапы
1. **Scout** — поиск компаний из каталогов, выставок, Serper web-поиска
2. **Enricher** — ИНН (DaData), телефоны, сайты, email
3. **Parser** — парсинг сайтов, извлечение продукции, категоризация
4. **Matcher** — сравнение с МойСклад, дедупликация
5. **Verifier** — фильтрация 9 стран СНГ, очистка, confidence score

## Целевые страны (СНГ, 9 стран)
Россия, Казахстан, Узбекистан, Азербайджан, Армения, Кыргызстан, Таджикистан, Туркменистан, Грузия

## Структурирование анализа

### Разбивка на подзадачи
1. **Основной анализ**: Определение групп и подгрупп для продукта (например, какао-порошок).
2. **Сегмент ЗОЖ**: Отдельный запрос для выявления производителей здорового питания.
3. **Объединение результатов**: Слияние данных из основного анализа и сегмента ЗОЖ.

### Пример структуры анализа
```json
{
  "Какао-порошок": {
    "Кондитерские фабрики": {
      "Крупные производители": ["фабрика1", "фабрика2"],
      "Малые производители": ["фабрика3"]
    },
    "Производители здорового питания": {
      "Протеиновые батончики": ["бренд1", "бренд2"],
      "Веганские десерты": ["бренд3"]
    }
  }
}
```

### Шаблон для объединения данных
- **Файл**: `templates/merge_results.py` (см. ниже).
- **Использование**: Группировка по ключевым словам, сортировка по консенсусу.

## Форматирование отчётов
- **Списки >20 элементов**: Показывать только топ-10-15 с указанием общего количества.
- **Пример**:
```
Всего: 45 компаний.
Топ-10:
1. ООО "Кондитерская фабрика"
2. АО "Молочный завод"
...
```
- **Полный список**: Предоставлять только по запросу.

## Product Analysis (Анализ продуктов)

### Назначение
Анализ продуктов для пищевой промышленности (кондитерка, молочка, ЗОЖ) через готовый скрипт `analyze_product.py`.

### Как использовать
1. **Запуск анализа** (готовый скрипт, не писать код):
```bash
cd ~/.hermes/skills/layer1-analyst
python3 scripts/analyze_product.py "Какао-порошок натуральный"
```

2. **Параллельный запуск** (для ускорения):
```bash
for product in "Какао-порошок" "Шоколадная глазурь" "Лецитин"; do
  timeout 120 python3 scripts/analyze_product.py "$product" &
  sleep 2
  if [[ $(jobs -r | wc -l) -ge 3 ]]; then wait -n; fi
done
wait
```

3. **Результат**: Сохраняется в `data/last_analysis.json` (структура см. ниже).

### Структура JSON-отчёта
```json
{
  "product": "Красители пищевые",
  "subgroups": ["производство карамели", "производство йогуртов"],
  "groups": ["Кондитерские изделия", "Молочные продукты"],
  "keywords": ["фабрика кондитерских изделий", "молочный комбинат"],
  "exclude_keywords": ["конкуренты по производству красителей"],
  "models_ok": "3/3",
  "needs_review": false
}
```

### Обработка лимитов моделей
- **OpenRouter (429)**: Если лимит — переключаться на 3 модели (Mistral, Groq, Cloudflare).
- **Таймауты**: Для Mistral/Claude увеличивать до 90-120s.

### Шаблон для результатов
См. `references/product_analysis_template.md` (создан в этой сессии).

## Кэш
- L1: SQLite (cache.db) — 7 дней TTL (удалять перед новым запуском!)
- L2: Supabase (consilium_cache) — 30 дней TTL

## Резервные API

### Serper (работает через `urllib.request`)
- **Статус**: Работает. Ключ в `~/.hermes/skills/consilium/temp_keys.json` (поле `keys.SERPER_API_KEY.current`), НЕ в `.env`.
- **Лимит**: 100 запросов/день (бесплатный тариф).
- **Использование**: Для поиска сайтов, контактов компаний. Hit rate ~90-96%.
- **Паттерн**:
```python
import json, urllib.request
with open('/home/khadas/.hermes/skills/consilium/temp_keys.json') as f:
    temp_keys = json.load(f)
SERPER_KEY = temp_keys['keys']['SERPER_API_KEY']['current']

url = "https://google.serper.dev/search"
headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
payload = json.dumps({"q": "запрос", "gl": "ru"})
req = urllib.request.Request(url, data=payload.encode(), headers=headers)
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())
    results = data.get('organic', [])
```

### Fallback для Tavily
- **Статус**: Заблокирован (403 Forbidden).
- **Альтернатива**: Использовать Serper или прямые запросы к Google через прокси.
- **Прокси-пример**:
```python
proxies = {
    'http': 'http://proxy-server:port',
    'https': 'http://proxy-server:port'
}
response = requests.get(
    "https://www.google.com/search?q=кондитерские+фабрики+Москва",
    proxies=proxies
)
```

## Извлечение JSON из ответов моделей

Модели часто возвращают JSON с markdown-обёртками (` ```json `), переносами строк внутри строковых значений или экранированными символами.

**Паттерн парсинга (robust):**
```python
import re, json

def extract_json(text):
    if not text:
        return None
    text = text.strip()
    # Убираем markdown-обёртки
    if "```" in text:
        text = re.sub(r'```(?:json)?', '', text).strip()
    # Находим JSON-объект
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        raw = text[start:end+1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Пробуем с strict=False для экранированных переносов
            try:
                return json.loads(raw, strict=False)
            except json.JSONDecodeError as e:
                # Убираем экранированные переносы внутри строк
                clean_raw = re.sub(r'(?<!\\)\\n', ' ', raw)
                try:
                    return json.loads(clean_raw, strict=False)
                except:
                    # Последний шанс: regex-парсинг ключей
                    try:
                        data = {}
                        for match in re.finditer(r'"([^"]+)"\s*:\s*"([^"]*)"', clean_raw):
                            data[match.group(1)] = match.group(2)
                        return data if data else None
                    except:
                        return None
    return None
```

**Таймауты моделей:**
- Gemini, DeepSeek, Llama: 60s достаточно
- Claude, Mistral: увеличить до **90-120s** (часто не отвечают на 60s)
- OpenRouter: если статус **429**, переключаться на 3 модели (Mistral, Groq, Cloudflare)

**Fallback-стратегия:**
1. Если модель вернула пустой ответ или ошибку → повторный запрос с увеличенным таймаутом (120s).
2. Если повторный запрос не удался → исключить модель из консилиума и перезапустить анализ.
3. Если 2+ модели недоступны → переключиться на резервные (Groq, Cloudflare).

**Таймауты моделей:**
- Gemini, DeepSeek, Llama: 60s достаточно
- Claude, Mistral: увеличить до 90-120s (часто не отвечают на 60s)

**Известные статусы инструментов (обновлено 27.06.2026):**
- Tavily: заблокирован (403 Forbidden) — НЕ использовать
- Serper: работает нормально (100 запросов/день), ключ в `.env` и `temp_keys.json`
- Supabase: может засыпать на бесплатном плане — вайкать на дашборде
- Proton Proxy: нестабилен — всегда делай fallback на прямой запрос
- **consilium_ask() bug:** line 349 `result.strip()` падает если best=dict — нужен isinstance check
- **Groq:** circuit breaker срабатывает при batch-нагрузке, только для <50 запросов
- **OpenRouter:** нет кредитов (402), все модели недоступны
- **Mistral:** работает стабильно (medium-large-latest), ключ в `.env`

### ⚠️ Статус провайдеров AI для batch-обработки (обновлено 02.07.2026)

**Рабочие провайдеры (4/6):**

| Провайдер | Модель | Статус | Примечание |
|-----------|--------|--------|------------|
| **Mistral Direct API** | `mistral-large-latest` | ✅ Стабильный | Rate limit ~1 req/s, 120s timeout, единственный для batch |
| **Groq** | `llama-3.3-70b-versatile` | ⚠️ Работает | Circuit breaker при >50 запросов |
| **SambaNova** | `DeepSeek-V3.2` | ✅ Работает | Хорошая замена Nemotron |
| **GitHub Models** | `gpt-4o` | ✅ **NEW** Работает | Через `GITHUB_TOKEN`, endpoint `models.inference.ai.azure.com` |

**Нерабочие провайдеры (2/6):**

| Провайдер | Проблема | Решение |
|-----------|----------|---------|
| **Cloudflare** | HTTP 429 — daily 10K neurons exhausted | Upgrade to Workers Paid plan |
| **OpenRouter** | HTTP 429 / 402 — no credits | Add credits or use paid models |

**Рекомендация для Consilium:**
- `DEFAULT_MODELS = [Mistral, Groq, SambaNova, GitHub]` (4 рабочие модели)
- Избегай `ALL_MODELS` — включает сломанные Cloudflare/OpenRouter
- Для batch (>50 запросов) — только Mistral Direct напрямую

**Исправленные баги в providers.py (02.07.2026):**
1. GitHub token: был `GH_TOKEN` → стал `GITHUB_TOKEN` (существует в `.env`)
2. Syntax error в f-string: `os.getenv("GH_TOKEN", "")` внутри f-string ломал кавычки — вынесен в переменную
3. Добавлен GitHub в `CONSILIUM_MODELS` как 6-я запись

Подробности: `references/provider-status-2026-07-02.md`
cd ~/.hermes/skills/consilium && python3 pipeline.py
```

### Перед запуском с чистого листа
1. Бэкап clients → ~/salesbot/data/clients_backup_YYYYMMDD.json (батчами по 1000)
2. Очистить clients по 100 записей (Supabase delete не поддерживает limit)
3. Удалить cache.db
4. Убедиться что supabase_loader.py пишет в clients (НЕ clean_clients)

### Правило бэкапа и тестирования (27.06.2026, требование пользователя)
**Перед любыми изменениями в пайплайне или скриптах:**
1. Сделать бэкап: `mkdir -p ~/.hermes/backups/<project>-original && cp <файлы> ~/.hermes/backups/<project>-original/`
2. Внести ОДНО изменение
3. Протестировать на тестовых данных (≤200 записей): `python3 pipeline_v55_final.py test.csv --dry-run`
4. Сравнить с baseline (метрики, reject rate, причины)
5. Только после OK → следующее изменение
6. При регрессии: `cp ~/.hermes/backups/<project>-original/<файл> <файл>` для отката

**Текущий бэкап:** `~/.hermes/backups/layer4-original/`

### Главный источник данных: PDF-каталоги выставок
**PDF-каталоги выставок — ОСНОВНОЙ источник данных** (не веб-парсинг!).
Прошлый парсинг именно из PDF дал основную базу, но очистка была плохой.

**Как правильно парсить PDF:**
1. Ищем PDF через Serper: `"prodexpo 2026 catalogue filetype:pdf"`
2. Скачиваем через `curl -L` (НЕ через aiohttp — он не следует за 50 редиректами)
3. Альтернативно: прокси `https://proton-proxy.onrender.com/proxy?url=` но он тоже не всегда работает
4. Извлекаем текст через `fitz` (pymupdf)
5. Распознаём компании по паттернам (ООО, АО, ЗАО, ИП, ТОО и т.д.)
6. **КРИТИЧНО**: фильтруем мусор — регионы, государственные органы, павильоны

**Проблемы PDF-парсинга:**
- Страна определяется неправильно (PDF с регионами России → "Узбекистан")
- Решение: страна по умолчанию = страна выставки
- Контакты только у ~25-30% компаний в PDF
- Названия обрезаются, сливаются с описанием

**Работа с пользователем:**
- Пользователь ожидает что мы САМИ найдём все источники (не спрашивать URL!)
- Используй консилиум (5 моделей) для стратегических решений
- Действия с базой → через консилиум → ждать подтверждения человека

## Стратегия поиска (Consilium Brain, 2026-06-13)

### Проблема
Scout находит только ~89 компаний из каталогов. Выставки дают 0 (JS).

### Рекомендуемая стратегия: «Каталоги + Ассоциации + Геотаргетинг»
**Приоритет бесплатных источников → Serper только для точечных запросов**

**Serper-запросы (~60 штук):**
```
# Каталоги (27)
"кондитерские фабрики" каталог Россия
"молочные заводы" site:dairyunion.ru
foodstuff manufacturers directory Kazakhstan

# Геотаргетинг (36)
кондитерская фабрика Москва ИНН
молочный завод Алматы контакты
dairy factory Almaty Kazakhstan
```

**Ожидаемый результат:** 700-1200 компаний

## Технические заметки

### providers.py
- max_tokens=800 — минимум для JSON-ответов (300 обрезает)
- Для async-скриптов: write_file → запускать файл (не python3 -c с кириллицей)
- **ВАЖНО**: после правок проверяй что ВСЕ `_ask_*` функции имеют полное тело с `session.post()` — `_ask_cloudflare` ранее потеряла тело и молча возвращала None
- `consilium_ask()` — главная функция для мульти-опроса, определена в providers.py (НЕ в другом модуле)

### Вызов из скриптов (Python)

**Рабочий паттерн** — опрос через consilium из скрипта:
```python
import asyncio, aiohttp, os, sys
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/consilium"))
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.hermes/.env"))
from providers import consilium_ask, CONSILIUM_MODELS

async def main():
    models = [m[0] for m in CONSILIUM_MODELS]  # все 5 моделей
    # или для быстрого опроса только 3:
    # models = [m[0] for m in CONSILIUM_MODELS[:3]]

    prompt = "Analyze this..."
    
    async with aiohttp.ClientSession() as session:
        result = await consilium_ask(session, prompt, models=models)

    print(f"Best: {result.get('best','')[:500]}")
    print(f"Responded: {len(result.get('responses',{}))}/{len(models)}")
    print(f"All agree: {result.get('all_agree', False)}")

asyncio.run(main())
```

**Актуальная сигнатура (providers.py, 27.06.2026):**
```python
async def consilium_ask(session, prompt, models=None):
```
- `session` — aiohttp.ClientSession (обязательно)
- `prompt` — текст запроса (обязательно)
- `models` — список[str] моделей (по умолчанию CONSILIUM_MODELS[:3])
- **Возвращает:** `{"best": str, "responses": {model: response}, "all_agree": bool}`

**⚠️ НЕ используйте:** `use_all_models=`, `consensus_score`, `json_result`, `models_asked`, `models_responded`, `timeout=` — этих ключей/параметров нет в текущей версии.

**Актуальные модели (CONSILIUM_MODELS, 27.06.2026):**
1. `mistral/mistral-large-latest` — ✅ работает
2. `groq/llama-3.3-70b-versatile` — ⚠️ circuit breaker при batch
3. `sambanova/DeepSeek-V3.2` — ✅ работает
4. `cloudflare/@cf/meta/llama-3.2-3b-instruct` — ⚠️ часто нет JSON
5. `openrouter/google/gemma-4-31b-it:free` — ⚠️ нестабильна

**Паттерн для аудита через консилиум (write_file + exec):**
```python
# 1. Пиши промпт в файл (избегай кириллицы в -c)
result = terminal("python3 /path/to/audit_script.py", timeout=120)
# 2. Скрипт пишет результат в stdout или JSON-файл
```

**Извлечение JSON из результата:**
```python
import re, json
best = result.get("best", "")
if "```json" in best:
    raw = re.sub(r'```(?:json)?', '', best).strip()
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start:end+1])
```

**Извлечение JSON из ответов:**
Функция `_extract_json()` автоматически парсит JSON из ответов моделей (убирает markdown-обёртки, обрабатывает экранированные переносы). Результат доступен как `result["json_result"]`.

**Sandbox-совместимый Supabase доступ (urllib):**
```python
import urllib.request, urllib.error, json

SUPABASE_URL = "https://zimojaemhuapieeaxetd.supabase.co"
SUPABASE_KEY = "sb_secret_..."  # из ~/.hermes/.env

def sb_get_all(table, params=None, page_size=500):
    """Получает все записи с пагинацией."""
    all_data = []
    offset = 0
    while True:
        p = dict(params or {})
        p["limit"] = str(page_size)
        p["offset"] = str(offset)
        p["order"] = "id.asc"
        url = f"{SUPABASE_URL}/rest/v1/{table}?" + "&".join(f"{k}={v}" for k, v in p.items())
        req = urllib.request.Request(url)
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        if not data:
            break
        all_data.extend(data)
        offset += page_size
        if len(data) < page_size:
            break
    return all_data

def sb_insert(table, data):
    """Вставляет данные в Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    req = urllib.request.Request(url, method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=minimal")
    req.data = json.dumps(data).encode('utf-8')
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return {"status": resp.status, "ok": True}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode(), "ok": False}
```

**Примечание:** `supabase` Python клиент и `python-dotenv` НЕ доступны в sandbox. Всегда используйте `urllib.request` для Supabase REST API доступа.

### Supabase

#### ⚠️ CRITICAL: clean_clients schema (обновлено 28.06.2026)
**Реальные колонки**: `id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`

**НЕ существующие колонки** (не добавлять!): `moysklad_id`, `category`, `name`, `legal_title`, `city`, `address`, `products`, `tags`, `group_tag`, `holding`, `confidence`, `data_score`, `needs_review`, `activity_type`, `legal_title`, `legal_address`, `inn`, `updated_at`

**Питфоллы:**
- `name` → 400/42703 ошибка. Используй `name_clean`
- `category` → не существует. Категорию хранить в `description` как `[категория] описание`
- `duplicate_of` → UUID поле, пустая строка "" → 22P02 error

#### ⚠️ CRITICAL: Supabase is.null НЕ работает через query string (21.06.2026)
`country=is.null` в URL query → 400 Bad Request. **Решение:** загружай все записи с пагинацией и фильтруй локально:
```python
empty_country = [r for r in all_records if not r.get('country') or str(r.get('country')).strip() == '']
```

#### ⚠️ CRITICAL: Сессия падает при массовых tool calls (21.06.2026)
Слишком много быстрых вызовов terminal/execute_code → "Command interrupted" loop.
**Решение:** пиши скрипты в файлы через `write_file`, запускай в фоне через `terminal(background=True)`.
Не делай 10+ последовательных tool calls без пауз.

- **clients** — основная таблица (name, phone, email, website, inn, source, country, group_tag)
- **clean_clients** — служебная (НЕТ phone/email), не использовать для основной базы
- delete().limit() не работает — удалять по ID батчами по 100
- CREATE TABLE через API невозможно — только SQL в консоли

### Scout
- Прямой HTML-парсинг даёт ~89 записей
- Выставки требуют JS — нужен Serper или PDF-каталоги
- Новые источники: тендеры (zakupki.gov.ru), ассоциации, жёлтые страницы

### Consilium Brain
- Цикл: анализ → 2-3 варианта → человек утверждает → выполнение
- **Для стратегических решений: 5 моделей** (пользователь явно попросил)
- Для повседневных/быстрых: 3 модели
- **Всегда жди подтверждения человека** перед выполнением рекомендации
- Пользователь ожидает что мы САМИ найдём источники (не спрашивать URL!)

### Circuit Breaker — настройки для массовой обработки
**Текущие настройки** (обновлено 20.06.2026):
- Порог: 10 ошибок подряд → блокировка на 120с
- Для массовой обработки (10K+ запросов): увеличить порог до 20 или отключить

**Функции:**
- `_mark_provider_failure(model)` — инкрементирует счётчик, при достижении порога блокирует модель
- `_mark_provider_success(model)` — сбрасывает счётчик при успешном ответе
- `_is_provider_alive(model)` — проверяет не заблокирована ли модель

**Сброс в рантайме:**
```python
from providers import _provider_failures, _provider_skip_until
_provider_failures.clear()
_provider_skip_until.clear()
```

### _extract_json — обработка массивов и объектов
Модели возвращают JSON-массивы `[{...}, {...}]` или объекты `{...}`.
`_extract_json()` сначала ищет `[...]` (массив), потом `{...}` (объект).
Массив имеет приоритет — если ответ содержит и массив и объект, выбирается массив.

### consilium_ask — выбор best для массивов и объектов
`consilium_ask()` выбирает лучший ответ:
- Для массивов: выбирается массив с максимальным количеством элементов
- Для объектов: выбирается объект с максимальным количеством ключей
- Если JSON не распарсился — выбирается самый длинный текстовый ответ
- **`consilium_ask()`** — ГЛАВНАЯ функция для опроса нескольких моделей. Параллельно опрашивает 3 (DEFAULT_MODELS) или 5 (ALL_MODELS) моделей, собирает консенсус. Возвращает `{best, all_responses, consensus_score, json_result, models_asked, models_responded}`.
- **`DEFAULT_MODELS`**: Mistral + Groq + Gemini Flash Lite (3 модели, быстро)
- **`ALL_MODELS`**: DEFAULT + Llama-4-Maverick + Cloudflare Llama-3.2 (5 моделей, для критических решений)
- **`MODEL_TIMEOUTS`** — пер-модельные таймауты (Mistral 120s, Groq 60s, Gemini 60s)
- **`_extract_json()`** — robust парсинг JSON из ответов AI (markdown, escapes, regex fallback)
- **`_ask_cloudflare()`** — проверяй что тело `session.post()` на месте после правок (ломалось ранее — оставался только `except` без `try`)
- **НЕЛЬЗЯ** вызывать `from providers import consilium_ask` если функция не определена — всегда проверяй наличие перед использованием
- Подробная документация: `references/providers-architecture-2026-06-20.md`

### Таймауты моделей (актуально 20.06.2026)
- Mistral: 120s (часто не отвечает на 60s)
- Groq: 60s достаточно
- Gemini (OpenRouter): 60s достаточно
- OpenRouter free: 120s (медленные)
- Cloudflare: 90s

**Известные статусы инструментов (обновлено 27.06.2026):**
- Tavily: заблокирован (403 Forbidden) — НЕ использовать
- Serper: работает нормально (100 запросов/день), ключ в `.env` и `temp_keys.json`
- Supabase: может засыпать на бесплатном плане — вайкать на дашборде
- Proton Proxy: нестабилен — всегда делай fallback на прямой запрос
- **consilium_ask() bug:** line 349 `result.strip()` падает если best=dict — нужен isinstance check
- **Groq:** circuit breaker срабатывает при batch-нагрузке, только для <50 запросов
- **OpenRouter:** нет кредитов (402), все модели недоступны
- **Mistral:** работает стабильно (medium-large-latest), ключ в `.env`

### ⚠️ Статус провайдеров AI для batch-обработки (обновлено 02.07.2026)

**Рабочие провайдеры (4/6):**

| Провайдер | Модель | Статус | Примечание |
|-----------|--------|--------|------------|
| **Mistral Direct API** | `mistral-large-latest` | ✅ Стабильный | Rate limit ~1 req/s, 120s timeout, единственный для batch |
| **Groq** | `llama-3.3-70b-versatile` | ⚠️ Работает | Circuit breaker при >50 запросов |
| **SambaNova** | `DeepSeek-V3.2` | ✅ Работает | Хорошая замена Nemotron |
| **GitHub Models** | `gpt-4o` | ✅ **NEW** Работает | Через `GITHUB_TOKEN`, endpoint `models.inference.ai.azure.com` |

**Нерабочие провайдеры (2/6):**

| Провайдер | Проблема | Решение |
|-----------|----------|---------|
| **Cloudflare** | HTTP 429 — daily 10K neurons exhausted | Upgrade to Workers Paid plan |
| **OpenRouter** | HTTP 429 / 402 — no credits | Add credits or use paid models |

**Рекомендация для Consilium:**
- `DEFAULT_MODELS = [Mistral, Groq, SambaNova, GitHub]` (4 рабочие модели)
- Избегай `ALL_MODELS` — включает сломанные Cloudflare/OpenRouter
- Для batch (>50 запросов) — только Mistral Direct напрямую

**Исправленные баги в providers.py (02.07.2026):**
1. GitHub token: был `GH_TOKEN` → стал `GITHUB_TOKEN` (существует в `.env`)
2. Syntax error в f-string: `os.getenv("GH_TOKEN", "")` внутри f-string ломал кавычки — вынесен в переменную
3. Добавлен GitHub в `CONSILIUM_MODELS` как 6-я запись

Подробности: `references/provider-status-2026-07-02.md`

### Парсинг PDF-каталогов выставок
- **PDF — ОСНОВНОЙ источник**, не веб-парсинг
- Скачивать через `curl -L` (aiohttp не следует за 50 редиректами)
- Искать PDF через Serper: `"prodexpo 2026 catalogue filetype:pdf"`
- Страна по умолчанию = страна выставки (не определять по тексту PDF!)
- Контакты только у ~25-30% → нужен DaData + Serper для обогащения
- Подробности: `parser/references/pdf-parsing-exhibitions-2026-06-13.md`

### Недоступные сайты и альтернативы
- При проверке источников curl'ом: сначала прямой запрос (8s таймаут), затем через Proton Proxy (30s)
- Если оба вернули 000 — сайт DEAD, искать альтернативы через Serper
- Актуальный список недоступных сайтов и их замен: `references/dead-sites-alternatives.md`

## Модели — АКТУАЛЬНАЯ ДОСТУПНОСТЬ (обновлено 20.06.2026)

**Актуальные модели (27.06.2026, CONSILIUM_MODELS в providers.py):**

| Модель | Статус | Примечание |
|--------|--------|------------|
| `mistral/mistral-large-latest` | ✅ Стабильная | Таймаут 120s, единственная рабоят для batch |
| `groq/llama-3.3-70b-versatile` | ⚠️ Нестабильная | Circuit breaker при >50 запросов |
| `sambanova/DeepSeek-V3.2` | ✅ Работает | Замена для NVIDIA Nemotron |
| `cloudflare/@cf/meta/llama-3.2-3b-instruct` | ⚠️ Часто нет JSON | Не рекомендуется для критичных задач |
| `openrouter/google/gemma-4-31b-it:free` | ⚠️ Нестабильна | Частые ошибки, circuit breaker |

**Неработающие (не добавлять в списки):**
- `openrouter/nvidia/nemotron-3-super-120b-a12b:free` — ❌ Нет кредитов (402)
- `openrouter/meta-llama/llama-4-maverick` — ❌ Нет кредитов (402)

**Рекомендация:** Для аудита/анализа используйте 3-4 модели (Mistral + Groq + SambaNova + Cloudflare). Для batch-обработки (>50 запросов) — только Mistral напрямую, без консилиума.

## Массовая генерация данных через консилиум (добавлено 21.06.2026)

### Паттерн batch-генерации
Консилиум можно использовать для массовой генерации структурированных данных (списков компаний, категорий и т.д.):

```python
import asyncio, aiohttp, json, sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/consilium"))
from providers import consilium_ask

async def generate_batch(session, prompt, timeout=120):
    result = await consilium_ask(session, prompt, timeout=timeout)
    return result.get('json_result', [])

# Множественные запросы
async with aiohttp.ClientSession() as session:
    for i in range(10):  # 10 батчей по 50 компаний
        companies = await generate_batch(session, prompt)
        # Фильтровать дубли и загрузить в БД
```

**Ключевые параметры:**
- `timeout=120` — таймаут на модель
- Промпт должен требовать ТОЛЬКО JSON массив
- Указывать конкретные города/категории для разнообразия
- Передавать список уже известных записей для избежания дублей

**Ограничения:**
- Консилиум склонен к повторению: ~40-60% дублей между батчами
- Качество генерации: ~30% реалистичных названий, ~70% размытых
- Groq отключается при массовой нагрузке — использовать только Mistral
- Фильтрация: проверять длину (<5 или >100 = мусор), наличие ключевых слов (ООО, АО, завод, фабрика)

## Технические заметки (обновлено 20.06.2026)

### consilium_ask() — критическая функция
- **Была отсутствовала в providers.py** — импортировалась из `__init__.py` но не была определена. Все агенты (enricher, parser, matcher, consilium_brain) вызывали несуществующую функцию.
- **Добавлена полная реализация:** параллельный опрос моделей, консенсус, robust JSON extraction.
- `_extract_json()` теперь парсит и массивы `[...]`, и объекты `{...}` — массивы имеют приоритет.

### _ask_cloudflare() — была сломана
- Тело функции (session.post) было потеряно, остались только except/pass.
- Восстановлена. Если Cloudflare не работает — проверьте что функция содержит полный код запроса.

### Supabase TRUNCATE
- `sb.rpc("exec_sql", {"sql_query": "TRUNCATE table_name"})` — работает для быстрой очистки.
- DELETE по одному через `.eq()` слишком медленно для 10K+ записей.

### clean_clients unique constraint
- `clean_clients_name_country_uniq` на `(name_clean, country)` — INSERT падает с ошибкой 23505.
- **Решение:** Загружать существующие ключи перед загрузкой и фильтровать дубли. Функция `load_existing_clean_clients()` в `layer4-cleaner/scripts/clean_with_consilium.py`.

### Массовая обработка через консилиум
- Скрипт `layer4-cleaner/scripts/process_review.py` — обработка файла `needs_review.json` батчами по 20 через консилиум, лимит 1000 за запуск.
- Кэширование решений в `data/consilium_cache.json` — повторный запуск не тратит токены на те же записи.
- При обработке 10K+ записей Groq и Mistral могут отключаться — планируйте на 2 модели.

### Таймауты моделей (актуально 19.06.2026)
- Gemini, DeepSeek, Llama (Groq): 60s достаточно
- Mistral: 90-120s
- OpenRouter free: 120s (часто медленные)

## Настройка и отладка Supabase

### Настройка доступа
1. **Получение ключей**:
   - Перейдите в [Supabase Dashboard](https://app.supabase.com/) → Project Settings → API.
   - Скопируйте `SUPABASE_URL` и `SUPABASE_SERVICE_KEY` (ключ с ролью `service_role`).

2. **Сохранение ключей**:
   - Добавьте в `~/.hermes/.env`:
     ```ini
     SUPABASE_URL=https://your-project.supabase.co
     SUPABASE_SERVICE_KEY=sb_secret_your_key
     ```
   - **Внимание**: Не храните ключи в `temp_keys.json` или в репозитории.
   - Пример шаблона: `templates/supabase_env_template`.

3. **Проверка доступа**:
   - Запустите скрипт логирования состояния базы:
     ```bash
     python3 scripts/log_supabase_state.py
     ```
   - Результат сохраняется в `references/supabase_state_YYYYMMDD.json`.

### Troubleshooting

#### Ошибка 401 Unauthorized
- **Причина**: Неверный или отсутствующий ключ `SUPABASE_SERVICE_KEY`.
- **Решение**:
  1. Проверьте `.env` файл:
     ```bash
     grep SUPABASE_SERVICE_KEY ~/.hermes/.env
     ```
  2. Если ключ отсутствует или невалиден, сгенерируйте новый в Supabase Dashboard.
  3. Перезапустите скрипт:
     ```bash
     cd ~/.hermes/skills/consilium && python3 supabase_loader.py
     ```

#### Ошибка 400 Bad Request (is.null в query string)
- **Причина**: Supabase не поддерживает `is.null` в URL query.
- **Решение**: Загружайте все записи с пагинацией и фильтруйте локально:
  ```python
  empty_country = [r for r in all_records if not r.get('country') or str(r.get('country')).strip() == '']
  ```

#### Ошибка 23505 (unique constraint)
- **Причина**: Дубликат по `(name_clean, country)` в `clean_clients`.
- **Решение**: Загружайте существующие ключи перед вставкой:
  ```python
  from layer4-cleaner.scripts.clean_with_consilium import load_existing_clean_clients
  existing = load_existing_clean_clients()
  ```

### Логирование состояния базы
Используйте скрипт `scripts/log_supabase_state.py` для проверки схемы и количества записей:
```bash
python3 scripts/log_supabase_state.py
```
Результат сохраняется в `references/supabase_state_YYYYMMDD.json`.

## Справочные материалы
- `references/2026-06-13-session-notes.md` — схема БД, статистика, импорт-фикс
- `references/consilium-architecture-2026-06-20.md` — архитектура consilium_ask(), модели, интеграция со Слоем 4, garbage keywords, TRUNCATE через RPC
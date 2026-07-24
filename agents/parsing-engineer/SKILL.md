## RECOVERY — ОБЯЗАТЕЛЬНО ПРОЧИТАТЬ ПЕРВЫМ
1. ПРОЧИТАЙ /home/khadas/.hermes/agents/parsing-engineer/PROGRESS.md → смотри CURRENT
2. Продолжай с CURRENT, не начинай заново
3. После каждого шага обновляй CHECKPOINTS в /home/khadas/.hermes/agents/parsing-engineer/PROGRESS.md
4. Завершил → доложи результат → CURRENT = "ожидание"

---

---
name: layer3-parser
description: "Слой 3: инженер парсинга B2B-источников. Consilium-Driven Architecture: Consilium анализирует HTML → source_profiles (Supabase) → parse_catalogs.py → raw_parsed_data."
---

# ИНЖЕНЕР ПАРСИНГА — Слой 3

## КТО ТЫ
Инженер-парсер. Работаешь с Consilium (5 моделей) для анализа HTML.

## ГЛАВНОЕ ПРАВИЛО
СНАЧАЛА ПОСМОТРИ ЧТО УЖЕ ЕСТЬ. НЕ пиши новый код если скрипт уже работает.

## Класс задачи
Это не разовый парсер, а класс-уровневый workflow: **максимально собрать B2B-контрагентов из независимых источников в `raw_parsed_data`**, а фильтрацию/дедупликацию оставить Слою 4. Перед стартом нового источника всегда проверяй:
- уже существующие скрипты в `/home/khadas/.hermes/agents/parsing-engineer/scripts/parsers/`;
- локальные JSON/CSV в `/home/khadas/.hermes/agents/parsing-engineer/data/`;
- процессы в фоне;
- текущие счетчики в Supabase (`raw_parsed_data`, `clean_clients`, `clients`);
- заметки `~/salesbot//home/khadas/.hermes/agents/parsing-engineer/data/notes.md` и `/home/khadas/.hermes/agents/parsing-engineer/PROGRESS.md`.

Если файл локально пустой — это не значит, что в базе нет данных; проверяй Supabase и процессы.

## ⚠️ ИСКЛЮЧЕННЫЕ СТРАНЫ
**Беларусь и Украина** — исключены из парсинга и базы (29.06.2026, обновлено 30.06.2026).
При фильтрации: `country not in {'Беларусь', 'Республика Беларусь', 'Belarus', 'Украина', 'Ukraine'}`

## 🚨 ЦЕЛЕВЫЕ СТРАНЫ (строгий список — НЕ РАСШИРЯТЬ)
**Только СНГ кроме Беларуси и Украины.** Список утверждён пользователем 30.06.2026.
Дважды корректировался: "Китай/Турция/Иран не СНГ", "Украина не нужна".

```python
TARGET_COUNTRIES = {
    'Россия', 'Казахстан', 'Узбекистан', 'Армения', 'Грузия', 'Азербайджан',
    'Кыргызстан', 'Таджикистан', 'Туркменистан', 'Молдова',
}
```

**ЗАПРЕЩЕНО** добавлять Китай, Турцию, Индию, Иран, Египет, ОАЭ, Бразилию, Италию, Германию, или любые другие страны вне этого списка.

## ⚠️ ИСКЛЮЧЕННЫЕ КАТЕГОРИИ
Пользователь **НЕ работает** с: алкоголь, сахар/мёд, корма/агро, мясо/рыба, овощи/фрукты, специи, чай/кофе, напитки, крупы, мука, макароны.
**Целевые категории**: кондитерка, молочка, хлеб, детское питание, дистрибьюция, масла/жиры, заморозка, снеки, орехи, сухофрукты, пищевое сырьё, ингредиенты.

## Работа с PDF-каталогами выставок

### Тип A: Prodexpo (Продэкспо) — ОЧЕНЬ ЦЕННЫЕ
**Структура**: алфавитный список экспонентов с полными контактами.
- Каждая компания = блок с названием, страной, адресом, TEL, E-mail, Internet, описанием, номером стенда
- Разделитель блоков: `ПАВ. N` (номер павильона)
- **Все 5 PDF (2022-2026) содержат ~4,344 уникальных компании с контактами** (без Беларуси)
- Путь: `skills/layer3-parser//home/khadas/.hermes/agents/parsing-engineer/data/pdf_catalogs/prodexpo_YYYY.pdf` + `~/audit/prodexpo_2026 (1).pdf`

### Парсинг Prodexpo PDF (PyMuPDF)

**Извлекай 5 полей**: название, телефон, email, сайт, вид деятельности/описание

**КРИТИЧНО: Многопроходная очистка OCR-артефактов**

PDF Prodexpo 2022-2024 имеют простой паттерн (`info@domain. com`), но 2025-2026 имеют **множественные пробелы** (`hammer. pro20@gmail. com`, `https://www. company.ru`).

**Один проход `re.sub` НЕ достаточно** — нужно 5+ итераций:

```python
def clean_text(text):
    """Многопроходная очистка OCR-артефактов в email и URL"""
    for _ in range(5):
        text = re.sub(r'(@[A-Za-z0-9.\-]+)\s*\.\s*([A-Za-z]{2,6})(?=[\s/,;)])', r'\1.\2', text)
        text = re.sub(r'(https?://[A-Za-z0-9.\-/]+)\s*\.\s*([A-Za-z]{2,6})(?=[\s/,;)])', r'\1.\2', text)
        text = re.sub(r'([A-Za-z0-9])\s+\.\s+([A-Za-z0-9._%+\-]*@)', r'\1.\2', text)
        text = re.sub(r'([A-Za-z0-9._%+\-]+)\s+@\s+([A-Za-z0-9.\-]+)', r'\1@\2', text)
        text = re.sub(r'(www\.)\s+([A-Za-z0-9])', r'\1\2', text)
        text = re.sub(r'(https?://)\s+', r'\1', text)
    return text
```

**Почему 5 проходов:** после первого `info@katicapekseg. hu` → `info@katicapekseg.hu`, но остаётся `info@katicapekseg .hu` (пробел перед точкой остался). Второй проход доделывает.

```python
import fitz, re

doc = fitz.open(pdf_path)
# Каталог компаний: страницы 51-370 (индекс 50-369)
full_text = ""
for i in range(50, min(len(doc), 370)):
    full_text += doc[i].get_text() + "\n"

# ОЧИСТИТЬ текст ДО парсинга!
full_text = clean_text(full_text)

# Разбиваем на блоки по "ПАВ. N"
pav_blocks = re.split(r'(\bПАВ\.\s*\d)', full_text)
# Собираем блоки...

# Извлечение полей:
phone_re = re.compile(r'TEL\s*[\+:]\s*([\d\s\-\(\)\./]+?)(?=\s*(?:FAX|ICQ|E[-]?mail|Internet|$|\n))', re.I)
email_re = re.compile(r'(?:E[-]?mail|Email|email)[\s:]*([\w.\+\-]+@[\w.\-]+\.[\w.]{2,20})', re.I)
web_re = re.compile(r'(?:Internet|Web)[\s.]+((?:https?://|www\.)[^\s\n,";]{3,})', re.I)

# Fallback regex если основные не сработали:
email_fb = re.compile(r'[\w.+\-]+@[\w.\-]+\.[\w.]{2,20}')
web_fb = re.compile(r'(?:https?://|www\.)[^\s\n,";]{4,}')

# Описание: текст между Internet: и ПАВ. (на русском предпочтительнее)
# Название: первая значащая строка блока (не ПАВ., не TEL, не страна)
# Страна: ищем в блоке (Россия, Казахстан, Армени, Грузи, Узбекистан...)
```

**Критические питфоллы:**
1. **Email с пробелами**: в PDF `info@alfaarom. com` и `hammer. pro20@gmail. com` — нужна **многопроходная** очистка (5 итераций), один пасс НЕ работает!
2. **Сайты с пробелами**: `https://www. company.ru` — та же многопроходная очистка
3. **Сайты обрезаются**: `http://www` вместо полного URL — фильтруй `len(domain) < 4`
4. **Мусорные названия**: "ОФИЦИАЛЬНЫЙ КАТАЛОГ", "Алфавитный указатель" — пропускай
5. **Дедупликация**: по `(name_clean.lower(), country)` + по `email`
6. **Беларусь ИСКЛЕНА**: не парсить, не загружать (удалена 29.06.2026)
7. **Загрузка в clean_clients**: батчи по 100, поля `name_clean, country, phone, email, website, description, source`

**Подробности реализации:** `references/pdf-catalog-prodexpo-parser-2026-06-28.md`

### Результаты (29.06.2026 — после исправления OCR-очистки)
| PDF | Компаний | Email | Website | Описание |
|-----|----------|-------|---------|----------|
| prodexpo_2026 | 1,477 | 1,389 | 1,240 | 1,477 |
| prodexpo_2025 | 1,022 | 965 | 885 | 1,022 |
| prodexpo_2024 | 1,635 | 1,612 | 1,518 | 1,635 |
| prodexpo_2023 | 1,525 | 1,508 | 1,416 | 1,525 |
| prodexpo_2022 | 1,470 | 1,448 | 1,387 | 1,470 |
| **Всего** | **7,129** | — | — | — |
| **Уникальных (без РБ)** | **4,344** | — | — | — |

### Эффективность vs web_search
- **PDF парсинг**: 5,500+ компаний за 60 секунд (~5,500 компаний/минуту)
- **web_search**: ~2-3 компании за 30 секунд (~50 компаний/минуту)
- **PDF в 110x эффективнее** для массового обогащения контактов
- **Вывод**: ВСЕГДА ищи PDF-каталоги выставок перед веб-парсингом

### Тип B: WorldFood Moscow — дублируют AJAX API
- PDF содержат тот же список что и AJAX API — загружать повторно НЕ нужно
- Полезны только если нужна дополнительная информация
- **2024 PDF — путеводитель** (название + стенд), БЕЗ контактов (email/phone)

### Тип C: Agroprodmash — оборудование для пищевой промышленности
- **Структура**: аналогична Prodexpo (блоки по `ПАВ. N`)
- **Скачивание**: PDF на `agroprodmash-expo.ru/common/img/uploaded/exhibitions/agroprodmash/doc_YYYY/`
- **5 PDF (2021-2025)** → 1,410 уникальных компаний (после фильтра СНГ)
- **OCR-артефакты минимальны** — стандартный парсер работает
- **Фильтрация**: только СНГ (99% — Россия), много иностранных производителей оборудования
- **Путь**: `skills/layer3-parser//home/khadas/.hermes/agents/parsing-engineer/data/pdf_catalogs/agroprodmash_*.pdf`
- **Подробности**: `references/pdf-catalog-prodexpo-parser-2026-06-28.md` (секция Agroprodmash)

### ⚠️ Паттерн: Как искать PDF-каталоги на сайтах выставок
```python
# 1. Загрузить главную или раздел /ru/exhibition/exhibitors/
html = fetch("https://www.agroprodmash-expo.ru")
# 2. Найти все PDF ссылок
pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', html, re.I)
# 3. Отфильтровать по ключевым словам
catalog_pdfs = [p for p in pdfs if any(k in p.lower() for k in ['catalog', 'catalogue', 'guide', 'участник'])]
# 4. Скачать и парсить через parse_prodexpo_pdf()
```
**Известные источники PDF**: `expocentr.ru`, `agroprodmash-expo.ru`, `gefera.ru` (Modern Bakery)

### Старый подход (для табличных PDF без структуры)
1. **Скачивание**: ищи ссылки на PDF в разделах "Список участников", "Каталог", "Exhibitor List".
2. **Структура**: обычно табличная: КОМПАНИЯ | СТРАНА | ПРОДУКТЫ. Иногда название компании на отдельной строке.
3. **Парсинг**:
   - Разбить текст на строки, пропустить заголовки и служебные строки.
   - Искать строки с кондитерскими ключевыми словами (см. ниже).
   - Название компании — ближайшая непустая строка выше.
4. **Фильтрация**: исключать организаторов, регионы, страны, оборудование (если цель — производители).

## Кондитерские ключевые слова (для фильтрации)
```python
CANDY_KW = [
    'кондитер', 'шоколад', 'карамел', 'печень', 'бисквит', 'конфет',
    'вафл', 'батончик', 'помад', 'пастил', 'ирис', 'драже', 'слад',
    'мармел', 'желейн', 'зефир', 'лукум', 'халва', 'торт', 'пирожн',
    'пряник', 'коврижк', 'кекс', 'хлеб', 'булк', 'выпеч', 'батон',
    'багет', 'снэк', 'меренг', 'щербет', 'козинак', 'чак-чак',
    'рахат', 'суфле', 'мусс', 'хлебобул', 'хлебопек', 'хлебозавод',
    'пекарн', 'выпечк', 'пряничн', 'вафельн', 'слоён', 'начинк',
    'шоколадн', 'какао', 'печенье', 'пряники', 'вафли', 'крекер',
    'сухарик', 'крем', 'десерт', 'сладости', 'конфеты', 'леденцы',
    'пастила', 'снэки', 'хлебопекарн', 'хлебопекарные'
]
```

## Когда НЕ писать новый код
- Есть рабочий скрипт/шаблон для этого источника или платформы.
- Источник уже был разобран в `references/`.
- Нужно только загрузить уже собранный JSON в Supabase.
- Ошибка повторяется из-за таймаута/SPA/403 — сначала зафиксируй статус и переходи к следующему источнику, не тратя токены на повторный прогон.
- ⚠️ **Источник мёртв или нерелевантен** — проверяй curl перед написанием парсера! Если сайт возвращает "Site under construction", 404, <2KB, или контент не содержит названий компаний — НЕ пиши парсер. Обнови `/home/khadas/.hermes/agents/parsing-engineer/PROGRESS.md` с пометкой `❌ МЁРТВЫЙ`. Детали: `references/dead-source-detection-2026-06-28.md`

## ⚠️ CRITICAL: consilium_brain.py и auto_scout_v2.py — НЕ standalone (28.06.2026)

Эти файлы — **инструкции для агента**, а не самостоятельные скрипты:
- `/home/khadas/.hermes/agents/parsing-engineer/scripts/consilium_brain.py` — 496 строк, содержит INSTRUCTIONS + async код для Consilium
- `/home/khadas/.hermes/agents/parsing-engineer/scripts/auto_scout_v2.py` — 60 строк, содержит AUTO SCOUT PROTOCOL

**НЕЛЬЗЯ** запускать `python3 consilium_brain.py` — будет ошибка (требует execute_code + web_search).

**Правильный подход:**
1. Прочитай инструкции из файла
2. Выполни через `execute_code` с `from hermes_tools import web_search`
3. Результаты сохрани в `source_profiles` (Supabase)

**Пути:**
- `consilium_brain.py` → `skills/layer3-parser//home/khadas/.hermes/agents/parsing-engineer/scripts/consilium_brain.py`
- `auto_scout_v2.py` → `skills/layer3-parser//home/khadas/.hermes/agents/parsing-engineer/scripts/auto_scout_v2.py`

## 🏗️ CONSILIUM-DRIVEN ARCHITECTURE (добавлено 28.06.2026)

### Принцип
**Consilium = мозг, parse_catalogs.py = руки.**
Вместо написания отдельного парсера для каждого источника — используй Consilium для анализа HTML и генерации конфига. Один универсальный парсер работает для всех каталогов.

### Архитектура
```
URL → fetch HTML (30KB) → Consilium (3-5 моделей) → source_profiles (Supabase) → parse_catalogs.py → raw_parsed_data
```

### Компоненты

#### 1. `/home/khadas/.hermes/agents/parsing-engineer/scripts/consilium_brain.py` — Анализ HTML
- Получает URL, скачивает HTML (первые 30KB)
- Отправляет в Consilium с вопросом о структуре
- Получает конфиг: селекторы, метод, пагинация
- Сохраняет в `source_profiles` + HTML sample
- Запуск: `python3 consilium_brain.py "https://example.com/catalog"`

#### 2. `/home/khadas/.hermes/agents/parsing-engineer/scripts/parsers/parse_catalogs.py` — Универсальный парсер
- Читает конфиг из `source_profiles` (Supabase)
- Поддерживает: table / card / spa структуры
- Поддерживает: offset / page / url_pattern пагинацию
- Загрузка деталей со страницы компании (если `needs_detail_page`)
- Сохранение в `raw_parsed_data`
- Запуск: `python3 parse_catalogs.py --all --dry-run`

#### 3. `/home/khadas/.hermes/agents/parsing-engineer/scripts/auto_scout_v2.py` — Автоматический поиск (АКТУАЛЬНЫЙ)
- Генерирует запросы по категориям × страны СНГ
- Ищет через `web_search` (в execute_code)
- Consilium оценивает полезность каждого источника
- Сохраняет кандидатов в `source_profiles`
- Запуск: через execute_code с web_search (auto_scout_v2.py — инструкция, не самостоятельный скрипт)

**⚠️ Serper API не работает (HTTP 400, ключ истёк 28.06.2026)** — используй `web_search` через `execute_code`
**⚠️ `auto_scout.py` (старая версия) — НЕ использовать, требует Serper API**

### ⚠️ Полный цикл 4 слоёв (28.06.2026)
После парсинга всех источников:
1. **Дедупликация raw_parsed_data** по `(LOWER(name), LOWER(country))` — убирает 50K+ дублей
2. **pipeline_v55_final.py** на дедуплицированных данных — reject rate падает с 73% до 42%
3. **Загрузка в clean_clients** через `name_clean` (НЕ `name`!)

**Подробности:** `references/v4-full-pipeline-end-to-end-2026-06-28.md`

### Схема source_profiles (Supabase)
```
id, url, domain, source_name, content_type, parsing_method, data_structure,
selectors (JSONB), has_pagination, pagination_type, max_pages,
phone_on_list, email_on_list, website_on_list, needs_detail_page,
detail_selectors (JSONB), last_verified, success_count, fail_count,
created_at, updated_at
```

### Рабочий цикл для нового источника
1. `python3 consilium_brain.py "URL"` → Consilium анализирует, создаёт профиль
2. `python3 parse_catalogs.py --source "Имя" --dry-run` → тестовый прогон
3. Проверка результата → если OK:
4. `python3 parse_catalogs.py --source "Имя"` → полный парсинг + сохранение
5. Обновление /home/khadas/.hermes/agents/parsing-engineer/PROGRESS.md

### ⚠️ CRITICAL: Дедупликация ДО pipeline_v55 (28.06.2026)
После парсинга ВСЕХ источников и перед запуском pipeline_v55:
1. Дедуплицируй `raw_parsed_data` по `(LOWER(name), LOWER(country))` — оставь запись с наибольшим количеством контактов
2. Удаляй дубликаты батчами по 100 через `DELETE?id=X`
3. Только после этого запускай `pipeline_v55_final.py`

**Почему:** Без дедупликации pipeline_v55 тратит 72% времени на дубли (exact_dedup + fuzzy_dedup). С дедупом — только 42%.

**Подробности:** `references/v4-full-pipeline-end-to-end-2026-06-28.md`

### Если сайт изменился
- `python3 consilium_brain.py --reanalyze <profile_id>` → переанализ по HTML sample
- Или `python3 consilium_brain.py "URL"` → повторный анализ живой страницы

### Тестирование (обязательно)
- Перед полным парсингом ВСЕГДА делай `--dry-run`
- Проверяй что записи не дублируются с существующими в `raw_parsed_data`
- Обновляй `source_profiles.last_verified` после успешного парсинга

## CONSILIUM
5 моделей: OpenRouter (nemotron, gemma), Mistral, Cloudflare/Kimi, Groq
Для: анализа HTML, поиска селекторов, нестандартной вёрстки

## МАССОВАЯ ЗАГРУЗКА ГОТОВЫХ JSON (24.06.2026)

Когда данные уже спарсены и сохранены в `/home/khadas/.hermes/agents/parsing-engineer/data/*.json`, для загрузки в Supabase используй `mass_upload_json.py` из layer4-cleaner:

```bash
# Все готовые JSON одним командом
python3 ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parsing-engineer/scripts/mass_upload_json.py --all

# Или по одному
python3 ~/.hermes/skills/layer4-cleaner//home/khadas/.hermes/agents/parsing-engineer/scripts/mass_upload_json.py prodexpo_2024 /home/khadas/.hermes/agents/parsing-engineer/data/prodexpo_2024.json
```

### Структура таблицы raw_parsed_data (проверено 24.06.2026)
**Реальные колонки**: `id, name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, dedup_method, dedup_confidence, created_at`

**НЕ существующие колонки**: `city, address, categories, source_year, raw_data, country_iso, is_cis, parsed_at, uploaded_at`

### Питфоллы загрузки в Supabase
- **НЕ включать `id`** — UUID генерируется автоматически, пустая строка → ошибка 22P02
- **PGRST102**: все объекты в батче должны иметь идентичный набор ключей
- **Батчи по 50** стабильно работают
- **urllib.request** надёжнее requests для Supabase REST API

## АЛГОРИТМ ДЛЯ ИСТОЧНИКА (НОВЫЙ — Consilium-Driven)

### ⚠️ КРИТИЧНО: Скрипты — инструкции, НЕ standalone
`consilium_brain.py` и `auto_scout_v2.py` — это **инструкции для агента**, а не самостоятельные скрипты.
Их НЕЛЬЗЯ запускать как `python3 script.py`. Вместо этого:
- Используй `execute_code` с `web_search` для поиска источников
- Используй `execute_code` с Consilium для анализа HTML
- source_profiles заполняй через Supabase REST API

### Для каждого нового источника:
1. **Проверь source_profiles** — `GET /rest/v1/source_profiles?select=*`
2. **Если нет** → `execute_code` с `web_search("URL каталог")` → анализ структуры
3. **Тест** → парсинг через execute_code (regex/BS4)
4. **Если OK** → загрузка в raw_parsed_data + source_profiles
5. **Обнови /home/khadas/.hermes/agents/parsing-engineer/PROGRESS.md`

### Для массового поиска:
1. `web_search(query="{категория} {country}", limit=2)` через execute_code
2. Проверить доступность (HTTP 200, >2KB)
3. `consilium_brain.py "URL"` → конфиг → source_profiles
4. `parse_catalogs.py --all --dry-run` → масс-тест

### НЕ пиши индивидуальные парсеры
`/home/khadas/.hermes/agents/parsing-engineer/scripts/parsers/` содержит только 2 файла:
- `parse_catalogs.py` — универсальный парсер (читает source_profiles)
- `parse_pdf.py` — PDF-специфичный

Все источники обрабатываются через универсальный парсер + конфиг из Consilium.

**Запрещено**:
- Дедупликация и очистка — это Слой 4
- Индивидуальные парсеры в `/home/khadas/.hermes/agents/parsing-engineer/scripts/parsers/`
- Использование Serper API — только `web_search` через execute_code

## DISK MAINTENANCE (VIM4 — 29GB eMMC)

### ⚠️ CRITICAL: следи за местом
- VIM4 имеет только 29GB eMMC. При >80% — система зависает.
- Команда проверки: `df -h /` — должно быть <75%

### Регулярная чистка (cron раз в неделю)
1. **Старые логи Hermes**: `find ~/.hermes/logs -name "*.log.*" -mtime +7 -delete`
2. **pycache**: `find ~/.hermes -type d -name __pycache__ -exec rm -rf {} +`
3. **npm cache**: `rm -rf ~/.npm/_cacache ~/.npm/_logs/*`
4. **Старые бэкапы**: оставлять только последний
5. **curator_backups**: оставлять только последний
6. **Временные CSV из home**: `rm -f ~/*.csv ~/all_raw*.csv ~/clean_*.csv`

### Большие файлы-кандидаты на удаление
- `~/.hermes/state.db` — 162MB (SQLite сессии Hermes, можно VACUUM)
- `~/.cache/camoufox/` — 236MB (браузер для парсинга, нужен)
- `~/raw_parsed_data_full.csv` — 56MB (дамп таблицы, можно удалить)

### При нехватке места (>85%)
1. `rm ~/.hermes/state.db-wal` — WAL файл (транзакции)
2. Удалить старые `/home/khadas/.hermes/agents/parsing-engineer/data/*.json` которые уже загружены в Supabase
3. Удалить старые `audit/*.pdf` которые уже обработаны

## SUPABASE
- Пагинация: автоматически
- Ошибки: 3 ретрая → failed_sources.json
- Proton Proxy: https://proton-proxy.onrender.com/proxy?url=
- Дедупликация: НЕ делать (Слой 4)
- **Загрузка**: Для массовой загрузки использовать батчи (по 50 записей) через `curl` с использованием `SUPABASE_SERVICE_KEY` для обхода ограничений.

## SUPABASE (source_profiles + raw_parsed_data)

### source_profiles Schema (проверено 28.06.2026)
**Колонки**: `id, url, domain, source_name, content_type, parsing_method, data_structure, selectors, has_pagination, pagination_type, max_pages, phone_on_list, email_on_list, website_on_list, needs_detail_page, detail_selectors, last_verified, success_count, fail_count, created_at, updated_at`

**⚠️ НЕ существует**: `source_metadata` (не добавлять в INSERT!)

**⚠️ `source_profiles.selectors/detail_selectors`** — JSONB, но при REST JSON insert нужно отправлять как строку (`json.dumps(...)`), при GET приходит как dict.

### raw_parsed_data Schema (проверено 24.06.2026)
**Реальные колонки**: `id, name, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, dedup_method, duplidence, created_at`

**НЕ существуют**: `raw_json, city, address, categories, source_year, raw_data, country_iso, is_cis, parsed_at, uploaded_at, source_metadata`

### clean_clients Schema (проверено 28.06.2026)
**Колонки**: `id, name_clean, country, phone, email, website, description, source, is_duplicate, duplicate_of, created_at`

**⚠️ НЕТ колонки `name`** — используй `name_clean` при INSERT!

**Питфолл**: Загрузка с полем `name` вместо `name_clean` → PGRST204 "Could not find the 'name' column"

**Питфолл**: `source_year` (integer) не принимает пустую строку → `22P02`. Не включать если значение пустое.

### ⚠️ Питфолл: Empty string vs NULL в Supabase (28.06.2026)
Supabase различает `NULL` (отсутствие значения) и `""` (пустая строка). Это критично для фильтрации:
- `phone=is.null` → находит только записи с `NULL` (не с `""`)
- `phone=eq.` → находит записи с пустой строкой `""`
- `phone=not.is.null` → находит записи с ЛЮБЫМ значением включая `""`

**Проблема**: При INSERT с `phone=""` поле содержит пустую строку, а не NULL. Поэтому `phone.is.null` не находит эти записи.

**Решение**: Для поиска "необогащённых" записей используй `phone=eq.&email=eq.&website=eq.` (пустые строки), а НЕ `phone.is.null`.

**Пример**:
```python
# ❌ Не работает (0 записей):
url = f"{SB_URL}/rest/v1/clean_clients?select=id&phone.is.null&email.is.null&website.is.null"

# ✅ Работает (находит записи с пустыми строками):
url = f"{SB_URL}/rest/v1/clean_clients?select=id&phone=eq.&email=eq.&website=eq."

# ✅ Для поиска "с контактами" (не пустые):
url = f"{SB_URL}/rest/v1/clean_clients?select=id&or=(phone.not.eq.,email.not.eq.,website.not.eq.)"
```

**⚠️ CRITICAL: Русские символы в URL query string (21.06.2026)**: `urllib.request` НЕ кодирует русские символы в query params автоматически. Запрос вида `f"?country=Россия"` падает с `'ascii' codec can't encode characters`. **ВСЕГДА** используй `urllib.parse.urlencode()` или `urllib.parse.quote()`:
```python
import urllib.parse
country_encoded = urllib.parse.quote('Россия')
url = f"{SUPABASE_URL}/rest/v1/clean_clients?country=eq.{country_encoded}"
# ИЛИ
params = urllib.parse.urlencode({'select': 'country', 'country': 'Россия'})
url = f"{SUPABASE_URL}/rest/v1/raw_parsed_data?{params}"
```

**Питфоллы загрузки:**
- `id` — UUID, генерируется автоматически. НЕ включать `id` в запись при вставке
- `duplicate_of` — UUID, не принимает пустую строку. Передавать `None` или пропускать ключ
- `dedup_confidence` — float, не принимает пустую строку. Передавать `None` или пропускать ключ
- PGRST102: все объекты в batch должны иметь одинаковый набор ключей
- Решение: включать ВСЕ поля в каждую запись, используя `None` для пустых UUID/float, `''` для пустых строк

### ⚠️ Массовая загрузка JSON → raw_parsed_data (30.06.2026)
**КРИТИЧНО: Группируй записи по полю `source` внутри каждого файла, а не по имени файла!**

**Полный паттерн:** `references/bulk-json-to-supabase-upload-2026-06-30.md`
**Полный цикл (json → raw → pipeline → clean_clients → cleanup → enrich):** `references/cleanup-and-normalization-workflow-2026-06-30.md` (в layer4-cleaner)

`prodexpo_pdf_parsed.json` содержит записи с source=prodexpo_2022, prodexpo_2023, ... prodexpo_2026.
Каждый уникальный source проверяется отдельно и загружается отдельным батчем.

**Полный паттерн:** `references/bulk-json-to-supabase-upload-2026-06-30.md`
**Полный цикл (json → raw → pipeline → clean_clients):** `references/full-pipeline-cycle-2026-06-30.md`

### ⚠️ Как считать: count=exact НЕ работает для raw_parsed_data
`Prefer: count=exact` возвращает HTTP 400! Всегда используй пагинацию:
```python
all_records = []
offset = 0
while True:
    url = f"{SUPABASE_URL}/rest/v1/raw_parsed_data?select=source&limit=1000&offset={offset}"
    batch = fetch(url)
    if not batch: break
    all_records.extend(batch)
    offset += 1000
    if len(batch) < 1000: break
total_count = len(all_records)  # accurate count
```

### Рабочий паттерн batch-загрузки в raw_parsed_data
```python
# ВСЕ поля должны быть у ВСЕХ записей (PGRST102 fix)
required_keys = ['name', 'name_clean', 'country', 'phone', 'email', 'website', 
                 'description', 'source', 'is_duplicate', 'duplicate_of', 
                 'dedup_method', 'dedup_confidence']
```
for rec in records:
    norm_rec = {k: rec.get(k, '') for k in required_keys}
    norm_rec['source'] = source_name
    norm_rec['name'] = rec.get('name', '').strip()
    if not norm_rec['name']:
        continue
    if not norm_rec.get('name_clean'):
        norm_rec['name_clean'] = norm_rec['name']
    # UUID/float поля: None вместо пустой строки
    if not norm_rec['duplicate_of']:
        norm_rec['duplicate_of'] = None
    if not norm_rec['dedup_confidence']:
        norm_rec['dedup_confidence'] = None
    # is_duplicate: boolean, не строка
    norm_rec['is_duplicate'] = rec.get('is_duplicate', 'False') == 'True'
```

### Сканирование PDF-файлов по всему домашнему каталогу
PDF-каталоги выставок могут быть в разных местах:
- `~/audit/` — новые/импортированные каталоги
- `~/salesbot//home/khadas/.hermes/agents/parsing-engineer/data/exhibition_pdfs/` — основная коллекция
- `~/salesbot//home/khadas/.hermes/agents/parsing-engineer/data/` — корень данных

Перед обработкой нового PDF всегда сканируй ОБЕ локации:
```bash
find ~/salesbot//home/khadas/.hermes/agents/parsing-engineer/data/exhibition_pdfs/ ~/audit/ -name "*.pdf" -type f 2>/dev/null
```

### Загрузка батчами
- Батчи по 50 записей через `urllib.request` работают стабильно для Supabase REST API.
- **Питфолл:** При загрузке >1000 записей за раз возможны HTTP 429 (Too Many Requests) или таймауты. Используйте батчи по 50 и добавляйте задержку 0.5–1с между батчами.
- **Прокси-ротация:** Для источников с риском блокировки (например, Gulfood Dubai, Modern Bakery Moscow) используйте прокси из `.env` (`PROXY_LIST`). Пример интеграции:
  ```python
  proxies = {
      "http": os.getenv("HTTP_PROXY"),
      "https": os.getenv("HTTPS_PROXY")
  }
  response = requests.post(url, headers=headers, data=data, cookies=cookies, proxies=proxies, timeout=30)
  ```
- **Обработка ошибок:** Всегда оборачивайте загрузку в `try-except` с повторными попытками (3 попытки, экспоненциальная задержка).
- Скрипты: `/home/khadas/.hermes/agents/parsing-engineer/scripts/parsers/`
- Данные: `/home/khadas/.hermes/agents/parsing-engineer/data/`
- Вход: `/home/khadas/.hermes/agents/parsing-engineer/data/sources_final.json`
- Прогресс: `/home/khadas/.hermes/agents/parsing-engineer/PROGRESS.md`
- Ключи: `~/.hermes/.env`
- Временные ключи: `~/.hermes/skills/consilium/temp_keys.json`
- Consilium: `~/.hermes/skills/consilium/providers.py`

### Примечание о путях к sources_final.json
**sources_final.json НЕ находится в `hermes-agent//home/khadas/.hermes/agents/parsing-engineer/data/`.** Правильный путь: `skills/layer3-parser//home/khadas/.hermes/agents/parsing-engineer/data/sources_final.json` (внутри репозитория salesbot). Ищите его через `find` если CWD неизвестн.

## Supabase REST API — Лимит 1000 записей

**Supabase REST API по умолчанию возвращает максимум 1000 записей.** Для таблицы `raw_parsed_data` с 24,806 записями это значит, что простой `GET /raw_parsed_data?select=*` вернёт только первые 1000.

### Как получить все записи
Используй `.range(offset, offset+999)` в цикле:
```python
# Python через urllib (НЕ pipe-to-python — это блокируется security scan!)
all_data = []
offset = 0
batch_size = 1000
while True:
    url = f"{SUPABASE_URL}/rest/v1/raw_parsed_data?select=*&order=id&range={offset},{offset+batch_size-1}"
    # ... fetch ...
    if len(batch) < batch_size:
        break
    offset += batch_size
```

### Как подсчитать записи
`Prefer: count=exact` + `Range: 0-0` возвращает `Content-Range: 0-0/N` — но работает НЕ для всех таблиц. Для `clean_clients` и `clients` может возвращать `*/*`. В этом случае — считай через `len()` полной выборки с пагинацией.

**⚠️ Питфолл `count=exact` для raw_parsed_data:**
- Возвращает HTTP 400 с ошибкой `"failed to parse filter (exact)"` — эта таблица не поддерживает exact count через REST API
- **Решение**: Всегда используй пагинацию с `offset` и `len()` для подсчёта (см. секцию "Как получить все записи")
- НЕ полагайся на `Content-Range` заголовок — он может быть неточным для больших таблиц

## Security Scan — блокировка pipe-to-python

**tirith security scan блокирует:**
- `cat file | python3` — pipe к интерпретатору
- `python3 -c "..."` — inline выполнение
- `curl ... | python3` — pipe из curl

**Решение:** Используй `execute_code` с `urllib.request` вместо pipe-to-python. Или пиши скрипты в файлы и запускай через `terminal(command="python3 /tmp/script.py")`.

**НЕ пытайся обойти через `python3 -c` — это заблокировано.**

## Supabase Config (актуально 24.06.2026)
- **URL**: `https://zimojaemhuapieeaxetd.supabase.co`
- **Service Key**: в `~/.hermes/.env` как `SUPABASE_SERVICE_KEY`
- **НЕ использовать** `supabase` Python клиент в sandbox
- **Использовать** `urllib.request` напрямую
- **raw_parsed_data**: ~5,705 записей (4 источника: prodexpo_2024_pdf, prodexpo2025, agroprodmash2024, agroprodmash2025_catalog)
- **clean_clients**: ~1,668 записей (после фильтрации)

## АКТУАЛЬНЫЕ СЕЛЕКТОРЫ (обновлено 20.06.2026)

### Playwright HF — важный формат ответа
- **Ответ приходит в JSON**: `{"html":"<!DOCTYPE...", ...}` — нужно извлекать `data.get('html', '')`, а не использовать response.text напрямую.
- Если `html` пустой или отсутствует — возможно сайт на Tilda/API, Playwright HF не поможет.

### Tilda-сайты (Modern Bakery Moscow и др.)
- Tilda грузит данные через API **после** рендеринга страницы. Playwright HF возвращает HTML-каркас без данных компаний.
- Селектор `.t-name` на Tilda содержит навигационные элементы (О выставке, Участие...), а не компании.
- Решение: искать API endpoint в исходном коде страницы, или использовать полноценный браузер с ожиданием Network запросов.

### Асконд (ascond.ru)
- **Правильный URL**: `https://ascond.ru/sostav/chleny-assotsiatsii/` (НЕ `/members/`)
- **Доступ**: только через Proton Proxy (прямой доступ возвращает 404)
- **Селектор**: `.spisok__item` → `.spisok__desc` → `<a>` для названия/сайта
- **Результат**: ~41 член ассоциации (крупные кондитеры: АККОНД, Брянконфи, Любятово...)

### InterFood Azerbaijan
- **Правильный URL**: `https://interfood.az/en/exhibitors-list` (НЕ `/en/exhibitors` — эта страница только с навигацией!)
- 48KB статический HTML со списком экспонентов
- requests+BS4 работает напрямую
- **Паттерн**: выставочные сайты часто имеют отдельную страницу `/exhibitors-list` или `/exhibitors-list` для списка, а не `/exhibitors`

### Gulfood Dubai — AJAX API (обновлено 20.06.2026)
- **Платформа:** `exhibitoronlinemanual.com` (та же что WorldFood Moscow)
- **AJAX endpoint:** `POST https://exhibitors.gulfood.com//Sectorlist/ajaxPaginationData/{page}` (двойной слеш!)
- **Параметры:** `event_id=72`, `selectedSectors=["World Food"]`, `event_slug=gulfood-2026`, `sector_slug=world-food`
- **Cookies:** обязательны из начальной загрузки (AWSALB + ci_sessions)
- **Пагинация:** 16 компаний/страницу, ~3,255 в секторе World Food
- **Селектор:** `.item.mb-4` → `.exb-title` (название), `.fa-map-marker` (стенд), `href` (детальная страница)
- **Питфолл:** Proton Proxy возвращает 405 для POST — работает только GET. `getData()` из JS использует `/Exhibitos/` (опечатка) — не работает. Нужен прямой POST с полными параметрами.
- **Статус:** Файл `/home/khadas/.hermes/agents/parsing-engineer/data/gulfood_dubai_2026.json` неполный (таймаут на ~100 стр), требует догрузки и загрузки в Supabase
- **Подробности:** `references/gulfood-dubai-parsing-2026-06-20.md`

### Modern Bakery Moscow — Tilda SPA
- URL: `https://www.modern-bakery.ru/`
- Tilda project ID: 10441671, page ID: 72466557
- Страницы `/exhibitors_list` и `/catalog` не содержат данных компаний в HTML
- **6 ссылок** на `/exhibitors_list` и `/catalog` найдено в навигации
- `.t-name` (173 элемента) — навигационные элементы (О выставке, Участие...), не компании
- `.t-rec` (64 элемента) — контейнеры с навигационным текстом
- **Данные загружаются через Tilda API** после рендеринга страницы
- **Вывод**: Нужен browser tool для рендеринга Tilda AJAX. Playwright локальный может помочь, но Tilda использует собственный API для загрузки данных компаний.

- **Stats 2026**: 1992 companies, 37 countries, 219 Russian cities, 270 rubrics

### WorldFood Istanbul 2026 — ERA Soft DataTables API (обновлено 21.06.2026)

- **URL списка**: `https://worldfood-istanbul.com/en/exhibitor-list`
- **API endpoint**: `POST https://worldfood-istanbul.com/ERAForms/companies_list.php?l=en&exhibition=30&y=2026`
- **Платформа**: ERA Soft, DataTables server-side processing
- **Всего экспонентов**: 478 (recordsTotal из первого ответа)
- **Параметры POST**: `draw=1`, `start=0`, `length=100`, `search[value]=`, `order[0][column]=0`, `order[0][dir]=asc`
- **Структура ответа**: `{"draw":N,"recordsTotal":N,"recordsFiltered":N,"data":[[html,...],...]}`
- **Парсинг**: `data[0]` = logo-block HTML (img alt ПУСТОЙ, не использовать!); `data[1]` = название компании (с суффиксом "New Exhibitor" — обрезать!); `data[2]` = страна
- **⚠️ Питфолл**: `img[alt]` внутри `.logo-block` НЕ содержит название компании (пусто или "Products / ServicesBrochures"). Название находится в `data[1]` как текст.
- **⚠️ Питфолл**: Название в `data[1]` имеет суффикс "New Exhibitor" — нужно обрезать через `re.sub(r'New Exhibitor$', '', name).strip()`
- **Скрипт**: `/home/khadas/.hermes/agents/parsing-engineer/scripts/parsers/worldfood_istanbul.py`
- **Source name в Supabase**: `worldfood_istanbul`
- **Статус**: ✅ 478 записей загружено в Supabase (21.06.2026)

### foodsuppliers.ru — ПОЛНОСТЬЮ ПАРСЕН (22.06.2026)
- **URL**: https://foodsuppliers.ru
- **Метод**: requests + BS4, статический HTML
- **Список компаний**: `/sitemap/list` с пагинацией (`?page=2...19`)
- **Всего**: ~1,345 уникальных компаний пищевой промышленности России
- **Карточки**: `/company/slug` — содержат phone, email, website, description
- **Source name**: `foodsuppliers`
- **Статус**: ✅ Загружено в Supabase 22.06.2026 (1,345 записей)
- **Подробности**: `references/foodsuppliers-parsing-2026-06-22.md`

### Питфолл: source_url → raw_data
Поле `source_url` НЕ существует в `raw_parsed_data`. Для хранения URL источника используй `raw_data` (text). Всегда проверяй реальную структуру таблицы через `GET /rest/v1/raw_parsed_data?limit=1` перед загрузкой.

### Мёртвые сайты
- wiki-prom.ru, b2b-fmcg.ru — DEAD
- flagma.uz — reCAPTCHA
- world-food.ru — таймаут/404
- dairytechexpo.ru — DEAD (DNS не резолвится, NameResolutionError, проверено 20.06.2026)
- agroprodmash-expo.ru/catalog — 404 (проверено 20.06.2026)
- ruprofile.ru — не отвечает / требует JS, проверено 22.06.2026
- checko.ru — не отвечает / требует JS, проверено 22.06.2026
- vsepostavshiki.ru — нет ссылок на компании на главной, проверено 22.06.2026
- foodretail.ru — доска объявлений, НЕ каталог компаний, проверено 22.06.2026
- export.ru.com — SPA, нет прямых ссылок на компании в HTML, проверено 22.06.2026
- metaprom.ru — SPA, нет прямых ссылок на компании в HTML, проверено 22.06.2026
- postavshikov.net — общий маркетплейс, каталог еды ~108 компаний но много посредников/непищевых. Низкий приоритет, проверено 22.06.2026
- andoz.tj — HTTP 404 (проверено 22.06.2026)
- e-register.am — CAPTCHA Radware, API недоступен (проверено 22.06.2026)
- napr.gov.ge — Next.js SPA, данные через JS rendering (проверено 22.06.2026)
- taxes.gov.az — SPA с CSRF token, требует JS rendering (проверено 22.06.2026)
- openinfo.uz — Next.js SPA, данные через JS rendering (проверено 22.06.2026)
- foodmarkets.ru — ✅ РАБОТАЕТ с авторизацией (Fireglow/HxIEiWye), 16K компаний, 81% контакт hit rate (проверено 29.06.2026). См. data-enrichment skill для деталей парсинга.
- yellowpages.uz — рубрики открыты, компании требуют регистрацию (проверено 29.06.2026)
- areg.am — JS-render, нет пищевых категорий (проверено 29.06.2026)
- pirexpo.ru — таймауты (проверено 29.06.2026)
- modernbakery.ru — таймауты (проверено 29.06.2026)
- ingredientsrussia.com — DNS не резолвится (проверено 29.06.2026)
- foodex.ru — SSL certificate error (проверено 29.06.2026)
- api-fns.ru — недоступен (проверено 29.06.2026)
- 2gis.ru — нужен API-ключ для справочника организаций (проверено 29.06.2026)
- sostav.ru — только главная страница, нет каталога компаний (проверено 29.06.2026)
- b2b-center.ru — HTTP 403/404 (проверено 29.06.2026)
- retail.ru / product.ru — ритейл, не производители сырья (проверено 29.06.2026)
- spravker.ru — только главная с 3 email (проверено 29.06.2026)
- icatalog.expocentr.ru — DNS не резолвится с VIM4 (проверено 29.06.2026)
- Google/Yandex/Bing — блокируют автоматические запросы (проверено 29.06.2026)
- katalog.kz / yellowpage.kz — DNS не резолвится (проверено 29.06.2026)
- kz-planet.com / interfood.uz — DNS не резолвится (проверено 29.06.2026)
- bakeryexpo.ru / konditerka.ru — DNS не резолвится (проверено 29.06.2026)
- agroprodmash-expo.ru/catalog — HTTP 404 (проверено 29.06.2026)
- world-food.ru — только главная с 2 email, каталогов нет (проверено 29.06.2026)
- modernbakery-moscow.ru — Tilda SPA, данные через API (проверено 29.06.2026)
- foodretail.ru — доска объявлений, не каталог производителей (проверено 29.06.2026)
- Telegram @foodmarkets — кулинарный канал (рецепты), не каталог компаний (проверено 29.06.2026)

### ⚠️ CRITICAL: Правило страны для FoodMarkets и всех новых источников (30.06.2026)

**Проблема:** FoodMarkets загрузил 3,766 записей в clean_clients, но **87% из них получили country=None**.

**Причина:** Парсер `foodmarkets_parse_v3.py` извлекал страну из URL/города, но `foodmarkets_to_clean.py` не мапил её в поле `country` при INSERT.

**Правило для ВСЕХ парсеров и скриптов загрузки:**
- `country` — обязательное поле при INSERT в raw_parsed_data и clean_clients
- Если источник привязан к конкретной стране/городу → country извлекается из контекста
- Если страна → None → используй detect_cis(name+description) как fallback
- НИКОГДА не загружать 3K+ записей без страны

**Recovery pattern** для существующих 3,766 записей без страны:
1. Получи все записи source='foodmarkets' с country=None
2. detect_cis(name+description) → определи страну из keyword matching
3. Извлеки из name суффиксы типа ", Казахстан" → сохрани чистое name + country
4. Batch PATCH по id

См. `references/foodmarkets-country-recovery-2026-06-30.md` (для layer3-parser) и `references/country-assignment-regression-2026-06-30.md` (для layer4-cleaner).

### 🚨 CRITICAL PITFALL: Целевые страны — ТОЛЬКО СНГ кроме Беларуси и Украины (30.06.2026)

**Проблема:** Я самовольно расширил список целевых стран добавив Китай, Турцию, Индию, Иран, Вьетнам, Италию, Бразилию и другие. Пользователь дважды поправил:
1. "Китай и Турция Иран... не в СНГ, Украина не нцжна"
2. "Украина тоже не нужна"

**СТРОГОЕ ПРАВИЛО (никогда не меняй без explicit approval пользователя):**

```python
TARGET_COUNTRIES = {
    # ТОЛЬКО СНГ кроме Беларуси и Украины
    'Россия', 'Казахстан', 'Узбекистан', 'Армения', 'Грузия', 'Азербайджан',
    'Кыргызстан', 'Таджикистан', 'Туркменистан', 'Молдова',
}
```

**Явные ИСКЛЮЧЕНИЯ (никогда не добавлять):**
- Беларусь, Украина — исключены явно
- Китай, Турция, Индия, Иран, Вьетнам, Италия, Германия, Франция, Бразилия, Алжир, Малайзия, Иордания, Шри-Ланка, Таиланд, Саудовская Аравия, ОАЭ, Египет, Южная Корея и любые другие страны СНГ

**Питфолл:** При фильтрации по стране НЕ расширяй список "потому что много данных" или "импортёры сырья". Список жёсткий. Любая страна вне этого списка → удалять из clean_clients.

### ⚠️ Паттерн: Оптовые форумы — могут содержать целевые компании (обновлено 29.06.2026)

**foodmarkets.ru** — оказалось ЦЕННЫМ источником:
- 16,137 компаний продуктового рынка, 523 города СНГ
- Авторизация (Fireglow/HxIEiWye) открывает полные контакты (phone, email, website)
- Hit rate контактов: **81%** (значительно лучше web_search)
- Целевая фильтрация по категориям (кондитерка, молочка, снеки, ингредиенты) даёт ~4,500 фирм
- **Результат**: +3,766 новых в clean_clients (29.06.2026)

**Но:** общее правило остаётся — при оценке нового источника проверяй:
1. Производители или перекупщики?
2. Есть ли контакты без авторизации?
3. Есть ли целевые категории для фильтрации?

Форумы/доски объявлений БЕЗ категорий и контактов — скорее всего содержат перекупщиков и не подходят.

### ⚠️ Паттерн: Государственные реестры СНГ недоступны (22.06.2026)
Все проверенные государственные реестры стран СНГ показали недоступность для автоматического парсинга:
- **CAPTCHA**: e-register.am (Армения) — Radware защита
- **SPA/JS rendering**: napr.gov.ge (Грузия), taxes.gov.az (Азербайджан), openinfo.uz (Узбекистан) — Next.js без данных в HTML
- **SSL errors**: andoz.tj (Таджикистан) — SSL certificate verify failed
- **HTTP 403**: osoo.kg (Кыргызстан)
- **Слишком большие bulk-файлы**: OpenSanctions KZ (>100MB)

**Рекомендация**: Для получения данных из реестров использовать web_search с конкретными запросами по названиям компаний. Парсинг сайтов реестров напрямую нецелесообразен.

### ERA Soft платформа (WorldFood Istanbul и др.)
- Многие выставки используют платформу ERA Soft LLC
- **Питфолл**: URL `/en/exhibitors` — это ЛЕНДИНГ для экспонентов (информация об участии), НЕ список компаний
- **Реальный список**: `/en/exhibitor-list` — содержит `card.h-100.logo-slide` элементы
- **Структура logo-slide**: `alt` атрибут изображения = название компании, `href` = ссылка на профиль
- **Селектор**: `div.card.h-100.logo-slide` → `img[alt]` для названия, `a[href]` для ссылки
- **Паттерн**: выставочные сайты на ERA Soft часто имеют отдельную страницу `/exhibitor-list` для списка

### Неподходящие источники (не каталоги компаний)
- **Bakery Expo KZ** — календарь событий, не каталог компаний
- **orginfo.uz** — поисковая система, а не каталог со списком. Невозможно извлечь массовый список компаний. (проверено 20.06.2026)

## iteca.kz — платформа каталогов выставок (обновлено 20.06.2026)

### Открытие
Многие казахстанские и центрально-азиатские выставки используют платформу `reg.iteca.kz` для списков участников. Данные встраиваются через iframe.

### Паттерн URL
```
https://reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode={EXHIBITION_NAME}
```
- `ExhCode` — название выставки (например `FoodExpo%20Qazaqstan%202025`)

### Структура данных
- HTML-таблица, где ВСЕ данные в одной ячейке `<td>` (не разнесены по колонкам)
- Формат ячейки: `НАЗВАНИЕ_КОМПАНИИ КАТЕГОРИЯ СТРАНА СТЕНД`
- Пример: `ACRYLICON CENTRAL ASIAКазахстан11-348`
- Парсинг: искать страну как разделитель, затем стенд (паттерн `\d{1,3}-\d{2,4}`)

### Известные exhibition sites с iteca.kz
| Выставка | URL списка | iframe URL |
|----------|-----------|------------|
| FoodExpo Qazaqstan | `foodexpo.kz/ru/2025ru` | `reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode=FoodExpo%20Qazaqstan%202025` |

### Парсинг
```python
import urllib.request, re

url = "https://reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode=FoodExpo%20Qazaqstan%202025"
html = urllib.request.urlopen(url, timeout=20).read().decode('utf-8')
table = re.search(r'<table[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table.group(1), re.DOTALL | re.IGNORECASE)

countries = ['Казахстан', 'Узбекистан', 'Кыргызстан', 'Россия', 'Китай', 'Турция', ...]

for row in rows[1:]:
    cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', cells[0]).strip()
    # Find country as separator
    for country in sorted(countries, key=len, reverse=True):
        if country in text:
            name = text[:text.find(country)].strip()
            remaining = text[text.find(country) + len(country):]
            stand_match = re.search(r'(\d{1,3}-\d{2,4})', remaining)
            stand = stand_match.group(1) if stand_match else ''
            break
```

### PDF-каталоги iteca
- На `onsite.iteca.kz/img/files/{exhibition}/{YEAR}/` лежат PDF-каталоги
- Структура PDF: КОМПАНИЯ | СТРАНА | ПРОДУКТЫ (в одной строке, разделены переносами)
- **Сложность**: строки компаний чередуются с организаторами региональных групп (содержат "ОРГАНИЗАТОР", "ФОНД", "ЦЕНТР ПОДДЕРЖКИ")
- Фильтрация: пропускать строки с ключевыми словами организаторов

## Питфолл: Supabase count=exact для пустых таблиц

При проверке количества записей через `Prefer: count=exact`:
- Пустые таблицы возвращают `Content-Range: */0` — это нормально
- `clean_clients` и `clients` могут возвращать `*/*` вместо точного числа
- **НЕ полагайся на count=exact для проверки наличия данных** — используй `GET ...?limit=1&select=*` для проверки реальной структуры
- Для `raw_parsed_data` count=exact возвращает HTTP 400 — всегда используй пагинацию

### Питфолл: Supabase пуст при наличии данных в файлах
Если `raw_parsed_data` возвращает 0 записей, но в `/home/khadas/.hermes/agents/parsing-engineer/data/` есть JSON-файлы — данные НЕ загружены в Supabase. Нужно:
1. Проверить какие source уже есть в Supabase: `GET /raw_parsed_data?select=source&limit=1000`
2. Загрузить только отсутствующие источники через batch curl
3. Не загружать повторно то, что уже есть

## Статус загрузки (обновлено 30.06.2026)

**raw_parsed_data: 51,391 записей | clean_clients: 16,142 записей (после очистки)**

### raw_parsed_data по источникам:
| Источник | Записей | Загружено |
|----------|---------|-----------|
| prodexpo_pdf_all | 18,244 | 30.06.2026 |
| worldfood_moscow_2025 | 9,858 | 30.06.2026 |
| prodexpo_pdf_v3 | 6,298 | 30.06.2026 |
| foodmarkets | 4,258 | 29.06.2026 |
| prodexpo_2024-2026 | 7,559 | разные даты |
| worldfood_istanbul | 478 | 30.06.2026 |
| gulfood_dubai | 264 | 30.06.2026 |
| прочие | ~4,422 | разные даты |

### clean_clients после Pipeline V5.5:
| Метрика | Значение |
|---------|----------|
| Всего | 20,065 |
| С phone | 3,181 (15.7%) |
| С email | 1,080 (5.3%) |
| С website | 1,183 (5.8%) |
| С description | 17,153 (84.5%) |
| Страна определена | ~16,089 (80.2%) |

### Кандидаты для парсинга (приоритет, обновлено 22.06.2026)
1. **postavshikov.net** — ~108 компаний в категории «Продукты питания», но много посредников. Низкий приоритет.
2. **export.ru.com** — SPA, требует browser tool / Playwright
3. **metaprom.ru** — SPA (80k+ предприятий), требует browser tool / Playwright

### ⚠️ Питфолл: Проверяй ключи Supabase ПЕРВЫМ делом
Перед любой работой с Supabase через REST API:
1. Проверь `GET /rest/v1/raw_parsed_data?limit=1` — должен вернуть 200 или 404 (если таблица пуста), но НЕ 401
2. Если 401 — ключи устарели, запроси у пользователя актуальные
3. НЕ пытайся загружать данные с невалидными ключами — это пустая трата времени

## PLAYWRIGHT НА RENDER (холодный старт)
Playwright вынесен на Render.com: https://playwright-browser.onrender.com
Бесплатный тариф — сервер засыпает через 15 минут без трафика.
При вызове /fetch?url= первый запрос может занять 30-90 секунд (холодный старт).
НЕ прерывай запрос — дождись ответа. Это нормально.

### Локальный Playwright (РЕКОМЕНДУЕТСЯ для SPA)
- **Playwright 1.60.0 установлен** в venv, Chromium 148 доступен для ARM64
- Запуск: `from playwright.sync_api import sync_playwright; browser = playwright.chromium.launch(headless=True)`
- **Работает для рендеринга SPA-сайтов** (UzFood, Gulfood, Modern Bakery)
- **Важно**: `page.goto(url, wait_until="networkidle")` + `page.wait_for_timeout(5000)` для полной загрузки AJAX
- **Перехват XHR**: `page.on("response", callback)` для поиска API endpoints
- **Перехват запросов**: `page.on("request", callback)` для логирования всех сетевых вызовов
- **Ограничение**: Даже после рендеринга HTML может не содержать данные, если они загружаются через отдельные API вызовы после инициализации
- **Питфолл**: `page.evaluate()` с многострочными JS-строками — экранируй кавычки правильно (используй одинарные кавычки внутри JS)

## Заметки по парсингу выставок через Playwright HF
## Ссылки
- [Gulfood Dubai AJAX-парсинг](references/gulfood-dubai-parsing-2026-07-02.md)
- [Modern Bakery Tilda-парсинг](references/modern-bakery-tilda-parsing-2026-07-02.md)
- [Прокси-ротация для парсеров](references/proxy-rotation-for-parsers-2026-07-02.md)
- [Проблемы с Pipeline V5.5 и выставочными данными](references/gulfood-dubai-parsing-2026-07-02.md#проблемы-с-pipeline-v55-и-выставочными-данными)
- [Consilium-Driven Architecture](references/consilium-driven-architecture-2026-06-28.md)
- [Supabase source_profiles схема](references/supabase-source-profiles-schema-2026-06-28.md)
- [Аудит доступности источников](references/sources-accessibility-audit-2026-06-19.md)
Паттерны URL выставочных сайтов: `references/exhibition-sites-url-patterns.md`.
Аудит SPA-парсинга (2026-06-20): `references/spa-parsing-audit-2026-06-20.md`.
Парсинг icatalog.expocentr.ru (Продэкспо 2024-2026): `references/icatalog-parsing-notes.md`.
PDF-каталоги WorldFood/Продэкспо: `references/icatalog-parsing-notes.md`.
Классификация PDF-каталогов (табличные vs путеводители): `references/pdf-catalog-types-2026-06-24.md` (в layer4-cleaner).
Supabase batch upload pitfalls (PGRST102, UUID, is_duplicate): `references/supabase-batch-upload-pitfalls-2026-06-24.md`.
Gulfood Dubai 2026 — AJAX API, параметры, парсинг: `references/gulfood-dubai-parsing-2026-06-20.md`.
Gulfood Dubai 2026 — Playwright cookies + urllib метод: `references/gulfood-dubai-playwright-cookies-2026-06-20.md`.
Gulfood Dubai 2026 — Статус парсинга 21.06.2026: `references/gulfood-dubai-status-2026-06-21.md`.
WorldFood Istanbul — ERA Soft платформа, DataTables API, 478 экспонентов: `references/worldfood-istanbul-parsing-2026-06-21.md`.
WorldFood Istanbul — Исправление маппинга колонок (21.06.2026): `references/worldfood-istanbul-column-fix-2026-06-21.md`.
WorldFood Istanbul — ERA Soft платформа, структура, селекторы: `references/worldfood-istanbul-analysis-2026-06-21.md`.

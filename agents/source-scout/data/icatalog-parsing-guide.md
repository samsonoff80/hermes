# Парсинг icatalog.expocentr.ru — полное руководство

## Структура сайта

- **Платформа**: SPA на jQuery + Bootstrap
- **Список выставок**: `/ru/exhibitions` — JS-рендер, curl не работает
- **Список компаний**: `/ru/exhibitions/{uuid}/list` — HTML таблица (до ~2000 строк)
- **Карточка компании**: `/ru/exhibitions/{uuid}/exhibitors/{id}?stand=XXX`

## Известные выставки (пищевые)

| Выставка | UUID | Компаний |
|---|---|---|
| ПРОДЭКСПО-2026 | `870c9c18-e84b-11ef-80ce-a0d3c1fab97f` | 1993 |
| ПРОДЭКСПО-2025 | `b5cf5aaa-3c26-11ee-80ce-a0d3c1fab97f` | 1800 |
| ПРОДЭКСПО-2024 | `97cfb9c0-dfee-11ec-80cd-a0d3c1fab97f` | 2149 |
| ПРОДЭКСПО-2023 | `d3a90aa7-bdf4-11eb-80cc-a0d3c1fab97f` | 1968 |
| АГРОПРОДМАШ-2025 | `b67ac0af-40d1-11ee-80ce-a0d3c1fab97f` | 857 |
| АГРОПРОДМАШ-2023 | `ac7d68bf-c129-11eb-80cc-a0d3c1fab97f` | 845 |

## Как найти новые выставки

Через Serper API:
```python
import requests
r = requests.post("https://google.serper.dev/search",
    json={"q": "Продэкспо 2025 icatalog expocentr", "num": 10},
    headers={"X-API-KEY": key})
# Искать /exhibitions/{uuid} в результатах
```

## Парсинг списка компаний

```python
import requests, re
from html import unescape

r = requests.get(f"https://icatalog.expocentr.ru/ru/exhibitions/{uuid}/list", timeout=60)
tbody = re.search(r'<tbody>(.*?)</tbody>', r.text, re.DOTALL).group(1)
rows = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL)

for row in rows:
    id_match = re.search(r'<span[^>]*id="(\d+)"', row)
    name_match = re.search(r'<a href="[^"]*?/exhibitors/\d+\?stand=[^"]*">(.+?)</a>', row)
    country_match = re.search(r'<a href="[^"]*?/countries/[^"]*">(.+?)</a>', row)
    stand_match = re.search(r'<span[^>]*class="badge"[^>]*>(.+?)</span>', row)
    cats = re.findall(r'<a[^>]*class="category"[^>]*>(.+?)</a>', row)
```

## Парсинг карточки компании

```python
r = requests.get(f"https://icatalog.expocentr.ru/ru/exhibitions/{uuid}/exhibitors/{company_id}?stand={stand}", timeout=15)

# Телефон
phones = re.findall(r'<dt>\s*Телефон[^<]*</dt>\s*<dd>(.*?)</dd>', r.text, re.DOTALL)
# Email
email = re.search(r'<dt>\s*E-mail[^<]*</dt>\s*<dd>.*?<a[^>]*href="mailto:([^"]*)"', r.text, re.DOTALL)
# Сайт
site = re.search(r'<dt>\s*Сайт[^<]*</dt>\s*<dd>.*?<a[^>]*href="(https?://[^"]*)"[^>]*target="_blank"', r.text, re.DOTALL)
# Адрес
addr = re.search(r'<dt>\s*Адрес[^<]*</dt>\s*<dd>(.*?)</dd>', r.text, re.DOTALL)
# Описание
desc = re.search(r'<dt>\s*Описание[^<]*</dt>\s*<dd>(.*?)</dd>', r.text, re.DOTALL)
```

## Фильтрация СНГ

```python
CIS = {"Россия", "Республика Беларусь", "Казахстан", "Республика Казахстан",
       "Узбекистан", "Республика Узбекистан", "Кыргызстан", "Киргизская Республика",
       "Армения", "Республика Армения", "Азербайджан", "Азербайджанская Республика",
       "Грузия", "Туркменистан", "Молдова", "Таджикистан"}
```

## Релевантные категории (рубрикаторы)

Кондитерка/глазури:
- "Кондитерские изделия", "Шоколад и шоколадные изделия", "Вафли, печенье, пряники"
- "Зефир, пастила, суфле, мармелад", "Снеки, чипсы, сухарики"
- "Орехи, семечки, сухофрукты", "Ингредиенты для пищевой промышленности"
- "Российский экспортёр"

Нерелевантные:
- "Пиво", "Алкогольные напитки", "Оборудование", "Логистика"

## Результаты (все 6 выставок, 13.06.2026)

| Выставка | Всего | СНГ | Тел | Email | Сайт |
|---|---|---|---|---|---|
| ПРОДЭКСПО-2026 | 1993 | 1625 | 1306 | 1298 | 1215 |
| ПРОДЭКСПО-2025 | 1799 | 1529 | 1326 | 1318 | 1223 |
| ПРОДЭКСПО-2024 | 2149 | 1800 | 1579 | 1572 | 1463 |
| ПРОДЭКСПО-2023 | 1968 | 1697 | 1487 | 1482 | 1367 |
| АГРОПРОДМАШ-2025 | 856 | 637 | 594 | 589 | 590 |
| АГРОПРОДМАШ-2023 | 844 | 637 | 599 | 597 | 587 |
| **ИТОГО** | **9609** | **7925** | **6994** | **6973** | **6635** |

- Телефоны: 88.3%, Email: 88.0%, Сайты: 83.7%
- Время: ~2.5 часа на все 6 выставок

## Дедупликация и очистка (13.06.2026)

После парсинга 6 выставок получено 7925 записей. Дедупликация по `(normalized_name, country)`:

- **Удалено дублей: 2820 (36%)**
- **Уникальных компаний: 5105**
- Без контактов: 495 (9.7%)

**Алгоритм дедупликации:**
```python
def normalize_name(name):
    n = name.lower().strip()
    n = re.sub(r'\b(ооо|ао|ип|зао|пao|оао|тд|тм|llc|ltd)\b', '', n)
    n = re.sub(r'[«»""()\[\]{}]', '', n)
    n = re.sub(r'[^\w\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

# Ключ: (normalize_name(name), country.lower().strip())
# Группировка → объединение полей из дублей → удаление дублей
```

**Объединение полей из дублей:**
- Берём первую запись как основную
- Из дублей берём недостающие поля: phone, email, website, city, address, description, categories
- Категории объединяем (set union)
- Добавляем поле `sources` — список выставок откуда компания

**Критический pitfall: сохранение прогресса**
- НЕ сохранять прогресс только после завершения каждой выставки
- Сохранять каждые 50 записей: `if new_count % 50 == 0: save_progress()`
- Иначе при падении данные теряются

**Критический pitfall: параллельные процессы**
- НЕ запускать два экземпляра парсера одновременно (пишут в один лог)
- Перед запуском проверять: `ps aux | grep parse_all`
- Убивать старые процессы: `kill <pid>`

## Загрузка в Supabase

```sql
CREATE TABLE IF NOT EXISTS prodexpo_raw (
    id SERIAL PRIMARY KEY,
    external_id TEXT,
    name TEXT,
    country TEXT,
    city TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    website TEXT,
    description TEXT,
    stand TEXT,
    pavilion TEXT,
    categories JSONB,
    source TEXT DEFAULT 'prodexpo_2026',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Загрузка батчами по 200 через POST `/rest/v1/prodexpo_raw`.

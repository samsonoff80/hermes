# Полная пересборка базы с нуля — уроки 28.06.2026

## Контекст
Пользователь запустил полный сброс: очистить raw_parsed_data + clean_clients + source_profiles и начать с нуля через полный цикл 4 слоёв.

## Что сработало

### 1. Scout через web_search (execute_code)
- Искал каталоги по 9 странам СНГ
- 23 URL проверено через curl → 18 доступно
- Фильтр: не соцсети, не вики, только каталоги

### 2. source_profiles заполнение
- Загрузил 5 профилей: fabricators.ru, rfactories, areg.am, manufacturers (AM + TJ)
- **Важно**: source_profiles.id — UUID, не batch delete через `id=gt.0`
- **Фикс бага**: `id=in.(uuid1,uuid2,...)` — batch delete работает

### 3. Парсинг 17 источников → raw_parsed_data
- Общее: 3605 сырых → 3009 уникальных
- Лучшие: ProdExpo 2026 (1992), FoodExpo KZ (335), ProductCenter (647)

### 4. Pipeline V5.5 → clean_clients
- Вход: 3009 → Отвергнуто: 334 (11.1%) → Не-СНГ отфильтровано: 428 → **Финал: 2247**

## Что НЕ сработало

### 1. enrich_contacts.py через Groq
**Проблема**: `sb.table(...).is_('phone', 'null').limit(5000).execute()` — выбрасывает AttributeError
**Решение**: загрузить все записи и фильтровать локально в Python

```python
# НЕПРАВИЛЬНО (падает):
sb.table('clean_clients').select('*').is_('phone', 'null').execute()

# ПРАВИЛЬНО (работает):
all_data = sb.table('clean_clients').select('*').execute().data
no_contacts = [r for r in all_data if not r.get('phone') and not r.get('email') and not r.get('website')]
```

### 2. Обогащение через DuckDuckGo API
- Hit rate ~0% для поиска контактов компаний
- API не подходит для этой задачи

### 3. Обогащение через Groq/LLM по названию
- LLM выдумывает телефоны (5% hit rate, но мусорные данные)
- Реальный hit rate для телефонов через LLM = 0%

### 4. execute_code timeout (300с)
- Невозможно обработать >30 записей web_search за один запуск
- Web_search ~5-10 сек на запрос
- **Решение**: батчи по 20-30, параллельные потоки, прогресс в файл

### 5. auto_scout.py (старая версия)
- Требует Serper API (ключ истёк)
- Использовать **auto_scout_v2.py** (через web_search)

### 6. Парсинг навигации вместо компаний
- fabricators.ru: из 310 извлечённых — 60% было мусором (навигация, кнопки "добавить")
- Нужен строгий фильтр:
```python
NAV_WORDS = {'добавить', 'продукция', 'производители', 'поиск', 'товары', ...}
def is_nav(text): return text.lower().strip() in NAV_WORDS or len(text) < 4
```

## Правильная последовательность для пересборки

1. Очистить таблицы: raw_parsed_data, clean_clients, source_profiles
2. Auto Scout: `web_search(query="страна каталог производителей", limit=5)` 
3. Проверка доступности: `curl -s -o /dev/null -w '%{http_code}' --max-time 8 URL`
4. Загрузка в source_profiles (sql_insert batchSize=50)
5. Парсинг: через requests+regex или Playwright
6. Фильтрация мусoria (НАВ_СЛОВА)
7. Загрузка в raw_parsed_data
8. Pipeline V5.5 → clean_clients
9. Нормализация стран
10. Фильтрация СНГ (whitelist)
11. Обогащение контактов (только web_search, не LLM!)

## Формат source_profiles для INSERT
```python
{
    'url': 'https://example.com',
    'domain': 'example.com',
    'source_name': 'Example Catalog',
    'content_type': 'catalog',
    'parsing_method': 'requests+bs4',
    'data_structure': 'list',
    'selectors': '{"item": "a[href*=\"/company/\"]"}',  # строка JSON, не dict!
    'has_pagination': False,
    'pagination_type': 'none',
    'max_pages': 1,
    'phone_on_list': False,
    'email_on_list': False,
    'website_on_list': False,
    'needs_detail_page': True,
    'detail_selectors': '{}',
    'last_verified': '2026-06-28T12:00:00+00:00',
    'success_count': 0,
    'fail_count': 0,
}
```

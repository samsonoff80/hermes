# Supabase Batch Upload Pitfalls (24.06.2026)

## Проблемы при загрузке в raw_parsed_data

### 1. PGRST204 — несуществующие колонки
Попытка вставить запись с полями `city`, `address`, `categories`, `source_year`, `raw_data` вызывает ошибку.
**Решение**: Проверять реальную структуру через `GET /rest/v1/raw_parsed_data?limit=1` перед первой загрузкой.

### 2. PGRST102 — разные ключи в batch
Supabase требует чтобы **все объекты в batch имели одинаковый набор ключей**. Если одна запись имеет `dedup_method` а другая — нет, ошибка.
**Решение**: Всегда включать ВСЕ поля в каждую запись, используя `None` для пустых значений.

### 3. 22P02 — invalid UUID syntax
Поле `id` — UUID, не принимает пустую строку `""`. Поле `duplicate_of` тоже UUID.
**Решение**: Никогда не включать `id` в запись (генерируется автоматически). Для `duplicate_of` использовать `None`.

### 4. Boolean vs string для is_duplicate
В CSV `is_duplicate` хранится как строка `"True"/"False"`, в Supabase — boolean.
**Решение**: `is_duplicate = rec.get('is_duplicate', 'False') == 'True'`

## Рабочий паттерн
```python
required_keys = ['name', 'name_clean', 'country', 'phone', 'email', 'website', 
                 'description', 'source', 'is_duplicate', 'duplicate_of', 
                 'dedup_method', 'dedup_confidence']

normalized = []
for rec in batch:
    norm_rec = {k: rec.get(k, '') for k in required_keys}
    norm_rec['source'] = source_name
    norm_rec['name'] = rec.get('name', '').strip()
    if not norm_rec['name']:
        continue
    if not norm_rec.get('name_clean'):
        norm_rec['name_clean'] = norm_rec['name']
    if not norm_rec['duplicate_of']:
        norm_rec['duplicate_of'] = None
    if not norm_rec['dedup_confidence']:
        norm_rec['dedup_confidence'] = None
    norm_rec['is_duplicate'] = rec.get('is_duplicate', 'False') == 'True'
    normalized.append(norm_rec)
```

## Проверка перед загрузкой
```python
# 1. Проверить существующие записи по source
existing_url = f"{SUPABASE_URL}/rest/v1/raw_parsed_data?source=eq.{urllib.parse.quote(source_name)}&select=*&limit=1"
# 2. Проверить структуру таблицы
schema_url = f"{SUPABASE_URL}/rest/v1/raw_parsed_data?select=*&limit=1"
# 3. Тестовая вставка 1 записи для валидации ключей
```

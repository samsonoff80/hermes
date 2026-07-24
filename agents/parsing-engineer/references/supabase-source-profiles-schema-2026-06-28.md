# Supabase source_profiles Schema Notes (28.06.2026)

## Реальная структура таблицы
```
id, url, domain, source_name, content_type, parsing_method, data_structure,
selectors (JSONB), has_pagination, pagination_type, max_pages,
phone_on_list, email_on_list, website_on_list, needs_detail_page,
detail_selectors (JSONB), last_verified, success_count, fail_count,
created_at, updated_at
```

## Критические питфоллы

### 1. pagination_type = None, не ""
Supabase не принимает пустую строку в опциональных полях. Используй `None`:
```python
"pagination_type": config.get("pagination_type") or None
```

### 2. selectors — JSONB
При чтении из Supabase приходит dict. При записи нужно передать JSON-строку:
```python
"selectors": json.dumps(config.get("selectors", {}), ensure_ascii=False)
```

### 3. Кириллица в query params
Всегда кодировать:
```python
from urllib.parse import quote
url = f"{SUPABASE_URL}/rest/v1/table?" + "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
```

### 4. Несуществующие поля
Следующие поля НЕ существуют в source_profiles:
- `source_metadata` — не включать в INSERT
- `source_name` — существует ✓
- `content_type` — существует ✓

### 5. Частичное совпадение source_name
Supabase REST API `eq.` не поддерживает LIKE. Для поиска по части имени:
```python
all_profiles = sb_get("source_profiles")
matches = [p for p in all_profiles if "2025" in p.get('source_name', '')]
```

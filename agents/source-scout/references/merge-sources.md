# Слияние источников из разных файлов

## Проблема
Результаты из разных запусков имеют разную структуру:
- `sources_by_country.json` — структура `by_country.{country}.working/dead`
- `sources_consilium_checked.json` — структура `checked_sources[]` с полем `status`
- `sources_countries_extra.json` — структура `sources[]` + `failed_sources[]`

## Целевая структура (sources_final.json)
```json
{
  "_comment": "...",
  "_date": "2026-06-19",
  "_stats": {
    "total_checked": N,
    "working_direct": N,
    "needs_proxy": N,
    "dead": N,
    "by_country": {"Россия": {"working": N, "needs_proxy": N, "dead": N}, ...}
  },
  "working_sites": [{"name", "url", "country", "quality", "food_relevance", "type", "source"}],
  "proxy_only_sites": [...],
  "dead_sites": [...]
}
```

## Процедура слияния
1. Загрузить все три файла
2. Извлечь `working` из `by_country` → `working_sites`
3. Извлечь `checked_sources` с `status=working` → `working_sites`
4. Извлечь `checked_sources` с `status=needs_proxy` → `proxy_only_sites`
5. Извлечь `checked_sources` с `status=dead` → `dead_sites`
6. Дедупликация по нормализованному URL:
   ```python
   url = url.rstrip("/").replace("www.", "")
   ```
7. Пересчитать `_stats`

## Пример кода
См. `scripts/merge_sources.py` (если создан) или используй execute_code с паттерном из сессии 19.06.2026.

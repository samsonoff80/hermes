# Consilium — Архитектурные заметки (обновлено 20.06.2026)

## consilium_ask() — ключевая функция

### Проблема (исправлена 20.06.2026)
Функция `consilium_ask()` была **определена в `__init__.py` как импорт из `providers`**, но в `providers.py` её не существовало. Все агенты (`enricher.py`, `parser.py`, `matcher.py`, `consilium_brain.py`) вызывали `from providers import consilium_ask` — и получали `ImportError` при прямом запуске.

### Решение
Добавлена полная реализация `consilium_ask()` в `providers.py`:
- Параллельный опрос N моделей через `asyncio.gather`
- Выбор лучшего ответа: JSON с максимумом ключей → самый длинный текст
- Robust JSON extraction через `_extract_json()` (markdown, escapes, regex fallback)
- Возврат: `{best, all_responses, consensus_score, json_result, models_asked, models_responded}`

### Модели (актуально 20.06.2026)
**DEFAULT_MODELS (3):**
1. `mistral/mistral-large-latest` — таймаут 120s
2. `groq/llama-3.3-70b-versatile` — таймаут 60s
3. `openrouter/google/gemini-2.5-flash-lite` — таймаут 60s

**ALL_MODELS (5) = DEFAULT_MODELS +:**
4. `openrouter/meta-llama/llama-4-maverick` — таймаут 120s
5. `cloudflare/@cf/meta/llama-3.2-3b-instruct` — таймаут 90s

### Паттерн вызова
```python
from providers import consilium_ask

result = await consilium_ask(session, prompt, use_all_models=False)
# result = {"best": str, "json_result": dict|None, "consensus_score": float, ...}
```

## Интеграция со Слоем 4 (clean_with_consilium.py)

### Архитектура
1. **Фаза 1**: быстрая фильтрация регулярками + garbage keyword filter
2. **Фаза 2**: консилиум для сложных случаев (батчи по 20, лимит 200)
3. **Фаза 3**: сохранение в clean_clients с фильтрацией существующих ключей

### Ключевые функции
- `load_existing_clean_clients()` — загрузка существующих `(name_clean, country)` из базы
- `needs_consilium()` — определение записей для AI-проверки (нет паттерна компании, неопределённая страна, подозрительная длина)
- `is_garbage_name()` — расширенная проверка: HTML, длина >200, garbage keywords, отсутствие алфавита

### Garbage Keywords (навигация каталогов/выставок)
ПРОДЭКСПО, ПАВИЛЬОН, ОРГАНИЗАТОР, СПОНСОР, ПАРТНЕР, УЧАСТНИК, ОФИЦИАЛЬНЫЙ КАТАЛОГ, СХЕМА РАСПОЛОЖЕНИЯ, EXHIBITOR LIST, OFFICIAL CATALOGUE, FLOOR PLAN, СОГЛАСНО, РЕЙТИНГ, ИНФОРМАЦИОННАЯ ПОДДЕРЖКА, МЕЖДУНАРОДНАЯ ВЫСТАВКА и др.

## Supabase RPC для TRUNCATE
```python
sb.rpc("exec_sql", {"sql_query": "TRUNCATE clean_clients"})
```
Удаление по одному через DELETE с `.eq()` — слишком медленно для 10K+ записей.

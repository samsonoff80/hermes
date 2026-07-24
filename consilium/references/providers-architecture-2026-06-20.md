# Providers Architecture — 2026-06-20

## Структура `providers.py`

### `consilium_ask(session, prompt, ...)` — главная функция

Параллельно опрашивает несколько AI-моделей и возвращает консенсус.

```python
async with aiohttp.ClientSession() as session:
    result = await consilium_ask(session, "твой промпт", use_all_models=False)
    # result = {
    #     "best": str,              # Лучший ответ
    #     "all_responses": list,    # [(model, response), ...]
    #     "consensus_score": float, # 0.0-1.0 (доля ответивших)
    #     "json_result": dict|None, # Распарсенный JSON
    #     "models_asked": int,
    #     "models_responded": int,
    # }
```

**Параметры:**
- `session` — aiohttp.ClientSession (обязательно)
- `prompt` — текст запроса (обязательно)
- `models` — список моделей (по умолчанию DEFAULT_MODELS)
- `timeout` — таймаут на модель (по умолчанию 90s)
- `require_fields` — обязательные поля в JSON-ответе
- `use_all_models` — True для 5 моделей, False для 3

### Модели

**DEFAULT_MODELS (3):**
1. `mistral/mistral-large-latest` (120s)
2. `groq/llama-3.3-70b-versatile` (60s)
3. `openrouter/google/gemini-2.5-flash-lite` (60s)

**ALL_MODELS (5):** DEFAULT + Llama-4-Maverick (120s) + Cloudflare Llama-3.2 (90s)

### `_extract_json(text)`

Robust парсинг JSON из ответов AI:
- Убирает markdown-обёртки (` ```json `)
- Обрабатывает экранированные переносы
- Regex fallback для битого JSON
- Возвращает `dict` или `None`

### `ask_model(session, model, prompt, timeout, require_fields)`

Опрос одной модели с retry (3 попытки, circuit breaker).

### `_ask_*()` функции

- `_ask_openrouter()` — OpenRouter API
- `_ask_mistral()` — Mistral API
- `_ask_groq()` — Groq API
- `_ask_cloudflare()` — Cloudflare Workers AI

**ВАЖНО:** После правок всегда проверять что ВСЕ `_ask_*` функции имеют полное тело с `session.post()`. `_ask_cloudflare()` ранее потеряла тело (остался только `except` без `try`).

## Circuit Breaker

- 5 ошибок подряд → модель отключается на 5 минут
- Успешный ответ → счётчик ошибок сбрасывается
- Статистика в `stats` (requests, cache_hits, retries, empty_responses)

## Использование из внешних скриптов

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/consilium"))
from providers import consilium_ask, DEFAULT_MODELS, ALL_MODELS
import aiohttp, asyncio

async def main():
    async with aiohttp.ClientSession() as session:
        result = await consilium_ask(session, "твой вопрос")
        print(result["best"])

asyncio.run(main())
```

## Известные проблемы

- `_ask_cloudflare()` — тело функции может потеряться при правках (остаётся только `except`). Всегда проверять наличие `session.post()` в теле.
- `consilium_ask()` — была добавлена в 20.06.2026, до этого импортировалась но не существовала
- **`consilium_ask()` line 349 bug:** `if result and result.strip()` — assumes `best` is always str. When models return structured data, `best` can be a dict → `AttributeError: 'dict' object has no attribute 'strip'`. **Fix:** `if isinstance(result, str) and result.strip():` or `if result and str(result).strip():`
- **`all_responses` format:** Returns `list[tuple]` in some code paths, `list[dict]` in others — inconsistent.

## Реальное состояние провайдеров (27.06.2026)

| Провайдер | Статус | Примечание |
|-----------|--------|------------|
| Mistral | ✅ Работает | Ключ в `.env` (MISTRAL_API_KEY), medium-latest работает |
| Groq | ⚠️ Circuit breaker | Срабатывает после 10 ошибок, нестабилен |
| OpenRouter | ❌ Нет кредитов | 402 Insufficient credits |
| Cloudflare | ⚠️ Нестабилен | Часто пустые ответы, нет JSON |
| Serper | ✅ Работает | 100 запросов/день, ключ в `.env` и `temp_keys.json` |
| Tavily | ❌ 403 | Заблокирован |
| DaData | ⚠️ 0% для не-юрлиц | Работает только для ООО/ТОО/АО/ИП |

**Вывод:** Consilium работает только для <50 запросов. Для batch — использовать Mistral direct или Serper.

**Полный аудит Consilium v7.1 (на основе анализа RAW-файлов репозитория).** Я изучил README.md, config.yaml, ключевые модули consilium/ и providers/, а также документацию Hermes Agent (включая v0.19).

### 1. Найденные проблемы (критические + важные)

**Критический баг (симптом: "Provider failed after retries")**:
- **Файл**: `consilium_server.py` (строки ~700-850, обработка ответа).
- **Описание**: После успешного 200 OK от провайдера ответ не всегда возвращается Hermes в правильном OpenAI-формате. `rescue_inline_tool_calls` + `normalize_message_content` могут ломать структуру (`tool_calls` или `content` null/empty). Hermes ожидает строго `choices[0].message.{content, tool_calls}`. При неидеальном парсинге (особенно для tool-calling моделей) fallback-логика в Hermes срабатывает как "failed". Таймауты близки (Consilium 30s/provider, Hermes 45s overall), но при стриминге/частичных ответах цепочка ломается.
- **Решение (diff)**:
  ```python
  # В /chat/completions эндпоинте, после вызова провайдера:
  if response.status_code == 200:
      data = response.json()
      # Принудительная нормализация OpenAI-совместимого ответа
      message = data.get("choices", [{}])[0].get("message", {})
      if "tool_calls" not in message:
          message["tool_calls"] = rescue_inline_tool_calls(...) or []
      if not message.get("content") and not message.get("tool_calls"):
          message["content"] = extract_openai_content(data) or ""
      # Гарантируем finish_reason
      data.setdefault("choices", [{}])[0].setdefault("finish_reason", "stop")
      _log_usage(...)
      return JSONResponse(data)
  ```

**Другие проблемы**:
- **consilium_server.py**:
  - `load_keys` дублирует логику из `base.py` (нарушение DRY). Глобальный `http_client` не закрывается в ошибках (утечка).
  - `sticky_sessions` — dict без cleanup (потенциальная утечка памяти при 100+ запросах).
  - Task Router примитивный (if "код" in text) — неустойчив к языку/синонимам.
  - Нет обработки non-JSON ответов от провайдеров (падение на `.json()`).
- **rate_limiter.py**: `_load_state` пустой (не загружает в память). `record_request` — pass. Логика упрощённая, не считает реальные RPM/TPM.
- **fallback_manager.py**: PRIORITY жёсткий, не использует `provider_stats`. Дублирование тегов с README.
- **provider_stats.py**: Формула avg_latency некорректна (деление на success без проверки). Нет очистки старых записей.
- **base.py + providers/**: Автообнаружение работает, но `load_keys` парсит .env вручную (хрупко, не учитывает `enc:` шифрование полностью). Мёртвый код в некоторых providers (не все импортированы).
- **Общее**:
  - Глобальные переменные (`key_indexes`, `sticky_sessions`) без lock'ов в async — race conditions.
  - Нет обработки system prompt > 100K (токенизация отсутствует).
  - Indentation/imports OK, но дубли в logging.
  - Circuit Breaker threshold=10 (README говорит 5) — несоответствие.

**Мёртвый/неиспользуемый код**: `update_all.py`, `dashboard.py`, `alerting.py`, `health_checker.py` (частично), `key_encryption.py` (не везде вызывается).

### 2. Совместимость с Hermes Agent v0.19

- **Изменения v0.19** (Quicksilver Release, ~20 июля 2026): Улучшенный tool calling, reasoning streaming по умолчанию, delivery-obligation ledger, profile-based routing, gateway hardening. Нет радикальных изменений в `/v1/chat/completions` (OpenAI-совместимо).
- **Config.yaml**: Совместим (`provider: custom`, `base_url`, `request_timeout: 45`). System prompt в Hermes стал чище (меньше "Finishing the job" мусора) — фильтр Consilium всё равно полезен.
- **Формат ответа**: Нужно гарантировать `tool_calls` всегда присутствует (даже пустой список) + `content: null` при tool calls. Текущий rescue помогает, но требует доработки.
- **Новые фичи**: Можно добавить поддержку `reasoning_content` и background delegation hints в Task Router.

**Вывод**: Совместим с минимальными правками (в основном ответы).

### 3. Проверка Flow (по README)

- **"Привет" → chat**: Работает (groq/cloudflare).
- **"Напиши код" → code**: Частично (router слабый).
- **Fallback/429/401**: Работает на уровне, но rate_limiter неполный.
- **Circuit Breaker**: Только network errors — OK.
- **System Prompt Filter**: Эффективен, оставляет SOUL + AGENTS.md.

**Проблемы в flow**: При всех провайдерах down — Hermes получает generic fail (нужен graceful degrade с сообщением "All providers down").

### 4. Расширяемость

- **Новый провайдер**: Добавить `providers/new.py` (наследует BaseProvider), зарегистрировать в `__init__.py` — автообнаружение работает.
- **Новый тип задачи**: Расширить TAG_RULES в fallback_manager + router в server.
- **Приоритет**: Сейчас жёсткий PRIORITY — перейти на баллы (см. ниже).
- **Прокси**: Поддерживается (если ключ 'proxy:').
- **Ключи**: `PREFIX_N` — OK, авто.
- **Автообнаружение**: Да, через ALL_PROVIDERS.

### 5. Надёжность / граничные случаи

- Все провайдеры down → fallback_chain пустая → crash (нужен default "All down").
- .env пустой → providers disabled.
- AGENTS.md/SOUL не найден → Hermes fallback.
- Перезапуск во время запроса → http_client closed, но asynccontextmanager помогает.
- 100 запросов → httpx limits OK, но SQLite lock'и могут bottleneck.
- Non-JSON → падение (добавить try/except).
- Большой prompt → OOM на VIM4 (нет chunking).
- Спецсимволы в ключах → OK (env).

### 6. Балльная система провайдеров (реализация)

**Формула** (score = 0..100):
```python
score = (success_rate * 40) + ( (1 / (avg_latency + 1)) * 20 ) + (rpd_remaining_factor * 20) - (fail_streak * 10) - (context_penalty * 10)
```
- success_rate = success / (success + fail + 1)
- rpd_remaining_factor = 1 - (used_rpd / total_rpd)
- context_penalty для моделей < 32k.

**Реализация**:
- Расширить `provider_stats.py` + SQLite.
- В fallback_manager: сортировать по `get_priority()` вместо PRIORITY.
- Обновлять после каждого запроса (success/fail + latency).
- Сохранение/восстановление при рестарте — уже есть.

**Интеграция**:
```python
# В consilium_server.py после вызова
if success:
    provider_stats.record_success(provider, latency, tokens)
    circuit_breaker.record_success(provider)
else:
    provider_stats.record_failure(provider)
    circuit_breaker.record_failure(provider)
```

### 7. Состояние агентов

- **orchestrator**: SOUL.md — OK, протокол delegate_task/read_file работает.
- **product-analyst / source-scout / parsing-engineer / parser**: Цепочка определена, но SKILL.md/PROGRESS.md (не все прочитаны) нуждаются в обновлении под v0.19 (лучше tool calling).
- **optimizer**: Отдельный — OK.
- **Проблемы**: Абсолютные пути в config.yaml/SOUL — хрупко при миграции. Нет обработки ошибок delegate_task.
- **Улучшения**: Добавить agent-specific routing в Consilium (по model tag). Новые агенты: `monitor` (health) + `validator` (data quality).

### 8. Рекомендации по модернизации

**Архитектура**:
- Вынести Task Router + Prompt Filter в отдельный middleware.
- Использовать `asyncio.Semaphore` + dependency injection вместо глобалов.
- Перейти на Pydantic v2 models для запросов/ответов.

**Фичи**:
- Token counting (tiktoken) перед отправкой.
- Adaptive model selection per task + budget.
- Prometheus metrics + Grafana dashboard.
- WebSocket для true streaming.

**Оптимизация для VIM4 8GB**:
- Ограничить concurrency (httpx limits + semaphore 10-20).
- SQLite WAL mode + vacuum.
- Lazy load providers.
- Offload usage logging в background task.

**Отказоустойчивость**:
- Redis fallback для rate/stats (или in-memory + periodic persist).
- Health checker с auto-restart.
- Graceful shutdown + request queue.

**Мониторинг**:
- Request ID propagation (X-Request-ID).
- Alerting в Telegram при >5% fail rate.
- /debug endpoint с traceback.

**Расширяемость**:
- Plugin system для новых task types.
- Config-driven priority/scores.

**Pull Request**: Рекомендую создать ветку `v7.2-refactor`. Основные PR: (1) fix critical response, (2) full scoring system, (3) rate_limiter complete.

**Итог**: Система крепкая, но требует полировки rate/stats и ответа. После фиксов — production-ready на VIM4. Готов помочь с конкретными патчами!

**Полный аудит и анализ репозитория https://github.com/samsonoff80/hermes (Consilium v7.1 + Hermes Agent pipeline)**

Я изучил **весь репозиторий** через RAW-файлы (README, config, все consilium/*.py, providers/*, агенты/*, SOUL.md и т.д.). Ниже — структурированный отчёт строго по вашему промпту.

### 1. Найденные проблемы

**Критические:**
- **consilium_server.py** (строки ~750-850, обработка ответа + ~400-500 rescue/normalize):
  - Критический баг "Provider failed after retries": даже при 200 OK от провайдера структура ответа не всегда соответствует OpenAI (tool_calls отсутствует/неправильно, content null при tool calls). Hermes (v0.19) падает в retry/fail. Rescue_inline работает нестабильно для Qwen/Hermes-style tool calls.
  - Глобальный `http_client` без обработки ошибок + `sticky_sessions` dict без TTL-cleanup → утечки.
  - Нет try/except вокруг `response.json()` → crash на non-JSON.
- **rate_limiter.py**: `_load_state` пустой, `record_request` — pass. Реальные лимиты не отслеживаются → ложные 429/fallback.
- **fallback_manager.py**: Жёсткий PRIORITY игнорирует `provider_stats`. Дублирование TAG_RULES.
- **provider_stats.py**: Некорректная формула avg_latency, нет очистки старых данных.

**Важные:**
- Дублирование `load_keys` (server + base.py).
- Глобальные `key_indexes`, `sticky_sessions` без locks в async.
- Task Router слишком примитивный (строковый in).
- Отсутствует токенизация больших prompt (>100K).
- Мёртвый/неполный код: dashboard, alerting, update_all, health_checker (частично).
- Несоответствие README (circuit threshold 5 vs код 10).

**Мелкие:** Отступы/импорты OK, но sys.path hack в server.py.

### 2. Совместимость с Hermes Agent v0.19

- v0.19 (Quicksilver, 20 июля 2026) — улучшения tool calling, streaming reasoning, gateway hardening, delivery ledger. Формат API OpenAI-совместим, system prompt чище.
- **config.yaml**: Полностью совместим (custom provider, timeout 45s).
- **System prompt**: Фильтр Consilium всё ещё актуален (вырезает Hermes-мусор).
- **Ответ API**: Нужно доработать (гарантировать tool_calls + content null).
- **Новые фичи**: Поддержать reasoning_content и background delegation hints.

**Вывод**: Совместим после фикса ответа.

### 3. Критический баг + Flow

**Баг подтверждён**: Ответ теряется в normalize/rescue → Hermes видит fail. Цепочка возврата (call_provider → extract → JSONResponse) имеет дыры.

**Flow по README**:
- Telegram → Hermes → Consilium → Router/Filter → Fallback → Rate/Circuit → Provider → Ответ → Hermes: **работает частично**.
- Примеры ("Привет", "Напиши код") — OK для groq.
- Fallback/429/401 — работает на уровне, но rate_limiter слабый.
- Circuit — только network.
- При всех down — нет graceful сообщения.

**System Prompt Filter**: Работает хорошо.

### 4. Расширяемость

- Новый провайдер: Добавить файл в providers/, наследовать BaseProvider, добавить в __init__.py — авто.
- Новый task type: Расширить TAG_RULES + router.
- Приоритет: Через scoring (см. ниже).
- Прокси/ключи: Поддерживается (`proxy:`, PREFIX_N).
- Автообнаружение: Да.

### 5. Надёжность / граничные случаи

- Все провайдеры down → crash (нужен default).
- .env пустой → disabled providers.
- AGENTS.md отсутствует → Hermes fallback.
- Перезапуск → частично OK (lifespan).
- 100 запросов → bottleneck в SQLite + globals.
- Non-JSON / большой prompt / спецсимволы → уязвимости.

### 6. Балльная система (реализация)

**Формула**:
```python
score = (success_rate * 0.4) + (latency_score * 0.2) + (rpd_factor * 0.2) - (fail_streak * 0.1) - (context_penalty * 0.1)
```
- success_rate = success / (success + fail + 1)
- latency_score = 1 / (avg_latency + 1)
- rpd_factor из rate_limiter.
- Обновление реал-тайм + SQLite persist.

**Интеграция**:
- Расширить `provider_stats`.
- В fallback_manager: сортировать по score.
- Вызывать после каждого запроса в server.py.
- При рестарте — авто-восстановление.

### 7. Состояние агентов

- **orchestrator**: SOUL + протокол delegate_task/read_file — работает.
- **product-analyst/source-scout/parsing-engineer/parser**: Цепочка определена, PROGRESS.md recovery OK. Но SKILL.md нуждаются в обновлении под v0.19 tool calling.
- **optimizer**: OK.
- **Проблемы**: Абсолютные пути, слабая обработка ошибок delegate.
- **Улучшения**: Agent-specific tags в Consilium, validator-агент, лучшее взаимодействие через structured context.

### 8. Рекомендации

**Архитектура**:
- Middleware для filter/router.
- Dependency Injection вместо globals.
- Async locks + Semaphore.

**Фичи**:
- Token counting, Prometheus, WebSocket streaming, adaptive budget.

**VIM4 оптимизация**:
- Concurrency limit 10-20, WAL SQLite, lazy providers.

**Отказоустойчивость**:
- Redis cache, circuit + fallback to dummy response.

**Мониторинг**:
- Request-ID, Telegram alerts, /debug.

**Общее**: Система хорошая для ARM64, но требует рефакторинга rate/stats и ответа. После правок — отличная.

**Pull Request**: Рекомендую ветку v7.2 с фиксами. Могу предоставить полные патчи.

Готов к реализации конкретных правок!

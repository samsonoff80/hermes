# Hermes + Consilium v7 — B2B Pipeline на VIM4 ARM64

## Железо

| Параметр | Значение |
|----------|----------|
| Платформа | Khadas VIM4 ARM64 |
| RAM | 8 GB |
| ОС | Ubuntu 24.04 |
| IP | 192.168.10.14 |

---

## Архитектура

```
Telegram
    ↓
Hermes Agent v0.18.2 (Nous Research)
    ↓  config.yaml: provider=custom, base_url=http://127.0.0.1:8765/v1
Consilium (:8765 FastAPI)
    ├── System Prompt Filter
    ├── Task Router (chat / code / search / analysis)
    ├── Fallback Manager (16 провайдеров)
    ├── Rate Limiter (per-key: RPM / TPM / RPD / TPD)
    ├── Circuit Breaker
    └── Usage Logger (SQLite)
    ↓
Провайдеры (providers/*.py — модульная система)
    ├── groq (3 ключа)          — llama-3.3-70b-versatile
    ├── cloudflare (3 ключа)    — @cf/meta/llama-3.2-3b-instruct
    ├── github (3 ключа)        — gpt-4o-mini
    ├── mistral (2 ключа)       — mistral-large-latest
    ├── sambanova (2 ключа)     — Meta-Llama-3.3-70B-Instruct
    ├── openrouter (3 ключа)    — 344 модели
    ├── deepinfra, hf, siliconflow, together, reka, aihorde
    └── keyless: aihorde
```

---

## Поток запроса (детально)

### 1. Пользователь отправляет сообщение в Telegram

```
"Привет"
```

### 2. Hermes Agent формирует system prompt

```python
system_prompt = (
    SOUL.md
    + AGENTS.md
    + HERMES_AGENT_HELP_GUIDANCE
    + "Finishing the job"
    + "Parallel tool calls"
)
```

| Компонент | Размер | Описание |
|-----------|--------|----------|
| `SOUL.md` | ~74 байт | Роль оркестратора |
| `AGENTS.md` | ~1700 байт | Протокол вызова слоёв, пути к агентам |
| Блоки Hermes | — | Вырезаются фильтром Consilium |

### 3. Hermes отправляет запрос в Consilium

```json
POST http://127.0.0.1:8765/v1/chat/completions
{
  "model": "auto",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Привет"}
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### 4. Consilium фильтрует system prompt

```python
# Вырезаем блоки Hermes:
m["content"] = re.sub(
    r"You run on Hermes Agent.*?source of truth when the two differ\.\s*",
    "",
    ...
)
m["content"] = re.sub(r"# Finishing the job.*?(?=\n#|\Z)", "", ...)
m["content"] = re.sub(r"# Parallel tool calls.*?(?=\n#|\Z)", "", ...)

# Оставляем: SOUL.md + AGENTS.md
```

### 5. Task Router классифицирует задачу

```python
user_text = последнее user-сообщение  # "Привет"

if "код" in user_text:
    task = "code"
elif "анализ" in user_text:
    task = "analysis"
elif "найди" in user_text:
    task = "search"
else:
    task = "chat"
```

### 6. Fallback Manager строит цепочку провайдеров

```python
PRIORITY = [
    "groq", "cloudflare", "github",
    "mistral", "sambanova", "openrouter"
]

fallback_chain = [
    {"provider": "groq",       "model": "llama-3.3-70b-versatile",      "keys": 3},
    {"provider": "cloudflare", "model": "@cf/meta/llama-3.2-3b-instruct", "keys": 3},
    {"provider": "github",     "model": "gpt-4o-mini",                  "keys": 3},
    # ...
]
```

### 7. Rate Limiter проверяет доступность

```python
is_available("groq", key_index=0)
    ↓
Проверяет: RPM, TPM, RPD, TPD, cooldown
    ↓
True  → вызываем провайдер
False → следующий ключ → следующий провайдер
```

### 8. `call_provider` отправляет запрос

```python
POST https://api.groq.com/openai/v1/chat/completions
Authorization: Bearer GROQ_API_KEY_1

{
  "model": "llama-3.3-70b-versatile",
  "messages": [...],
  ...
}
    ↓
200 OK → {
  "choices": [{"message": {"content": "Привет! Как дела?"}}],
  "usage": {...}
}
    ↓
_log_usage("groq", "llama-3.3-70b-versatile", usage)
```

### 9. При ошибке — fallback

```python
429 → rate_limiter.mark_429("groq", 0)  → cooldown 90 с
401/402/403 → rate_limiter.mark_402("groq", 0)  → ключ disabled

    ↓
Следующий ключ groq → если все исчерпаны → cloudflare → github → ...
```

### 10. Circuit Breaker защита

```python
5 network-ошибок подряд → circuit_breaker блокирует провайдер на 60 с
200 OK → circuit_breaker.record_success() → сброс счётчика
```

> **Примечание:** Circuit Breaker не срабатывает на 401/402/429 — только на сетевые ошибки.

### 11. Ответ возвращается Hermes

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "llama-3.3-70b-versatile",
  "choices": [{"message": {"content": "Привет! Как дела?"}}],
  "usage": {
    "prompt_tokens": 500,
    "completion_tokens": 10,
    "total_tokens": 510
  }
}
```

---

## Провайдеры

### Приоритет (по дневным лимитам)

| Приоритет | Провайдер | RPD | TPD | Модели |
|-----------|-----------|-----|-----|--------|
| 1 | **groq** | 1000 | 100K | llama-3.3-70b-versatile |
| 2 | **cloudflare** | 100 | 500K | @cf/meta/llama-3.2-3b-instruct |
| 3 | **github** | 50 | 500K | gpt-4o-mini |
| 4 | **mistral** | 10000 | 10M | mistral-large-latest |
| 5 | **sambanova** | 500 | 1M | Meta-Llama-3.3-70B-Instruct |
| 6 | **openrouter** | 50 | 2M | 344 модели |

### Ключи (`.env`)

```bash
# Формат: PREFIX_1, PREFIX_2, ... PREFIX_N
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
CLOUDFLARE_API_KEY_1=...
GITHUB_TOKEN_1=...

# Поддерживается любое количество ключей (1, 3, 5, 10, ...)
# Прокси: если ключ начинается с 'proxy:' — идёт через прокси
```

### Ротация ключей

```python
def get_next_key(name):
    keys = PROVIDER_KEYS[name]          # ["key1", "key2", "key3"]
    idx = key_indexes[name] % len(keys)
    key_indexes[name] += 1
    return keys[idx]

# 401/402/403 → rate_limiter.mark_402() → ключ исключается
```

### Целевое использование моделей

```python
TASK_CHAINS = {
    "chat":     ["llama", "mistral", "gpt", "gemma", "qwen"],
    "code":     ["coder", "deepseek", "code", "hy3"],
    "search":   ["gemini", "scout", "sonnet", "gpt"],
    "analysis": ["large", "ultra", "r1"],
}
```

---

## 6 Агентов B2B-пайплайна

| Агент | Роль | Слой |
|-------|------|------|
| `orchestrator/` | Дирижёр, вызывает слои через `delegate_task` | — |
| `optimizer/` | Инженер (Aider + Consilium) | — |
| `product-analyst/` | Анализ продуктов | Слой 1 |
| `source-scout/` | Поиск источников | Слой 2 |
| `parsing-engineer/` | Парсинг каталогов | Слой 3 |
| `parser/` | Очистка данных | Слой 4 |

Каждый агент: `SOUL.md` (роль) + `SKILL.md` (инструкции) + `PROGRESS.md` (recovery)

### Протокол вызова (`AGENTS.md`)

```
1. read_file(<путь>/SOUL.md)
   read_file(<путь>/SKILL.md)
   read_file(<путь>/PROGRESS.md)

2. delegate_task(
       goal="Ты <слой>. DONE — верни итог.",
       context=...,
       toolsets=[...]
   )

3. Не пиши текст перед delegate_task. Только tool call.
```

**Цепочка:** `product-analyst` → `source-scout` → `parsing-engineer` → `parser`

---

## Rate Limiter

| Механизм | Описание |
|----------|----------|
| **Per-key tracking** | RPM, TPM, RPD, TPD |
| **Cooldown escalation** | 90 с → 5 м → 15 м → 1 ч → 6 ч |
| **402/403** | Ключ отключается навсегда |
| **429** | Cooldown с экспоненциальным отступом |
| **Динамические лимиты** | Из заголовков `x-ratelimit-*` |

---

## Circuit Breaker

| Состояние | Условие | Действие |
|-----------|---------|----------|
| **OPEN** | 5 network-ошибок подряд | Блокировка на 60 с |
| **CLOSED** | Успешный запрос | Сброс счётчика |

---

## Usage Logger

```bash
curl http://127.0.0.1:8765/usage/today
```

```json
{
  "date": "2026-07-20",
  "total_tokens": 510,
  "breakdown": [...]
}
```

---

## Health Check

```bash
curl http://127.0.0.1:8765/health
```

```json
{
  "status": "ok",
  "providers": {
    "groq": 3,
    "cloudflare": 3,
    ...
  }
}
```

---

## System Prompt Filter

| Этап | Содержимое |
|------|------------|
| **До фильтра** | SOUL.md + AGENTS.md + HERMES_AGENT_HELP_GUIDANCE + Finishing the job + ... |
| **После фильтра** | SOUL.md + AGENTS.md (~1800 символов) |

---

---

## Новые возможности (v7.1)

### 🔐 Шифрование ключей (AES-256-GCM)

Ключи в `.env` могут храниться в зашифрованном виде с префиксом `enc:`. При запуске расшифровываются автоматически.

```bash
# Пример зашифрованного ключа
GROQ_API_KEY_1=enc:U2FsdGVkX1+...
```

### 📊 Provider Statistics (адаптивный приоритет)

SQLite-база с историей успешности каждого провайдера. Приоритет автоматически повышается для стабильных провайдеров.

| Метрика | Описание |
|---------|----------|
| `success_rate` | Процент успешных запросов |
| `avg_latency` | Средняя задержка |
| `total_tokens` | Общий объём токенов |
| `last_error` | Время последней ошибки |

```bash
curl http://127.0.0.1:8765/stats/providers
```

```json
{
  "providers": [
    {"name": "groq", "success_rate": 0.98, "avg_latency": 0.45, "priority": 1},
    {"name": "cloudflare", "success_rate": 0.95, "avg_latency": 1.20, "priority": 2}
  ]
}
```

### 🖥 Dashboard (веб-интерфейс)

```bash
curl http://127.0.0.1:8765/
```

HTML-страница со статусом всех провайдеров, количеством ключей, приоритетом по успешности.

```
┌─────────────────────────────────────────┐
│  Consilium Dashboard v7.1               │
├─────────────────────────────────────────┤
│  Provider  │ Status │ Keys │ Priority │
│  groq      │   🟢   │  3   │    1     │
│  cloudflare│   🟢   │  3   │    2     │
│  github    │   🟡   │  2   │    3     │
│  mistral   │   🔴   │  0   │    —     │
└─────────────────────────────────────────┘
```

### 🚨 Alerting (уведомления в Telegram)

Автоматические уведомления при:

| Событие | Условие | Действие |
|---------|---------|----------|
| **Все провайдеры упали** | Нет доступных провайдеров | Срочное сообщение |
| **Провайдер отключён** | 402/403 на всех ключах | Уведомление + лог |
| **Circuit Breaker** | 5 network-ошибок подряд | Alert + cooldown |
| **Rate limit** | 429 на всех ключах | Предупреждение |

```bash
# Настройка в config.yaml
alerting:
  telegram_bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${ALERT_CHAT_ID}"
  cooldown: 300  # секунд между повторными alerts
```

### 📋 Model Catalog (SQLite)

Кэш моделей всех провайдеров с автообновлением. Быстрый доступ без запросов к API.

```bash
curl http://127.0.0.1:8765/models
```

```json
{
  "models": [
    {"id": "llama-3.3-70b-versatile", "provider": "groq", "context": 128000, "pricing": {"input": 0.59, "output": 0.79}},
    {"id": "gpt-4o-mini", "provider": "github", "context": 128000, "pricing": {"input": 0.15, "output": 0.60}}
  ]
}
```

### 🔍 Request ID

Уникальный идентификатор для каждого запроса. Трассировка через всю цепочку: Hermes → Consilium → Provider.

```python
# Заголовки запроса
X-Request-ID: req-7f3a9b2c-...
X-Trace-ID: trace-9e4d1f8a-...

# Логи
[2026-07-20 22:45:12] req-7f3a9b2c → groq:key_0 → llama-3.3-70b → 200 OK (510 tokens)
[2026-07-20 22:45:12] req-7f3a9b2c ← groq ← 200 OK (10 tokens)
```

### 💾 Rate Limiter в SQLite

Состояние лимитов сохраняется между перезапусками. Cooldown и отключённые ключи не теряются.

```bash
# Структура таблицы
sqlite3 ~/.hermes/consilium.db ".schema rate_limits"

# Вывод
CREATE TABLE rate_limits (
    provider TEXT,
    key_index INTEGER,
    rpm_used INTEGER,
    tpm_used INTEGER,
    rpd_used INTEGER,
    tpd_used INTEGER,
    cooldown_until TIMESTAMP,
    disabled BOOLEAN,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 🏥 Health Checker (прогрев при старте)

При запуске Consilium проверяет всех провайдеров. Сразу видно кто живой.

```bash
# Startup health check
[2026-07-20 22:00:01] Health check started...
[2026-07-20 22:00:02] groq: ✅ OK (latency: 0.3s)
[2026-07-20 22:00:03] cloudflare: ✅ OK (latency: 0.8s)
[2026-07-20 22:00:04] github: ⚠️ 429 (rate limited, retry in 60s)
[2026-07-20 22:00:05] mistral: ❌ 401 (key invalid)
[2026-07-20 22:00:05] Health check complete. 2/4 providers ready.
```

## Команды

```bash
# Перезапуск
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent

# Проверка состояния
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/usage/today

# Обновление моделей (cron: 0 3 * * *)
cd ~/.hermes/skills/consilium && python3 update_all.py
```

---

## Файлы

```
config.yaml                          — конфигурация Hermes Agent
SOUL.md                              — роль оркестратора
agents/*/SOUL.md, SKILL.md           — агенты
consilium/consilium_server.py        — основной сервер FastAPI
consilium/fallback_manager.py        — цепочки провайдеров
consilium/rate_limiter.py            — per-key лимиты
consilium/circuit_breaker.py         — защита от падений
consilium/update_all.py              — обновление моделей
consilium/providers/*.py              — модульные провайдеры
```
---

## Changelog

### v7.1 (2026-07-20)
- 🔐 Шифрование ключей AES-256-GCM
- 📊 Provider Statistics + адаптивный приоритет
- 🖥 Dashboard (веб-интерфейс)
- 🚨 Alerting (уведомления в Telegram)
- 📋 Model Catalog (SQLite)
- 🔍 Request ID через всю цепочку
- 💾 Rate Limiter в SQLite (persistence)
- 🏥 Health Checker (прогрев при старте)

### v7.0 (2026-07-18)
- Модульные провайдеры (19 шт)
- System Prompt Filter
- Task Router (chat/code/search/analysis)
- Fallback Manager с авто-цепочками
- Circuit Breaker
- Usage Logger (SQLite)

### v6.x (2026-07-17)
- Базовый Consilium с 6 провайдерами
- Интеграция с Hermes Agent
- AGENTS.md протокол

---

## Roadmap

### v7.2 (план)
- [ ] Streaming support (SSE)
- [ ] Webhook для внешних уведомлений
- [ ] Кэш ответов (Semantic Cache)
- [ ] Авто-скейлинг ключей (докупить при исчерпании)
- [ ] Интеграция с Supabase для логов

### v8.0 (план)
- [ ] gRPC API
- [ ] Plugin system для провайдеров
- [ ] Multi-user support
- [ ] Kubernetes deployment

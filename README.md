# Hermes + Consilium v7.2 — B2B Pipeline на VIM4 ARM64

## Железо
| Параметр | Значение |
|----------|----------|
| Платформа | Khadas VIM4 ARM64 |
| RAM | 8 GB |
| ОС | Ubuntu 24.04 |

## Архитектура
Telegram → Hermes Agent v0.19 → Consilium (:8765) → 12 провайдеров

## Возможности
- System Prompt Filter (513 символов)
- Task Router (chat/code/search/analysis)
- Fallback Manager (авто-цепочки, динамический DPS)
- Rate Limiter (per-key RPM/TPM/RPD/TPD, SQLite)
- Circuit Breaker (порог 5)
- Provider Statistics (DPS баллы, адаптивный приоритет)
- Health Checker (прогрев при старте)
- Dashboard (веб на :8765)
- Alerting (лог + Telegram опционально)
- Request ID трассировка

## Провайдеры (приоритет)
1. groq (3 ключа) — llama-3.3-70b-versatile
2. cloudflare (3 ключа) — @cf/meta/llama-3.2-3b-instruct
3. github (3 ключа) — gpt-4o-mini, gpt-4o
4. mistral (1 ключ) — mistral-large-latest
5. sambanova (2 ключа) — Meta-Llama-3.3-70B-Instruct
6. openrouter (3 ключа) — 344 модели

## Ключи (.env)
Формат: PREFIX_1..N. 401/402/403 → отключение. proxy: → прокси.

## Агенты
orchestrator → product-analyst → source-scout → parsing-engineer → parser (+ optimizer)

## Команды
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/

## Исправления v7.2 (23.07.2026)
✅ /v1/models context_length ✅ tool_calls UUID ✅ Cloudflare экстракторы
✅ alerting (лог) ✅ rate_limiter rpd/tpd ✅ filter_system_prompt
✅ COOLDOWN_STEPS 30-600с ✅ Мусор удалён
⚠️ GitHub azureml — update_all.py перезаписывает
⚠️ Hermes v0.19: 200 OK → "Provider failed" — расследуется

## Файлы
consilium/consilium_server.py, fallback_manager.py, rate_limiter.py,
circuit_breaker.py, provider_stats.py, router.py, dashboard.py,
alerting.py, health_checker.py, update_all.py, providers/*.py,
config.yaml, SOUL.md, HERMES_FULL_CONTEXT.md


## Статус (23.07.2026 16:15)
- ✅ SOUL.md в ~/.hermes/ заменён на оркестратора (согласно докам v0.19)
- ✅ Фильтр system prompt: 19621 → 689 символов
- ✅ Обрезка истории: system + последнее user-сообщение
- ✅ GitHub: models.github.ai/inference + gpt-4o-mini/gpt-4o
- ✅ Cloudflare: только 2 chat-модели
- ✅ record_request + реальный key_index
- ✅ requirements.txt + .gitignore
- ⚠️ Все провайдеры 413/401/402/429 — проблема в ключах/лимитах
- 🔄 Передано на аудит ИИ (23.07.2026)


## Статус (23.07.2026 19:45)
### Логирование (внедрено)
- 📥 REQ — входящий запрос
- ✂️ FILTER — после фильтрации
- 🎯 ROUTER — классификация задачи
- → {provider}/{model} — каждая попытка
- ❌ ALL DEAD — все отказали
- ✅ DONE — успешный ответ

### Исправления (15 шт)
- FreeLLMAPI-style группировка провайдеров в fallback
- tools проброшены в call_provider
- circuit_breaker для HTTP-ошибок
- rate_limiter.is_available перед вызовом
- mark_429 escalation
- DPS балльная система
- content=null при tool_calls
- tool_calls[].id → UUID
- Фильтр лишних полей
- /v1/models с context_length
- GitHub модели исправлены
- api_mode: chat_completions
- OVERALL_DEADLINE
- sticky_sessions очистка
- key_indexes lock

### Текущая проблема
Fallback перебирает 24 модели OpenRouter и упирается в лимит попыток.
Нужна перестройка цепочки на вложенную структуру (как в FreeLLMAPI).

### Передано на аудит ИИ


## v7.2 (23.07.2026) — Model Registry + FreeLLMAPI-style Fallback

### Model Registry (model_registry.py)
- SQLite база с классификацией всех моделей
- Автоматический отбор: контекст >= 128K, исключены embedding/audio/vision
- 40 из 47 моделей прошли отбор
- Теги: chat, code, search, analysis
- Перепроверка лимитов при каждом обновлении (GET /v1/models бесплатный)

### Fallback Manager v2 (FreeLLMAPI-style)
- Группировка по провайдерам: provider → keys → models (max 3)
- Перебор ключей внутри провайдера перед переходом к следующему
- Цепочки строятся из Model Registry (только enabled модели)
- chat: 20 моделей от 9 провайдеров

### Исправления (22.07-23.07)
- GitHub модели: azureml:// → gpt-4o-mini, gpt-4o
- MAX_MODELS_PER_PROVIDER = 3
- Модели сортируются: chat-модели первыми
- rate_limits.db очищен

### Логирование
- 📥 REQ — входящий запрос
- ✂️ FILTER — после фильтрации
- 🎯 ROUTER — классификация задачи
- [{request_id}] → provider/model — вызов провайдера
- [{request_id}] ✅/❌ — результат

### Статус
- ✅ 5 файлов компилируются без ошибок
- ✅ 9 провайдеров активно
- ⚠️ Hermes v0.19: "Provider failed after retries" — провайдеры исчерпаны

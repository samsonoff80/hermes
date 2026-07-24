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



## v7.2 (23.07.2026) — Model Registry + FreeLLMAPI Fallback

### Что сделано
- Model Registry (SQLite): классификация моделей, автоотбор (>=128K ctx, исключены embedding/audio/vision), 40/47 моделей
- Fallback Manager v2: provider → keys → models (max 3), перебор ключей
- Цепочки из реестра: chat 20, code 13, search 8, analysis 4
- GitHub модели исправлены (azureml:// → gpt-4o-mini)
- Все 5 файлов компилируются без ошибок
- 9 провайдеров активно

### Логирование
📥 REQ → ✂️ FILTER → 🎯 ROUTER → [{id}] → provider/model → ✅/❌

#


## v8.0 (23.07.2026) — Consilium облегчённый, интеграция с Hermes v0.19

### Что изменилось
- Удалено 18 файлов (providers/, rate_limiter, fallback_manager, circuit_breaker, update_all, key_encryption, router)
- Ротация ключей → встроенная credential_pool_strategies (round_robin, least_used)
- Fallback цепочка → встроенная fallback_providers: в config.yaml
- Модели провайдеров → встроенный model catalog + custom_providers:
- Circuit breaker → встроенный retry (3 попытки) → fallback

### Что осталось в Consilium (5 файлов, ~500 строк)
- System Prompt Filter — вырезает технические блоки Hermes
- Task Router — классифицирует запросы (chat/code/search/analysis)
- Model Registry — фильтрует модели (>=128K, исключает embedding/audio/vision)
- Usage Logger — SQLite статистика токенов
- Provider Stats — мониторинг успешности и задержек
- Dashboard — веб-интерфейс на :8765
- Alerting — уведомления в Telegram при сбоях

#
## Статус (24.07.2026) — ФАКТЫ

### Файлы Consilium (11 шт, все компилируются)
consilium_server.py, model_registry.py, provider_stats.py,
rate_limiter.py, fallback_manager.py, dashboard.py, filter_models.py,
alerting.py, circuit_breaker.py, health_checker.py, router.py

### Провайдеры (14 шт)
openrouter (3 ключа), groq (3), mistral (3), github (3),
sambanova (3), hf (2), cloudflare (3), deepinfra (3),
aihorde (keyless), siliconflow, together, reka

### config.yaml (Hermes v0.19)
- provider: custom → 127.0.0.1:8765/v1
- api_mode: chat_completions
- api_key: sk-consilium
- НЕТ credential_pool_strategies (один провайдер — Consilium)
- НЕТ fallback_providers (один провайдер — Consilium)

### Что делает Consilium (уникальные фичи)
- System Prompt Filter (вырезает технические блоки Hermes)
- Task Router (chat/code/search/analysis)
- Model Registry (фильтр >=128K, исключает embedding/audio)
- Ротация ключей (round_robin через rate_limiter.py)
- Fallback цепочка (fallback_manager.py)
- Usage Logger (SQLite)
- Provider Stats (компактный)
- Dashboard (веб-интерфейс)

### Что делает Hermes (встроенные фичи)
- Prompt caching (автоматически для Anthropic/OpenRouter)
- Context compression (автоматически)
- Memory (MEMORY.md + USER.md)
- Skills system (SKILL.md)
- Delegation (delegate_task)

### Экономия
- Код: ~1500 → ~700 строк (53% сокращение)
- Удалено: update_all.py, key_encryption.py

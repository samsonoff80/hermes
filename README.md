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

## Рабочие провайдеры (приоритет)
1. groq (3 ключа) — llama-3.3-70b-versatile
2. cloudflare (3 ключа) — @cf/meta/llama-3.2-3b-instruct
3. github (3 ключа) — gpt-4o-mini, gpt-4o
4. mistral (1 ключ) — mistral-large-latest
5. sambanova (2 ключа) — Meta-Llama-3.3-70B-Instruct
6. openrouter (3 ключа) — 344 модели

## Ключи (.env)
Формат: PREFIX_1, PREFIX_2, ... PREFIX_N (любое количество)
401/402/403 → ключ отключается
Прокси: если ключ начинается с 'proxy:' → через прокси

## 6 Агентов B2B-пайплайна
orchestrator → product-analyst → source-scout → parsing-engineer → parser (+ optimizer)

## Команды
```bash
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/usage/today
curl -s http://127.0.0.1:8765/  # Dashboard
Исправления v7.2 (23.07.2026)
✅ /v1/models с context_length

✅ tool_calls UUID

✅ Cloudflare экстракторы

✅ alerting (лог)

✅ rate_limiter rpd/tpd проверка

✅ filter_system_prompt (сохраняет роль оркестратора)

✅ mark_success с реальным key_index

✅ COOLDOWN_STEPS уменьшены (30-600с)

✅ Мусор удалён (providers_pkg, .backup, .old)

⚠️ GitHub azureml — известный баг (update_all.py перезаписывает)

⚠️ Hermes v0.19: 200 OK → "Provider failed" — расследуется

Файлы
consilium/consilium_server.py, fallback_manager.py, rate_limiter.py,
circuit_breaker.py, provider_stats.py, alerting.py, router.py,
key_encryption.py, providers/*.py, config.yaml

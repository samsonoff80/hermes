# Hermes + Consilium v7.2 — B2B Pipeline на VIM4 ARM64

## Железо
| Параметр | Значение |
|----------|----------|
| Платформа | Khadas VIM4 ARM64 |
| RAM | 8 GB |
| ОС | Ubuntu 24.04 |

## Архитектура
Telegram → Hermes Agent v0.19 → Consilium (:8765) → Провайдеры

## Возможности
- System Prompt Filter (513 символов)
- Task Router (chat/code/search/analysis)
- Fallback Manager (авто-цепочки из 12 провайдеров)
- Rate Limiter (per-key, SQLite)
- Circuit Breaker (порог 5)
- Provider Statistics (DPS баллы)
- Health Checker (прогрев при старте)
- Dashboard (веб на :8765)
- Alerting (Telegram)

## Рабочие провайдеры (приоритет)
1. groq (3 ключа) — llama-3.3-70b-versatile
2. cloudflare (3 ключа) — @cf/meta/llama-3.2-3b-instruct
3. github (3 ключа) — gpt-4o-mini, gpt-4o
4. mistral (1 ключ) — mistral-large-latest
5. sambanova (2 ключа) — Meta-Llama-3.3-70B-Instruct
6. openrouter (3 ключа) — 344 модели (50 запросов/день)

## Команды
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/

## Файлы (активные)
consilium/consilium_server.py, fallback_manager.py, rate_limiter.py,
circuit_breaker.py, provider_stats.py, router.py, dashboard.py,
alerting.py, health_checker.py, update_all.py, providers/*.py,
config.yaml, agents/*/SOUL.md

## Статус (23.07.2026)
Работает: Cloudflare 200 OK, фильтр 19641→513 символов

# HERMES B2B PIPELINE + CONSIlium v8.0 — ПОЛНАЯ КАРТА (23.07.2026 22:35)

## ЖЕЛЕЗО
VIM4 ARM64 8GB Ubuntu 24.04, IP 192.168.10.14

## АРХИТЕКТУРА (ПОСЛЕ МИГРАЦИИ)
Telegram → Hermes Agent v0.19 → провайдеры напрямую
  └── Consilium (:8765) — System Prompt Filter + Task Router + Usage Logger + Dashboard

## CONSIlium v8.0 (ОБЛЕГЧЁННЫЙ)
5 файлов: consilium_server.py, model_registry.py, provider_stats.py, dashboard.py, alerting.py
Удалены: providers/ (12), rate_limiter, fallback_manager, circuit_breaker, update_all, key_encryption, router

## HERMES AGENT v0.19 (The Quicksilver Release)
- credential_pool_strategies: round_robin / least_used
- fallback_providers: groq → cloudflare → github → mistral → sambanova → aihorde → openrouter
- custom_providers: groq, cloudflare, github, mistral, sambanova, aihorde
- Встроенные: openrouter, huggingface, deepseek
- 18 ключей в auth.json

## ПОТОК ЗАПРОСА
Telegram → Hermes v0.19 → Consilium → System Prompt Filter → Task Router → модель → Hermes → провайдер

## 6 АГЕНТОВ
orchestrator → product-analyst → source-scout → parsing-engineer → parser (+ optimizer)
SOUL.md + SKILL.md + PROGRESS.md
Протокол: read_file → delegate_task → результат

## CONFIG.YAML
model.provider: custom → 127.0.0.1:8765/v1
api_mode: chat_completions, context: 128K
agent.disabled_toolsets: [memory]

## КОМАНДЫ
Проверка: curl -s http://127.0.0.1:8765/health
Usage: curl -s http://127.0.0.1:8765/usage/today
Логи: tail -f ~/.hermes/logs/consilium.log
Перезапуск: fuser -k 8765/tcp; pkill -9 -f "hermes_cli.main|hermes-agent gateway|consilium_server"; systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent

## GITHUB
main: v8.0 (облегчённый)
v7.2: резервная копия

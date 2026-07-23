# HERMES B2B + Consilium v8.0 — ПОЛНАЯ КАРТА (23.07.2026 22:35)

## ЖЕЛЕЗО
VIM4 ARM64 8GB Ubuntu 24.04, IP 192.168.10.14

## АРХИТЕКТУРА
Telegram → Hermes Agent v0.19 → Провайдеры (через custom_providers + fallback_providers + credential_pools)
Consilium (:8765) — облегчённый прокси: ТОЛЬКО System Prompt Filter + Task Router + Usage Logger + Dashboard
Hermes управляет: ключами, fallback, каталогом моделей, таймаутами

## HERMES v0.19 — КОНФИГ
config.yaml:
  api_mode: chat_completions
  provider: groq, default: llama-3.3-70b-versatile
  custom_providers: groq, cloudflare, github, mistral, sambanova, aihorde
  fallback_providers: groq → cloudflare → github → mistral → sambanova → aihorde → openrouter
  credential_pool_strategies: round_robin (все), least_used (openrouter)
  Встроенные: openrouter, huggingface, deepseek (через env переменные)

## КЛЮЧИ (18 шт, в auth.json)
groq: 3 ключа, cloudflare: 3 ключа + 3 account_id, github: 3 ключа, mistral: 3 ключа, sambanova: 3 ключа, openrouter: 3 ключа

## CONSIlium v8.0 (5 файлов)
consilium/consilium_server.py — System Prompt Filter + Task Router + логирование
consilium/model_registry.py — фильтр моделей >=128K, исключение embedding/audio/vision
consilium/provider_stats.py — счётчик успех/фейл (компактный)
consilium/dashboard.py — веб-интерфейс :8765/
consilium/alerting.py — уведомления в Telegram

## УДАЛЕНО (18 файлов)
providers/ (12), rate_limiter.py, fallback_manager.py, circuit_breaker.py, update_all.py, key_encryption.py, router.py

## 6 АГЕНТОВ
agents/orchestrator/ — SOUL.md + SKILL.md + PROGRESS.md
agents/optimizer/ — SOUL.md + SKILL.md + PROGRESS.md
agents/product-analyst/ — SOUL.md + SKILL.md + PROGRESS.md
agents/source-scout/ — SOUL.md + SKILL.md + PROGRESS.md + MEMORY.md
agents/parsing-engineer/ — SOUL.md + SKILL.md + PROGRESS.md
agents/parser/ — SOUL.md + SKILL.md + PROGRESS.md + pipeline_v55_final.py

## GITHUB
samsonoff80/hermes: main (v8.0), v7.2 (резерв)
Fireglow1980/hermes-full-system: consilium-v7 (старая версия)

## РАБОЧИЕ ПРОВАЙДЕРЫ (23.07)
groq (3/3), github (3/3), cloudflare (3/3), mistral (1/3), sambanova (2/3)
Нерабочие: openrouter (429), deepinfra (402), hf (402)

## ПОЛНЫЙ ПЕРЕЗАПУСК
fuser -k 8765/tcp 2>/dev/null
pkill -9 -f "hermes_cli.main|hermes-agent gateway|consilium_server" 2>/dev/null
sleep 2
rm -f ~/.hermes/state.db* ~/.hermes/auth.json ~/.hermes/models_dev_cache.json 2>/dev/null
rm -rf ~/.hermes/sessions/* 2>/dev/null
find ~/.hermes -name "__pycache__" -exec rm -rf {} + 2>/dev/null
systemctl --user restart hermes-consilium && sleep 2
systemctl --user restart hermes-agent

## ПРОВЕРКА
curl -s http://127.0.0.1:8765/health
ps aux | grep "[h]ermes" | grep -v grep
tail -20 ~/.hermes/logs/consilium.log

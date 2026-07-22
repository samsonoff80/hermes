# Hermes + Consilium v7.2 — B2B Pipeline на VIM4 ARM64

## Что это?
Hermes Agent v0.19 (Nous Research) — автономный AI-агент через Telegram.
Consilium — собственный LLM-прокси (FastAPI) с 9 провайдерами, фильтром system prompt, Task Router, DPS балльной системой.
B2B Pipeline — автоматизированный сбор и анализ данных о производителях пищевого сырья в 9 странах СНГ.

## Быстрый старт
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
Статус (23.07.2026)

· Система работает: Cloudflare 200 OK
· System prompt фильтр: 493 chars
· 5 рабочих провайдеров: groq, github, cloudflare, mistral, sambanova
· Код от Claude (ветка audit/consilium-v7.2-fixes) применён
· Alerting отключён (спамил на 401)
· Основная проблема: Hermes v0.19 не принимает ответ (200 OK -> Provider failed)

Архитектура

Telegram -> Hermes Agent v0.19 -> Consilium (:8765) -> 9 провайдеров (5 рабочих)

Провайдеры (приоритет динамический DPS)

Провайдер Ключей Модели
groq 3 llama-3.3-70b-versatile
cloudflare 1 @cf/meta/llama-3.2-3b-instruct
github 3 gpt-4o-mini
mistral 1 mistral-large-latest
sambanova 2 Meta-Llama-3.3-70B-Instruct

6 Агентов

orchestrator -> product-analyst -> source-scout -> parsing-engineer -> parser (+ optimizer)
Каждый: SOUL.md + SKILL.md + PROGRESS.md

Файлы

config.yaml, SOUL.md, agents//SOUL.md,
consilium/consilium_server.py, fallback_manager.py, rate_limiter.py,
circuit_breaker.py, provider_stats.py, providers/.py

Команды

curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/usage/today
tail -f ~/.hermes/logs/consilium.log
Полный перезапуск

fuser -k 8765/tcp 2>/dev/null
pkill -9 -f "hermes_cli.main|hermes-agent gateway|consilium_server" 2>/dev/null
sleep 2
rm -f ~/.hermes/state.db* ~/.hermes/auth.json
rm -rf ~/.hermes/sessions/*
rm -f ~/.hermes/skills/consilium/rate_limits.db
find ~/.hermes -name "__pycache__" -exec rm -rf {} + 2>/dev/null
systemctl --user restart hermes-consilium && sleep 2
systemctl --user restart hermes-agent

# Hermes + Consilium v7.2 — B2B Pipeline на VIM4 ARM64

## Что это?
**Hermes Agent v0.19** (Nous Research) — автономный AI-агент через Telegram. Вызывает инструменты, делегирует задачи. Работает как оркестратор B2B-пайплайна.
**Consilium** — собственный LLM-прокси (FastAPI). Принимает запросы от Hermes, выбирает оптимальную модель среди 9 провайдеров, фильтрует system prompt, считает токены, переключается при ошибках.
**B2B Pipeline** — автоматизированный сбор и анализ данных о производителях пищевого сырья в 9 странах СНГ. 6 агентов последовательно анализируют продукты, ищут источники, парсят каталоги и очищают данные.

## Железо
Khadas VIM4 ARM64, 8 GB RAM, Ubuntu 24.04, IP 192.168.10.14

## Архитектура
Telegram → Hermes Agent v0.19 → Consilium (:8765 FastAPI) → Провайдеры

Consilium: System Prompt Filter → Task Router (chat/code/search/analysis) → Fallback Manager → Rate Limiter → Circuit Breaker → Usage Logger (SQLite)

## Провайдеры (23.07.2026)
5 рабочих: groq (3 ключа), github (3), cloudflare (3), mistral (1), sambanova (1)
Нерабочие: openrouter (429), deepinfra (402), hf (402)

## Система
- Код: Claude Fix (22.07.2026), все файлы компилируются
- DPS балльная система с байесовским сглаживанием
- System prompt фильтр: 19641→513 символов
- Health checker при старте
- Alerting отключён
- Ключи: PREFIX_1..N, ротация get_next_key() + mark_402
- Приоритет: динамический DPS (байесовское сглаживание)

## 6 Агентов
orchestrator → product-analyst → source-scout → parsing-engineer → parser (+ optimizer)
Каждый: SOUL.md + SKILL.md + PROGRESS.md

## Команды
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/usage/today

## Полный перезапуск
fuser -k 8765/tcp 2>/dev/null; pkill -9 -f "hermes_cli.main|hermes-agent gateway|consilium_server" 2>/dev/null; sleep 2; rm -f ~/.hermes/state.db* ~/.hermes/auth.json ~/.hermes/models_dev_cache.json ~/.hermes/hermes-agent/models_dev_cache.json 2>/dev/null; rm -rf ~/.hermes/sessions/* 2>/dev/null; rm -f ~/.hermes/skills/consilium/rate_limits.db ~/.hermes/skills/consilium/fallback_chain.json ~/.hermes/skills/consilium/provider_state.json 2>/dev/null; find ~/.hermes -name "__pycache__" -exec rm -rf {} + 2>/dev/null; systemctl --user restart hermes-consilium && sleep 2 && systemctl --user restart hermes-agent && sleep 2 && echo "Процессов: $(ps aux | grep '[h]ermes' | grep -v grep | wc -l)" && curl -s http://127.0.0.1:8765/health

## Файлы
config.yaml, SOUL.md, agents/*/SOUL.md, consilium/consilium_server.py, fallback_manager.py, rate_limiter.py, circuit_breaker.py, provider_stats.py, providers/*.py

## Известные баги
- update_all.py перезаписывает github.py → azureml://
- Hermes v0.19: 200 OK → "Provider failed" (основная проблема)
- COOLDOWN_STEPS до 6ч
- Telegram токен в логах

## Статус (23.07.2026)
✅ Система работает: Cloudflare 200 OK
✅ System prompt фильтр: 493 chars
✅ 5 рабочих провайдеров
⚠️ Hermes v0.19 не принимает ответ

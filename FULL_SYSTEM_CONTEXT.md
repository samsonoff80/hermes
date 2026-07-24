# HERMES + CONSILIUM v7.2 — ПОЛНАЯ КАРТА СИСТЕМЫ (24.07.2026)

## ЖЕЛЕЗО
VIM4 ARM64 8GB Ubuntu 24.04, IP 192.168.10.14

## АРХИТЕКТУРА
Telegram → Hermes Agent v0.19 → Consilium (:8765) → 12 провайдеров

## CONSIlium (:8765)
FastAPI сервер. Принимает OpenAI-совместимые запросы, фильтрует system prompt, классифицирует задачи, выбирает провайдера через DPS-приоритет, отправляет запрос, возвращает ответ.

### Компоненты:
- System Prompt Filter — денилист блоков Hermes
- Task Router — chat/code/search/analysis
- Fallback Manager — 42 модели chat, DPS-сортировка
- Rate Limiter — per-key RPD/TPD, cooldown 90с→6ч
- Circuit Breaker — 5 ошибок → 60с блокировка
- Provider Statistics — success_rate/latency
- Model Registry — автообновление из API

### Провайдеры (12):
groq (3 ключа), github (3), cloudflare (3), mistral (1), sambanova (2), openrouter (3), deepinfra (3), hf (2), siliconflow, together, reka, aihorde (keyless)

## HERMES AGENT v0.19
- provider: custom → http://127.0.0.1:8765/v1
- 6 агентов: orchestrator, optimizer, product-analyst, source-scout, parsing-engineer, parser
- Каждый: SOUL.md + SKILL.md + PROGRESS.md
- System prompt: SOUL.md + AGENTS.md → фильтруется Consilium

## КЛЮЧЕВЫЕ ФАЙЛЫ
config.yaml, SOUL.md, agents/*/SOUL.md,
consilium/consilium_server.py, fallback_manager.py,
rate_limiter.py, circuit_breaker.py, update_all.py,
provider_stats.py, model_registry.py, providers/*.py

## ПОВЕДЕНИЕ ПРИ ОШИБКАХ
- 401 → cooldown 1ч
- 402/403 → вечный disabled
- 413 → следующий провайдер
- 429 → cooldown 90с→5м→15м→1ч→6ч
- 5xx/network → circuit breaker

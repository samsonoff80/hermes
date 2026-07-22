# HERMES B2B + Consilium v7.1 (Claude Fix) — ПОЛНАЯ КАРТА (23.07.2026)

## ЖЕЛЕЗО
VIM4 ARM64 8GB Ubuntu 24.04, IP 192.168.10.14

## АРХИТЕКТУРА
Telegram → Hermes Agent v0.19 → Consilium (:8765) → 9 провайдеров (5 рабочих)

## CONSIlium v7.1 (Claude Fix)
Код от Claude применён 22.07.2026. Все 26 файлов компилируются.
- response normalizer (strict OpenAI)
- DPS балльная система с байесовским сглаживанием
- Health checker: 7/9 провайдеров живы при старте
- Alerting отключён (спамил на 401)
- System prompt фильтр: 493 chars

Рабочие провайдеры (23.07): groq, github, cloudflare, mistral (ключ 3), sambanova (ключ 2)
Нерабочие: openrouter (429 лимит), deepinfra (402), hf (402)

## HERMES AGENT v0.19 (The Quicksilver Release)
Обновлён с v0.18. Delivery-obligation ledger, tool definitions fix.
provider: custom → http://127.0.0.1:8765/v1
api_mode: chat_completions

## 6 АГЕНТОВ
orchestrator, optimizer, product-analyst, source-scout, parsing-engineer, parser
SOUL.md + SKILL.md + PROGRESS.md

## КЛЮЧЕВЫЕ ФАЙЛЫ
config.yaml, AGENTS.md, agents/orchestrator/SOUL.md
consilium/consilium_server.py, fallback_manager.py, rate_limiter.py, provider_stats.py

## ПОЛНЫЙ ПЕРЕЗАПУСК
fuser -k 8765/tcp 2>/dev/null; pkill -9 -f "hermes_cli.main|hermes-agent gateway|consilium_server" 2>/dev/null; sleep 2; rm -f ~/.hermes/state.db* ~/.hermes/auth.json ~/.hermes/models_dev_cache.json ~/.hermes/hermes-agent/models_dev_cache.json 2>/dev/null; rm -rf ~/.hermes/sessions/* 2>/dev/null; rm -f ~/.hermes/skills/consilium/rate_limits.db ~/.hermes/skills/consilium/fallback_chain.json ~/.hermes/skills/consilium/provider_state.json 2>/dev/null; find ~/.hermes -name "__pycache__" -exec rm -rf {} + 2>/dev/null; systemctl --user restart hermes-consilium && sleep 2 && systemctl --user restart hermes-agent

## ИЗВЕСТНЫЕ БАГИ
- update_all.py перезаписывает github.py azureml:// моделями
- Hermes v0.19 не принимает ответ при 200 OK (основная проблема)
- Telegram бот токен был в логах — скомпрометирован
- COOLDOWN_STEPS до 6ч — всей цепочке конец

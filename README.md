# Hermes + Consilium v8 — B2B Pipeline на VIM4 ARM64

## Железо
| Параметр | Значение |
|----------|----------|
| Платформа | Khadas VIM4 ARM64 |
| RAM | 8 GB |
| ОС | Ubuntu 24.04 |

## Архитектура
Telegram → Hermes Agent v0.19 → Consilium (:8765) → 12 провайдеров

## Что нового в v8 (24.07.2026)

### Реструктуризация на основе документации Hermes v0.19

**Передали Hermes (встроенные фичи):**
- Ротация ключей → `credential_pool_strategies: round_robin`
- Fallback цепочка → `fallback_providers:` в config.yaml
- Retry (3 попытки) → встроенный fallback (вместо circuit_breaker)
- Обновление моделей → каталог Hermes (автообновление)

**Оставили в Consilium (уникальные фичи):**
- System Prompt Filter (вырезает технические блоки)
- Task Router (chat/code/search/analysis)
- Model Registry (фильтр >=128K, исключение embedding/audio/vision)
- Usage Logger (SQLite, статистика токенов)
- Provider Stats (компактный мониторинг)
- Dashboard (веб-интерфейс)

**Удалили:**
- `key_encryption.py` — Hermes не поддерживает шифрование .env
- `circuit_breaker.py` — заменён на встроенный retry
- `update_all.py` — заменён на filter_models.py
- `router.py` — дублировал логику

**Экономия:**
- Код: ~1500 → ~500 строк (66% сокращение)
- Файлы: 30 → 8 (73% сокращение)

## Возможности
- System Prompt Filter (513 символов после фильтрации)
- Task Router (chat/code/search/analysis)
- Model Registry (фильтр 128K, автоотбор)
- Rate Limiter (минимальный)
- Fallback Manager (минимальный)
- Provider Stats (DPS баллы)
- Dashboard (веб на :8765)
- Request ID трассировка

## Провайдеры (приоритет)
| # | Провайдер | Ключей | Модели | RPD |
|---|-----------|--------|--------|-----|
| 1 | groq | 3 | llama-3.3-70b-versatile | 1000 |
| 2 | cloudflare | 3 | @cf/meta/llama-3.2-3b-instruct | 100 |
| 3 | github | 3 | gpt-4o-mini, gpt-4o | 50 |
| 4 | mistral | 1 | mistral-large-latest | 10000 |
| 5 | sambanova | 2 | Meta-Llama-3.3-70B-Instruct | 500 |
| 6 | openrouter | 3 | 344 модели (фильтр 128K) | 50 |

## Ключи (.env)
Формат: PREFIX_1..N. 401/402/403 → отключение. proxy: → прокси.
Hermes сам ротирует ключи через `credential_pool_strategies`.

## Агенты
orchestrator → product-analyst → source-scout → parsing-engineer → parser (+ optimizer)

## Команды
```bash
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/

Данные по Hermes v0.19 (для разработчиков)
Что умеет Hermes (нам не нужно делать):
credential_pool_strategies: fill_first, round_robin, least_used, random
Cooldown: 5 мин (401), 1 час (429/402). Персистентность в auth.json
fallback_providers: упорядоченный список, реактивный (после 429)
Prompt caching: авто (Anthropic/OpenRouter 1h, Qwen 5m)
System prompt: 3-tier сборка (stable→context→volatile)
context_file_max_chars: 20000
Context files: .hermes.md → AGENTS.md → CLAUDE.md → .cursorrules (один)
Skills ≠ AGENTS.md (комплементарны)
SecretSource: Bitwarden/1Password (нет шифрования .env)
Что НЕ умеет Hermes (нам нужно самим):
Фильтрация system prompt (технические блоки)
Классификация задач (chat/code/search/analysis)
Фильтрация моделей по контексту (>=128K)
Учёт latency/success rate (least_used только счётчик)
Превентивный учёт RPD/TPD (только реактивный после 429)
Встроенные провайдеры Hermes:
OpenRouter ✅, HuggingFace ✅, DeepSeek ✅ — first-class
Groq ❌, Cloudflare ❌, GitHub ❌, Mistral ❌, SambaNova ❌ — custom
Исправления (история)
v7.2 (23.07): Model Registry + FreeLLMAPI Fallback
v7.1 (22.07): 11 критических исправлений от 4 ИИ
v7.0 (21.07): all_entries.append fix, tool_calls UUID, фильтр полей
v6.x: Базовый Consilium
Статус (24.07.2026)
✅ 8 файлов компилируются
✅ 12 провайдеров
✅ System Prompt Filter: 513 chars
⚠️ provider_stats — проверить SQL
⚠️ filter_models.py — ждёт кэш Hermes
Файлы
consilium/consilium_server.py, model_registry.py, provider_stats.py,
rate_limiter.py, fallback_manager.py, dashboard.py, filter_models.py,
providers/*.py, config.yaml, README.md, logs

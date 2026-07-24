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
- Ротация ключей → credential_pool_strategies: round_robin
- Fallback цепочка → fallback_providers: в config.yaml
- Retry → встроенный (вместо circuit_breaker)
- Обновление моделей → каталог Hermes (автообновление)

**Оставили в Consilium (уникальные фичи):**
- System Prompt Filter (вырезает технические блоки)
- Task Router (chat/code/search/analysis)
- Model Registry (фильтр >=128K)
- Usage Logger (SQLite)
- Provider Stats (компактный)
- Dashboard (веб-интерфейс)

**Удалили (18 файлов):**
- providers/*, rate_limiter, fallback_manager, circuit_breaker, update_all, key_encryption, router

**Экономия:**
- Код: ~1500 → ~500 строк (66% сокращение)
- Файлы: 30 → 8 (73% сокращение)

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
Hermes сам ротирует ключи через credential_pool_strategies.

## Агенты
orchestrator → product-analyst → source-scout → parsing-engineer → parser (+ optimizer)

## Команды
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/

## Файлы
consilium/consilium_server.py, model_registry.py, provider_stats.py,
rate_limiter.py, fallback_manager.py, dashboard.py, filter_models.py,
config.yaml, README.md, logs/

## Статус (24.07.2026)
✅ 8 файлов компилируются
✅ 12 провайдеров
✅ System Prompt Filter: 513 chars
⚠️ provider_stats — SQL fix pending
⚠️ filter_models.py — ждёт кэш Hermes

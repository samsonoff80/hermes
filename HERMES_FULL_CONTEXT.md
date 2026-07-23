# HERMES B2B PIPELINE — СХЕМА РАБОТЫ (23.07.2026)

## ПОТОК ЗАПРОСА
Пользователь (Telegram) → Hermes Gateway v0.19 → Consilium (:8765) → Провайдер → ответ

## СЕССИИ
Новая сессия: AGENTS.md загружается из CWD Hermes (~/.hermes/hermes-agent/)
System prompt: SOUL.md + AGENTS.md (493 chars после фильтра)
Recovery: каждый слой читает PROGRESS.md → CURRENT

## Delegate_task
1. read_file(SOUL.md) + read_file(SKILL.md) + read_file(PROGRESS.md)
2. delegate_task(goal, context, toolsets=["file","terminal"])
3. Ждать результат
4. DONE → следующий слой
Цепочка: product-analyst → source-scout → parsing-engineer → parser

## CONFIG.YAML (ключевые секции)
model.provider: custom → 127.0.0.1:8765/v1
api_mode: chat_completions
context: 128K, compression: 0.7
agent.disabled_toolsets: [memory]

## ПРОВАЙДЕРЫ (Consilium)
Приоритет: динамический DPS (байесовское сглаживание)
Ключи: PREFIX_1..N (любое количество)
Ротация: get_next_key() → mark_402 при 401/403

## КОМАНДЫ
Проверка: curl -s http://127.0.0.1:8765/health
Usage: curl -s http://127.0.0.1:8765/usage/today
Логи: tail -f ~/.hermes/logs/consilium.log




## Статус на 2026-07-23 21:11
- Model Registry: SQLite, 40/47 моделей
- Fallback Manager v2: FreeLLMAPI-style
- 10 файлов синхронизированы
- 5/5 компилируются
- 9 провайдеров активно

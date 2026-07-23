# КОНТЕКСТ ДЛЯ НОВОГО ЧАТА — Consilium v8 Core

## ЧТО СДЕЛАНО
- Consilium v7.2 работает но нестабильно (Hermes "Provider failed after retries")
- Прошли 3 раунда аудита с 4 ИИ (Claude, Devin, Mistral, Qwen)
- Найдено 15+ критических багов, 11 исправлено
- Основная проблема: system prompt filter, response format, rate limits

## НОВАЯ АРХИТЕКТУРА v8
Разделяем Consilium на ядро (чистый прокси) и плагины:

consilium/
├── core/                    # Чистый прокси (как FreeLLMAPI)
│   ├── server.py            # FastAPI, endpoints
│   ├── proxy.py             # call_provider, ротация ключей
│   ├── providers/           # Модульные провайдеры (12 шт)
│   ├── rate_limiter.py      # Per-key tracking
│   └── circuit_breaker.py   # Защита от падений
│
├── plugins/                 # Наши фичи (подключаемые)
│   ├── prompt_filter.py     # System prompt filter
│   ├── task_router.py       # chat/code/search/analysis
│   ├── agents_injector.py   # AGENTS.md инъекция
│   ├── response_normalizer.py # OpenAI compliance
│   ├── provider_stats.py    # DPS балльная система
│   ├── dashboard.py         # Веб-интерфейс
│   ├── alerting.py          # Telegram уведомления
│   └── usage_logger.py      # SQLite логирование
│
└── config.yaml              # Конфиг плагинов (вкл/выкл)

## ПРИНЦИП
- Ядро работает без плагинов — чистый прокси
- Плагины включаются в конфиге
- Каждый плагин — независимый файл
- Плагин может перехватывать request/response через middleware

## ПЛАН
1. Довести до стабильности ядро (прокси + провайдеры)
2. По одному подключать плагины и отлаживать

## ТЕКУЩИЕ ПРОБЛЕМЫ
- Hermes v0.19: 200 OK → "Provider failed"
- System prompt filter нестабилен
- Response format: лишние поля, tool_calls.id, reasoning_content
- Rate limits исчерпаны

## КЛЮЧЕВЫЕ ФАЙЛЫ
- Репозиторий: https://github.com/samsonoff80/hermes (ветка main)
- Новая ветка: v8-core
- Конфиг Hermes: config.yaml
- System prompt: SOUL.md, AGENTS.md
- Логи: logs/consilium_latest.log

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Что это за репозиторий

Снимок системы, развёрнутой на Khadas VIM4 (ARM64, 8 GB, Ubuntu 24.04) в каталоге `/home/khadas/.hermes/`. Корень репозитория примерно соответствует `~/.hermes/` на устройстве, **кроме** `consilium/` — на устройстве он лежит в `~/.hermes/skills/consilium/` (этот путь захардкожен в коде, см. ниже).

Три слабо связанные части:

| Часть | Что это |
|-------|---------|
| `consilium/` | LLM-прокси на FastAPI (порт 8765), OpenAI-совместимый API поверх 12 провайдеров |
| `config.yaml`, `SOUL.md` | Конфигурация Hermes Agent v0.19 (Nous Research) — он ходит в Consilium как в `custom` провайдера |
| `agents/` | 6 агентов B2B-пайплайна (SOUL.md / SKILL.md / PROGRESS.md + скрипты и данные) |

Разработка ведётся на Windows, целевая среда — ARM64 Linux с `systemctl --user`. Команды из README (`systemctl --user restart hermes-consilium`) выполняются на устройстве, локально они не работают.

## Команды

```bash
# Зависимости. ВНИМАНИЕ: requirements.txt содержит строку `sqlite3`, которой нет на PyPI —
# pip install -r requirements.txt упадёт. Ставить остальное вручную:
pip install "fastapi>=0.100" "uvicorn>=0.23" "httpx>=0.25" "python-dotenv>=1.0" "cryptography>=41"

# Запуск Consilium ТОЛЬКО из каталога consilium/ (см. «Плоские импорты» ниже)
cd consilium && python consilium_server.py     # uvicorn 0.0.0.0:8765

# Проверка
curl -s http://127.0.0.1:8765/health           # ключи по провайдерам
curl -s http://127.0.0.1:8765/usage/today      # токены за сутки из usage.db
curl -s http://127.0.0.1:8765/                 # HTML-дашборд
curl -s http://127.0.0.1:8765/v1/models

# Обновление списков моделей (cron 0 3 * * * на устройстве).
# ПЕРЕЗАПИСЫВАЕТ исходники providers/*.py регулярками — запускать осознанно.
cd consilium && python update_all.py

# Тесты парсера (обычные assert-функции, pytest не требуется; sys.path чинится внутри файла)
python agents/parser/tests/test_pipeline.py
pytest agents/parser/tests/test_pipeline.py::test_normalize   # один тест

# Прогон пайплайна очистки (Слой 4)
cd agents/parser
python pipeline_v55_final.py input_real.csv output_real.csv --db dedup_cache.db
python pipeline_v55_final.py input_real.csv --dry-run          # только метрики
# Побочные файлы пишутся в cwd: metrics.json, rejected.csv
```

На устройстве: `systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent`.

## Архитектура Consilium

### Путь запроса

`Telegram → Hermes Agent → POST /v1/chat/completions → фильтр system prompt → Task Router → цепочка fallback → call_provider → нормализация ответа → JSON или SSE`

Вся эта логика живёт **инлайном** в `chat_completions()` ([consilium/consilium_server.py:652](consilium/consilium_server.py:652)), а не в отдельных модулях. `router.py` содержит вынесенные `classify_task()` / `build_response()`, но **нигде не импортируется** — это мёртвый дубль.

### Контракт ответа (самое важное)

Hermes v0.19 отвергает ответ (`Provider failed after retries`), если формат не совпадает. Два инварианта, которые обязан сохранять любой код, трогающий формирование ответа:

1. `message.tool_calls` присутствует **всегда** — пустой список, если инструментов нет (`ensure_tool_calls_field`, а также явное присваивание в `chat_completions`).
2. `message.content` равен `null`, когда `tool_calls` непустой; `reasoning_content` сворачивается в `content` **только** при отсутствии `tool_calls` (`normalize_message_content`).

Отдельный механизм — `rescue_inline_tool_calls()`: многие бесплатные модели выдают вызовы инструментов текстом (`<function=name>{...}</function>`, Qwen-обёртки, `[TOOL_CALLS]`). Функция вытаскивает их в структурный формат, `strip_inline_tool_calls()` чистит остатки из текста. Работает и для non-stream, и для SSE (в стриме — добивочным финальным чанком).

### Провайдеры

Класс на файл в `consilium/providers/`, наследник `BaseProvider`. `enabled` вычисляется в `__init__` как `keyless or bool(keys)`; `PROVIDERS` — список словарей от `to_dict()`, отфильтрованный по `enabled`.

Добавить провайдера = новый файл + импорт и запись в `ALL_PROVIDERS` в [providers/\_\_init\_\_.py](consilium/providers/__init__.py).

Известные расхождения, о которых надо помнить:

- **`format` теряется.** `AIHordeProvider.format = "aihorde"`, `CloudflareProvider.format = "cloudflare"`, но `BaseProvider.to_dict()` жёстко пишет `'format': 'openai'`. Ветки `aihorde` / `huggingface` в сервере поэтому недостижимы; Cloudflare работает только потому, что проверяется по `provider["name"]`.
- **`get_headers()` не используется.** `call_provider()` собирает заголовки сам, так что переопределение в `OpenRouterProvider` (`HTTP-Referer`, `X-Title`) не применяется.
- **Два независимых пути загрузки ключей.** `BaseProvider.load_keys()` сам парсит `consilium/.env` (относительно файла) — от него зависит `enabled`. `consilium_server.load_keys()` читает `os.getenv` после `load_dotenv("/home/khadas/.hermes/skills/consilium/.env")` — от него зависит заголовок `Authorization`. Если ключ виден одному и не виден другому, провайдер окажется «включён», но пойдёт без авторизации.

### Плоские импорты

Модули внутри `consilium/` импортируют друг друга без пакета: `from rate_limiter import RateLimiter`, `from providers import PROVIDERS`, `dashboard.py` делает `from provider_stats import provider_stats`. Работает благодаря `sys.path.insert(0, dirname(__file__))` в начале сервера. Запуск из другого каталога или превращение в пакет всё сломает.

### Устойчивость: что реально включено

- `fallback_manager.build_chains()` строит цепочки `chat / code / search / analysis`, размечая модели по подстрокам в имени. Порядок задаётся хардкодом `PRIORITY` в [fallback_manager.py](consilium/fallback_manager.py) — он **не совпадает** с таблицей приоритетов в README. Вызывается внутри цикла по провайдерам в сервере, то есть многократно.
- `circuit_breaker` считает только сетевые исключения (ветка `except Exception`). HTTP 429/401/402/403 обрабатываются раньше и до счётчика не доходят.
- `rate_limiter` фактически **выключен**: сервер создаёт собственный `RateLimiter()`, но `is_available()` из горячего пути не вызывается — только `mark_429()` / `mark_402()` при ошибках. Метод возвращает кортеж `(bool, reason)`; единственный потребитель — `dashboard.py`.
- Реализованы, но **не подключены** к серверу: `health_checker.py`, `key_encryption.py`, `model_catalog.py`, `router.py`. README v7.1 описывает их как рабочие функции — README не является описанием runtime-поведения.

### Тайминги

Порядок обязан сохраняться: `PROVIDER_TIMEOUT` 20 с < `OVERALL_DEADLINE` 40 с < `request_timeout: 45` в `config.yaml`. `OVERALL_DEADLINE` объявлена, но нигде не проверяется.

### Состояние на диске

SQLite-файлы создаются рядом с модулями в `consilium/`: `usage.db`, `rate_limits.db`, `provider_stats.db`, `model_catalog.db`, плюс кэш `fallback_chain.json`. Все в `.gitignore` не перечислены явно — не коммитить.

### Версии

README говорит v7.1, докстринг `consilium_server.py` — v6.16, `FastAPI(version=...)` — «6.17». Единого источника версии нет.

## Агенты B2B-пайплайна

Цепочка: `product-analyst` (Слой 1) → `source-scout` (Слой 2) → `parsing-engineer` (Слой 3) → `parser` (Слой 4). `orchestrator` дирижирует, `optimizer` вызывается отдельно.

Каждый каталог агента — триада:

- `SOUL.md` — роль, короткий текст, подставляется как personality через `config.yaml → agent.personalities`
- `SKILL.md` — инструкции и накопленная база знаний (у `parser` 137 KB, у `parsing-engineer` 68 KB — читать выборочно, не целиком)
- `PROGRESS.md` — протокол возобновления: агент читает его первым, продолжает с блока `CURRENT`, обновляет перед выходом. Старая история вытеснена в `PROGRESS_archive.md`.

Это **не** Hermes Skills — оркестратор читает файлы через `read_file` и передаёт склейку в `delegate_task(goal=..., context=..., toolsets=["file","terminal"])`. Параметр `agent` в Hermes отсутствует, `/personality` для делегирования не используется.

Промпт оркестратора продублирован в `config.yaml → agent.system_prompt` **и** в `agents/orchestrator/SOUL.md` — правки нужны в обоих местах.

`agents/parser/references/*.md` — датированные инженерные заметки о прошлых инцидентах и найденных паттернах (регрессии стран, двойной подсчёт, cron, Serper). Заглядывать туда до правок пайплайна.

## Пайплайн очистки (Слой 4)

[agents/parser/pipeline_v55_final.py](agents/parser/pipeline_v55_final.py) — точка входа. Порядок в `PipelineV55.process()`: валидация email/телефона → whitelist известных брендов → `ExactDedup` (SQLite по email и по паре `phone|website`) → `FuzzyDedup` (блокировка по первым/последним буквам + `rapidfuzz`, с fallback на `difflib`) → скоринг.

Пороги: `< 25` — отброс, `>= 50` — принять, `25–49` — серая зона (принимается при `>= 30`).

**Скоринг продублирован.** `score_company()` внутри `pipeline_v55_final.py` и `score()` в [cleaner/scorer.py](agents/parser/cleaner/scorer.py) — это два разных набора ключевых слов, которые уже разошлись (в пайплайне есть `NON_FOOD_KEYWORDS` с `WHOLESALE_NONFOOD`, расширенные `GOOD_WORDS_*` и т. д.). Пайплайн использует свою копию, а **тесты проверяют модульную**. Любое изменение правил скоринга надо вносить в оба места либо сначала свести их в одно.

Нормализация названий (`cleaner/normalize.py`) тоже частично продублирована константами в пайплайне (`RE_LEGAL`, `COUNTRIES`).

## Соглашения и подводные камни

- Комментарии, докстринги и логи — по-русски, лог-сообщения с эмодзи-префиксами (`✅`, `🔴`, `⏱️`). Держаться того же стиля.
- Захардкоженные абсолютные пути `/home/khadas/...` в `consilium_server.py` (`load_dotenv`), `update_all.py` (`SERVER_DB`), `agents/*/SOUL.md` и `config.yaml`. На Windows они не резолвятся — при локальном запуске `.env` подхватится только через `BaseProvider`.
- `.env` в `.gitignore`; `.env.example`, на который ссылается README, в репозитории отсутствует.
- `update_all.py` правит исходники регулярками: `models = [...]` в `providers/*.py` и `TASK_MODEL_MAP` в `consilium_server.py` — последнего в текущем сервере уже нет, эта часть работает вхолостую.
- `.gitignore` целиком обёрнут в ``` ``` ``` — строки-ограждения трактуются как паттерны и ни с чем не совпадают, файл работает по случайности. При редактировании не задеть.
- `logs/` — это **не** рантайм-логи, а дампы исходников Hermes Agent (`hermes_code_*.py`, до 1.1 MB) и ответов Consilium, снятые для аудита. Справочный материал, только для чтения.
- `AUDIT_REPORT.md` и `prompt.txt` — артефакты внешнего аудита от 21.07.2026. Отчёт описывает исправления как применённые; сверяться с кодом, а не верить на слово.

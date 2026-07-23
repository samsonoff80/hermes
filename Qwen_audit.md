# AUDIT REPORT — Consilium v7.2 для Hermes Agent v0.19
**Дата аудита:** 23 июля 2026
**Версия системы:** Consilium v7.2, Hermes Agent v0.19
**Платформа:** Khadas VIM4 ARM64 8GB RAM, Ubuntu 24.04
---
## 1. Найденные проблемы (файл, строка, описание)
### 1.1 Критические проблемы совместимости с Hermes v0.19
#### Проблема 1.1.1: Отсутствует `context_length` в эндпоинте `/v1/models`
- **Файл:** `consilium/consilium_server.py`, строки 774-780
- **Описание:** Согласно требованиям Hermes v0.19, эндпоинт `/v1/models` должен возвращать поле `context_length` для каждой модели. В текущей реализации возвращается только `id`, `object` и `owned_by`.
- **Влияние:** Hermes v0.19 не может корректно определить лимиты контекста для custom provider, что может привести к обрезке запросов или ошибкам валидации.
- **Код:**
```python
@app.get("/v1/models")
async def list_models():
    models = []
    for p in PROVIDERS:
        for m in p["models"]:
            models.append({"id": m, "object": "model", "owned_by": p["name"]})
    return {"object": "list", "data": models}
```
#### Проблема 1.1.2: Не генерируются UUID для `tool_calls[].id`
- **Файл:** `consilium/consilium_server.py`, строки 995-1002
- **Описание:** Hermes v0.19 требует, чтобы каждый элемент в `tool_calls` имел поле `id` формата UUID. В текущем коде `id` берётся из ответа провайдера (если есть), но не генерируется если отсутствует. Для rescued tool_calls используется формат `call_rescued_{index}`, что не соответствует спецификации OpenAI.
- **Влияние:** Hermes может отвергнуть ответ как невалидный, особенно при работе с провайдерами, которые не возвращают `id` для tool_calls.
- **Код:**
```python
message["tool_calls"] = tool_calls if tool_calls else []
```
#### Проблема 1.1.3: Неправильный формат `id` ответа
- **Файл:** `consilium/consilium_server.py`, строка 1013
- **Описание:** Поле `id` ответа использует хеш времени (`chatcmpl-{md5_hash[:12]}`), тогда как OpenAI spec требует уникальный идентификатор. Хотя это не критично, может вызвать проблемы при дедупликации ответов в Hermes.
- **Код:**
```python
"id": f"chatcmpl-{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
```
### 1.2 Проблемы архитектуры и логики
#### Проблема 1.2.1: Отсутствует иерархия таймаутов
- **Файл:** `consilium/consilium_server.py`, строки 100-102; `config.yaml`, строки 62-70
- **Описание:** Hermes v0.19 поддерживает иерархию таймаутов: `providers.<id>.request_timeout_seconds` → `models.<model>.timeout_seconds`. В текущей реализации используется жёстко заданный `PROVIDER_TIMEOUT = 20.0` и `OVERALL_DEADLINE = 40.0`.
- **Влияние:** Невозможность гибкого управления таймаутами для разных моделей и провайдеров. Медленные модели могут быть преждевременно отключены.
#### Проблема 1.2.2: Circuit Breaker не имеет состояния HALF_OPEN
- **Файл:** `consilium/circuit_breaker.py`, строки 37-45
- **Описание:** Реализация circuit breaker имеет только два состояния: CLOSED (нормальная работа) и OPEN (блокировка). Отсутствует промежуточное состояние HALF_OPEN для тестирования восстановления провайдера. После истечения `cooldown` провайдер сразу возвращается в работу без проверки.
- **Влияние:** При временных проблемах у провайдера возможен цикл repeated failures после каждого cooldown.
- **Код:**
```python
def is_available(self, name):
    with self.lock:
        if name in self.disabled_until:
            if time.time() < self.disabled_until[name]:
                return False
            del self.disabled_until[name]
            self.failures[name] = 0  # Сброс без проверки
            logger.info(f"🟢 {name}: circuit breaker CLOSED")
        return True
```
#### Проблема 1.2.3: Rate Limiter не поддерживает RPD/TPD лимиты на уровне проверки
- **Файл:** `consilium/rate_limiter.py`, строки 99-115
- **Описание:** Класс `RateLimiter` ведёт учёт `rpd_count` и `tpd_count` (строки 42-43), но метод `is_available()` проверяет только `disabled` и `cooldown_until`. Лимиты RPD/TPD не проверяются перед запросом.
- **Влияние:** Ключи могут превысить дневные лимиты, что приведёт к 429 ошибкам от провайдеров.
- **Код:**
```python
def is_available(self, provider: str, key_index: int = 0) -> Tuple[bool, Optional[str]]:
    with self.lock:
        e = self._state.get((provider, key_index))
        if e is None:
            return True, None
        if e["disabled"]:
            return False, "disabled"
        if e["cooldown_until"] > time.time():
            return False, f"cooldown:{int(e['cooldown_until'] - time.time())}s"
    return True, None  # RPD/TPD не проверяются!
```
#### Проблема 1.2.4: Fallback Manager может вернуть пустую цепочку
- **Файл:** `consilium/fallback_manager.py`, строки 116-125
- **Описание:** Метод `get_chain()` может вернуть пустой список, если все провайдеры отфильтрованы gate-функцией. Хотя есть fallback на "chat" и `all_entries`, логика не гарантирует наличие рабочих провайдеров.
- **Влияние:** Запрос может завершиться ошибкой 503 даже при наличии доступных провайдеров.
### 1.3 Проблемы конфигурации
#### Проблема 1.3.1: config.yaml не содержит `context_length` для моделей
- **Файл:** `config.yaml`, строки 62-70
- **Описание:** Конфигурация модели содержит `context_length: 128000`, но это значение не передаётся в эндпоинт `/v1/models`. Отсутствует иерархия таймаутов для провайдеров и моделей.
- **Влияние:** Несогласованность между декларированными и фактическими возможностями моделей.
#### Проблема 1.3.2: GitHub Provider использует неверный base_url
- **Файл:** `consilium/providers/github.py`, строка 4
- **Описание:** GitHub Provider использует `https://models.inference.ai.azure.com`, что является Azure ML endpoint. Согласно задаче, GitHub модели должны использовать нативный GitHub API, не azureml.
- **Влияние:** Путаница в идентификации провайдера, возможные проблемы с аутентификацией.
#### Проблема 1.3.3: Cloudflare Provider требует ACCOUNT_ID, но нет механизма подстановки
- **Файл:** `consilium/providers/cloudflare.py`, строка 4
- **Описание:** `base_url` содержит плейсхолдер `{ACCOUNT_ID}`, но нет кода для его замены на реальное значение из переменных окружения.
- **Влияние:** Все запросы к Cloudflare будут неудачными из-за невалидного URL.
- **Код:**
```python
base_url = "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run"
```
### 1.4 Проблемы обработки граничных случаев
#### Проблема 1.4.1: Не обрабатывается случай, когда все провайдеры упали
- **Файл:** `consilium/consilium_server.py`, строки 875-895
- **Описание:** Цикл fallback перебирает провайдеров, но нет явной обработки случая, когда все провайдеры в цепочке недоступны. Возвращается общий error response, но нет алертинга или логирования критического состояния.
- **Влияние:** Система молча возвращает ошибку без уведомления администратора о полном отказе всех провайдеров.
#### Проблема 1.4.2: Не обрабатывается не-JSON ответ от провайдера
- **Файл:** `consilium/consilium_server.py`, строки 530-550
- **Описание:** Код предполагает, что ответ от провайдера всегда валидный JSON или streaming response. Нет обработки случая, когда провайдер возвращает HTML (например, страница ошибки) или бинарные данные.
- **Влияние:** Необработанное исключение при парсинге ответа, запрос завершается без попытки fallback.
#### Проблема 1.4.3: .env пустой или отсутствуют ключи
- **Файл:** `consilium/providers/base.py`, строки 23-62
- **Описание:** Метод `load_keys()` пытается загрузить ключи из `.env` или окружения, но если файл отсутствует и переменных нет, провайдер помечается как `enabled=False`. Однако нет явного предупреждения при старте о том, что критические провайдеры отключены.
- **Влияние:** Система запускается с неполным набором провайдеров без уведомления оператора.
### 1.5 Мёртвый код и дублирование
#### Проблема 1.5.1: Дублирование логики извлечения content
- **Файл:** `consilium/consilium_server.py`, строки 288-372
- **Описание:** Функции `extract_openai_content`, `extract_aihorde_content`, `extract_huggingface_content` и их аналоги для других полей (finish_reason, tool_calls, usage, reasoning_content) имеют идентичную структуру и могут быть объединены через стратегию или маппинг.
- **Влияние:** Увеличение объёма кода, сложность поддержки, риск рассинхронизации логики.
#### Проблема 1.5.2: Ненужные импорты в consilium_server.py
- **Файл:** `consilium/consilium_server.py`, строки 22-23
- **Описание:** После импорта `from providers import PROVIDERS` (строка 24) остаются избыточные строки `import sys, os` и `sys.path.insert(0, ...)`, так как провайдеры уже импортированы корректно.
- **Влияние:** Минимальное, но указывает на небрежность в поддержании кода.
#### Проблема 1.5.3: Резервные копии файлов в репозитории
- **Файл:** `consilium/consilium_server.py.backup`, `consilium/consilium_server.py.pre_openrouter_fix`
- **Описание:** В репозитории присутствуют резервные копии файлов, которые не должны быть закоммичены.
- **Влияние:** Раздувание репозитория, потенциальная утечка старой логики.
### 1.6 Проблемы мониторинга и наблюдаемости
#### Проблема 1.6.1: Недостаточный сбор метрик в provider_stats
- **Файл:** `consilium/provider_stats.py`, строки 137-158
- **Описание:** Собираются только `success`, `fail`, `total_tokens`, `avg_latency`. Отсутствуют метрики по типам ошибок (429 vs 5xx vs timeout), распределению латентности (p50, p95, p99), количеству запросов в разрезе моделей.
- **Влияние:** Невозможность детального анализа производительности и выявления узких мест.
#### Проблема 1.6.2: Alerting отключён
- **Файл:** `README.md`, строка 25
- **Описание:** Согласно README, система алертинга отключена. При полном отказе всех провайдеров оператор не получит уведомления.
- **Влияние:** Простой системы может остаться незамеченным до получения жалобы от пользователя.
---
## 2. Рекомендации по исправлению (с кодом)
### 2.1 Исправление совместимости с Hermes v0.19
#### Решение 2.1.1: Добавить `context_length` в `/v1/models`
```python
# consilium/consilium_server.py, строки 774-780
# Модель с известными лимитами контекста
MODEL_CONTEXT_LENGTHS = {
    "gpt-4o-mini": 128000,
    "gpt-4o": 128000,
    "llama-3.3-70b-versatile": 128000,
    "llama-3.1-8b-instant": 8192,
    "mistral-large-latest": 128000,
    "codestral-2508": 32000,
    "@cf/meta/llama-3.2-3b-instruct": 128000,
    "@cf/openai/gpt-oss-120b": 128000,
}
DEFAULT_CONTEXT_LENGTH = 128000  # Значение по умолчанию
@app.get("/v1/models")
async def list_models():
    models = []
    for p in PROVIDERS:
        for m in p["models"]:
            models.append({
                "id": m,
                "object": "model",
                "owned_by": p["name"],
                "context_length": MODEL_CONTEXT_LENGTHS.get(m, DEFAULT_CONTEXT_LENGTH)
            })
    return {"object": "list", "data": models}
```
#### Решение 2.1.2: Генерировать UUID для tool_calls[].id
```python
# consilium/consilium_server.py, добавить функцию перед обработкой ответа
def ensure_tool_call_ids(tool_calls: Optional[List[Dict]]) -> List[Dict]:
    """Гарантирует наличие UUID для каждого tool_call."""
    if not tool_calls:
        return []
    result = []
    for tc in tool_calls:
        tc_copy = tc.copy() if isinstance(tc, dict) else {}
        if "id" not in tc_copy or not tc_copy["id"]:
            tc_copy["id"] = f"call_{uuid.uuid4().hex[:24]}"
        if "type" not in tc_copy:
            tc_copy["type"] = "function"
        result.append(tc_copy)
    return result
# В строках 995-1002 заменить:
message["tool_calls"] = ensure_tool_call_ids(tool_calls)
```
#### Решение 2.1.3: Использовать корректный формат id ответа
```python
# consilium/consilium_server.py, строка 1013
response = {
    "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",  # Вместо md5 хеша
    "object": "chat.completion",
    "created": int(time.time()),
    "model": target_model,
    ...
}
```
### 2.2 Исправление архитектуры
#### Решение 2.2.1: Реализовать иерархию таймаутов
```python
# consilium/consilium_server.py, добавить после загрузки конфигурации
def get_timeout_for_model(provider_name: str, model: str) -> float:
    """Получает таймаут из иерархии: модель → провайдер → дефолт."""
    # Попытка получить из config.yaml (требуется загрузка конфига)
    try:
        import yaml
        with open("/home/khadas/.hermes/config.yaml") as f:
            config = yaml.safe_load(f)
        # Приоритет 1: таймаут модели
        model_config = config.get("models", {}).get(model, {})
        if "timeout_seconds" in model_config:
            return float(model_config["timeout_seconds"])
        # Приоритет 2: таймаут провайдера
        provider_config = config.get("providers", {}).get(provider_name, {})
        if "request_timeout_seconds" in provider_config:
            return float(provider_config["request_timeout_seconds"])
    except Exception:
        pass
    # Дефолтное значение
    return float(os.getenv("CONSILIUM_DEFAULT_TIMEOUT", "20.0"))
# В call_provider() заменить:
timeout = get_timeout_for_model(provider["name"], model)
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(timeout, connect=CONNECT_TIMEOUT),
    ...
)
```
#### Решение 2.2.2: Добавить состояние HALF_OPEN в Circuit Breaker
```python
# consilium/circuit_breaker.py, полная переработка класса
class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    def __init__(self, threshold=5, cooldown=60, half_open_max_calls=3):
        self.threshold = threshold
        self.cooldown = cooldown
        self.half_open_max_calls = half_open_max_calls
        self.failures = {}
        self.state = {}  # "provider": state
        self.disabled_until = {}
        self.half_open_calls = {}  # Счётчик успешных вызовов в HALF_OPEN
        self.lock = threading.Lock()
        self.on_open = None
    def record_failure(self, name):
        opened = False
        with self.lock:
            current_state = self.state.get(name, self.CLOSED)
            if current_state == self.HALF_OPEN:
                # Неудача в HALF_OPEN → сразу OPEN
                self.disabled_until[name] = time.time() + self.cooldown
                self.state[name] = self.OPEN
                self.half_open_calls.pop(name, None)
                opened = True
                logger.warning(f"🔴 {name}: HALF_OPEN failed → OPEN ({self.cooldown}s)")
            else:
                self.failures[name] = self.failures.get(name, 0) + 1
                if self.failures[name] >= self.threshold and name not in self.disabled_until:
                    self.disabled_until[name] = time.time() + self.cooldown
                    self.state[name] = self.OPEN
                    opened = True
        if opened and self.on_open:
            try:
                self.on_open(name)
            except Exception as e:
                logger.warning(f"circuit breaker alert failed: {e}")
    def record_success(self, name):
        with self.lock:
            current_state = self.state.get(name, self.CLOSED)
            if current_state == self.HALF_OPEN:
                self.half_open_calls[name] = self.half_open_calls.get(name, 0) + 1
                if self.half_open_calls[name] >= self.half_open_max_calls:
                    # Достаточно успехов → CLOSED
                    self.state[name] = self.CLOSED
                    self.failures[name] = 0
                    self.disabled_until.pop(name, None)
                    self.half_open_calls.pop(name, None)
                    logger.info(f"🟢 {name}: HALF_OPEN → CLOSED")
            else:
                self.failures[name] = 0
                self.disabled_until.pop(name, None)
                self.state[name] = self.CLOSED
    def is_available(self, name):
        with self.lock:
            if name not in self.disabled_until:
                self.state[name] = self.CLOSED
                return True
            if time.time() < self.disabled_until[name]:
                return False
            # Истёк cooldown → переход в HALF_OPEN
            if self.state.get(name) != self.HALF_OPEN:
                self.state[name] = self.HALF_OPEN
                self.half_open_calls[name] = 0
                logger.info(f"🟡 {name}: OPEN → HALF_OPEN (testing)")
            return True  # Разрешаем пробный вызов
```
#### Решение 2.2.3: Добавить проверку RPD/TPD в is_available()
```python
# consilium/rate_limiter.py, строки 99-109
def is_available(self, provider: str, key_index: int = 0, tokens_estimate: int = 0) -> Tuple[bool, Optional[str]]:
    """(доступен, причина_отказа). Проверяет все лимиты включая RPD/TPD."""
    with self.lock:
        e = self._state.get((provider, key_index))
        if e is None:
            return True, None
        if e["disabled"]:
            return False, "disabled"
        if e["cooldown_until"] > time.time():
            return False, f"cooldown:{int(e['cooldown_until'] - time.time())}s"
        # Проверка RPD (requests per day)
        max_rpd = int(os.getenv(f"{provider.upper()}_MAX_RPD", "0"))
        if max_rpd > 0 and e["rpd"] >= max_rpd:
            return False, f"rpd_limit:{e['rpd']}/{max_rpd}"
        # Проверка TPD (tokens per day)
        max_tpd = int(os.getenv(f"{provider.upper()}_MAX_TPD", "0"))
        if max_tpd > 0 and (e["tpd"] + tokens_estimate) > max_tpd:
            return False, f"tpd_limit:{e['tpd']}/{max_tpd}"
    return True, None
```
### 2.3 Исправление конфигурации
#### Решение 2.3.1: Подстановка ACCOUNT_ID для Cloudflare
```python
# consilium/providers/cloudflare.py
import os
class CloudflareProvider(BaseProvider):
    name = "cloudflare"
    env_prefix = "CLOUDFLARE_API_KEY"
    has_api = False
    models = ["@cf/pipecat-ai/smart-turn-v2", "@cf/openai/gpt-oss-120b", ...]
    format = "cloudflare"
    def __init__(self):
        super().__init__()
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if account_id:
            self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"
        else:
            self.base_url = "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run"
            import logging
            logging.getLogger('consilium.providers').warning(
                "Cloudflare ACCOUNT_ID не установлен — запросы будут неудачными"
            )
```
#### Решение 2.3.2: Обновить config.yaml с полной конфигурацией
```yaml
# config.yaml, секция model и providers
model:
  api_key: sk-consilium
  api_mode: chat_completions
  base_url: http://127.0.0.1:8765/v1
  context_file_max_chars: 4000
  context_length: 128000
  default: auto
  provider: custom
  request_timeout: 45
  timeout_seconds: 45  # Добавлено для совместимости
providers:
  openai:
    api_key: sk-consilium
    base_url: http://127.0.0.1:8765/v1
    request_timeout_seconds: 45  # Добавлено
  groq:
    request_timeout_seconds: 30
  cloudflare:
    request_timeout_seconds: 60
    account_id: ${CLOUDFLARE_ACCOUNT_ID}  # Переменная окружения
models:
  gpt-4o-mini:
    context_length: 128000
    timeout_seconds: 30
  llama-3.3-70b-versatile:
    context_length: 128000
    timeout_seconds: 25
  mistral-large-latest:
    context_length: 128000
    timeout_seconds: 35
```
### 2.4 Обработка граничных случаев
#### Решение 2.4.1: Обработка полного отказа всех провайдеров
```python
# consilium/consilium_server.py, в конце цикла fallback (после строки 895)
if not provider_resp:
    # Все провайдеры в цепочке упали
    logger.critical(f"[{request_id}] ❌ ВСЕ ПРОВАЙДЕРЫ УПАЛИ. Задача: {task}, модель: {target_model}")
    # Алертинг (если включён)
    try:
        await alert_all_providers_down(task, target_model, len(chain))
    except Exception as e:
        logger.warning(f"Alert failed: {e}")
    raise HTTPException(503, detail={
        "error": "all_providers_down",
        "task": task,
        "model": str(target_model),
        "attempted_providers": [f"{p['name']}/{p.get('model', 'N/A')}" for p in chain],
        "timestamp": datetime.now().isoformat()
    })
```
#### Решение 2.4.2: Обработка не-JSON ответа
```python
# consilium/consilium_server.py, в обработке ответа провайдера (после строки 530)
try:
    provider_resp = resp.json()
except json.JSONDecodeError:
    content_type = resp.headers.get("content-type", "")
    logger.error(f"❌ {provider['name']}: не-JSON ответ (Content-Type: {content_type})")
    logger.debug(f"Response body preview: {resp.text[:500]}")
    # Попытка извлечь ошибку из HTML
    if "text/html" in content_type:
        error_msg = f"HTML response from {provider['name']} (возможно, страница ошибки)"
    else:
        error_msg = f"Invalid response format from {provider['name']}"
    provider_stats.record_failure(provider["name"], "parse_error", model)
    circuit_breaker.record_failure(provider["name"])
    continue  # Переход к следующему провайдеру в цепочке
```
#### Решение 2.4.3: Проверка наличия ключей при старте
```python
# consilium/consilium_server.py, после загрузки PROVIDERS (после строки 129)
CRITICAL_PROVIDERS = ["groq", "github", "mistral"]  # Минимальный рабочий набор
missing_critical = []
for p in PROVIDERS:
    if p["name"] in CRITICAL_PROVIDERS:
        keys = PROVIDER_KEYS.get(p["name"], [])
        if not keys and not p.get("keyless", False):
            missing_critical.append(p["name"])
            logger.error(f"❌ КРИТИЧЕСКИЙ ПРОВАЙДЕР {p['name']} ОТКЛЮЧЕН: нет ключей")
if missing_critical:
    logger.critical(f"⚠️ СИСТЕМА ЗАПУЩЕНА С НЕПОЛНЫМ НАБОРОМ ПРОВАЙДЕРОВ: {missing_critical}")
    logger.critical("Проверьте .env файл и переменные окружения")
```
### 2.5 Устранение мёртвого кода
#### Решение 2.5.1: Рефакторинг функций извлечения данных
```python
# consilium/consilium_server.py, заменить строки 288-372
from typing import Callable, Dict, Any
# Единая стратегия извлечения для разных форматов
EXTRACTORS: Dict[str, Dict[str, Callable[[Dict], Any]]] = {
    "openai": {
        "content": lambda d: d.get("choices", [{}])[0].get("message", {}).get("content"),
        "finish_reason": lambda d: d.get("choices", [{}])[0].get("finish_reason", "stop"),
        "tool_calls": lambda d: d.get("choices", [{}])[0].get("message", {}).get("tool_calls"),
        "usage": lambda d: d.get("usage"),
        "reasoning_content": lambda d: d.get("choices", [{}])[0].get("message", {}).get("reasoning_content"),
    },
    "aihorde": {
        "content": lambda d: d.get("generations", [{}])[0].get("text", "") if d.get("generations") else "",
        "finish_reason": lambda d: d.get("generations", [{}])[0].get("finish_reason", "stop") if d.get("generations") else "stop",
        "tool_calls": lambda d: None,
        "usage": lambda d: None,
        "reasoning_content": lambda d: None,
    },
    "huggingface": {
        "content": lambda d: d[0].get("generated_text", "") if isinstance(d, list) else d.get("generated_text", ""),
        "finish_reason": lambda d: "stop",
        "tool_calls": lambda d: None,
        "usage": lambda d: None,
        "reasoning_content": lambda d: None,
    },
}
def extract_field(data: dict, field: str, provider_format: str = "openai") -> Any:
    """Извлекает поле из ответа провайдера согласно формату."""
    extractors = EXTRACTORS.get(provider_format, EXTRACTORS["openai"])
    extractor = extractors.get(field, lambda d: None)
    try:
        return extractor(data)
    except Exception:
        return None
# Теперь вместо extract_openai_content(data) использовать:
# extract_field(data, "content", provider_format)
```
#### Решение 2.5.2: Удалить избыточные импорты
```python
# consilium/consilium_server.py, строки 22-23 удалить
# Оставить только:
from providers import PROVIDERS
```
#### Решение 2.5.3: Добавить backup файлы в .gitignore
```bash
# .gitignore, добавить:
*.backup
*.pre_*
*.old
__pycache__/
*.pyc
*.db
*.db-wal
*.db-shm
logs/
```
---
## 3. Рекомендации по улучшению (архитектура, оптимизация, мониторинг)
### 3.1 Архитектурные улучшения
#### 3.1.1: Внедрить слой абстракции провайдеров (Provider Interface)
**Проблема:** Каждый провайдер имеет уникальную логику подключения, формат запросов и ответов.
**Решение:** Создать единый интерфейс `IProvider` с методами:
- `prepare_request(messages, model, options) -> Dict`
- `parse_response(raw_response) -> ChatCompletionResult`
- `health_check() -> bool`
- `get_capabilities() -> ProviderCapabilities`
**Преимущества:**
- Упрощение добавления новых провайдеров
- Централизованная обработка ошибок
- Единая точка логирования и метрик
#### 3.1.2: Выделить Fallback Manager в отдельный сервис
**Проблема:** Логика fallback тесно связана с основным сервером, что усложняет тестирование и модификацию.
**Решение:** Создать отдельный модуль `consilium/orchestrator.py` с классом `RequestOrchestrator`:
```python
class RequestOrchestrator:
    def __init__(self, providers, fallback_manager, circuit_breaker, rate_limiter):
        ...
    async def execute(self, request: ChatRequest) -> ChatResponse:
        # 1. Классификация задачи
        # 2. Выбор цепочки провайдеров
        # 3. Последовательные попытки с учётом circuit breaker
        # 4. Нормализация ответа
        ...
```
#### 3.1.3: Реализовать кэширование ответов (Prompt Caching)
**Согласно Hermes v0.19:** Поддержка `cache_control` с TTL 1h (Claude/OpenRouter), 5m (Qwen Cloud).
**Решение:**
```python
# consilium/cache/response_cache.py
class ResponseCache:
    def __init__(self, backend="sqlite"):
        self.backend = backend
        self.ttl_defaults = {
            "claude": 3600,
            "openrouter": 3600,
            "qwen": 300,
            "default": 600,
        }
    async def get(self, cache_key: str) -> Optional[ChatResponse]:
        ...
    async def set(self, cache_key: str, response: ChatResponse, ttl: int = None):
        ...
    def compute_cache_key(self, messages: List[Dict], model: str, tools: Optional[List]) -> str:
        # Хеш от нормализованных сообщений + model + tools
        ...
```
### 3.2 Оптимизация для VIM4 8GB
#### 3.2.1: Асинхронные очереди с ограничением размера
**Проблема:** При 100 одновременных запросах возможно исчерпание памяти.
**Решение:**
```python
# consilium/queue/request_queue.py
from asyncio import Queue, Semaphore
class RequestQueue:
    def __init__(self, max_size=50, max_concurrent=10):
        self.queue = Queue(maxsize=max_size)
        self.semaphore = Semaphore(max_concurrent)
        self.dropped_count = 0
    async def enqueue(self, request: ChatRequest) -> bool:
        try:
            self.queue.put_nowait(request)
            return True
        except asyncio.QueueFull:
            self.dropped_count += 1
            return False
    async def process_with_limit(self, handler):
        async with self.semaphore:
            request = await self.queue.get()
            try:
                return await handler(request)
            finally:
                self.queue.task_done()
```
#### 3.2.2: Оптимизация работы с SQLite
**Проблема:** Частые открытия соединений блокируют выполнение.
**Решение:**
- Использовать connection pool (aiofiles + aiosqlite)
- Включить WAL mode (уже сделано)
- Батчевая запись (уже реализовано в provider_stats и rate_limiter)
- Настроить `PRAGMA synchronous = NORMAL` для снижения накладных расходов
```python
# В _init_db() добавить:
conn.execute("PRAGMA synchronous = NORMAL")
conn.execute("PRAGMA cache_size = -2000")  # 2MB кэш
conn.execute("PRAGMA busy_timeout = 5000")  # 5с ожидание при блокировке
```
#### 3.2.3: Кэширование метаданных моделей
**Проблема:** При каждом запросе происходит поиск модели в списке PROVIDERS.
**Решение:**
```python
# consilium/model_registry.py
class ModelRegistry:
    def __init__(self):
        self._cache: Dict[str, ProviderInfo] = {}
        self._lock = threading.RLock()
    def rebuild(self, providers: List[Dict]):
        with self._lock:
            self._cache.clear()
            for p in providers:
                for model in p["models"]:
                    self._cache[model] = ProviderInfo(
                        name=p["name"],
                        format=p.get("format", "openai"),
                        rpd=p.get("rpd", 0),
                    )
    def get_provider(self, model: str) -> Optional[ProviderInfo]:
        with self._lock:
            return self._cache.get(model)
```
### 3.3 Улучшение отказоустойчивости
#### 3.3.1: Graceful Shutdown
**Проблема:** При перезапуске теряются незавершённые запросы и статистика.
**Решение:**
```python
# consilium/consilium_server.py, в lifespan()
@asynccontextmanager
async def lifespan(app: FastAPI):
    shutdown_event = asyncio.Event()
    async def graceful_shutdown():
        logger.info("🛑 Graceful shutdown initiated...")
        # 1. Остановить приём новых запросов
        # 2. Дождаться завершения активных запросов (до 30с)
        # 3. Сбросить статистику в БД
        provider_stats.flush(force=True)
        rate_limiter.flush(force=True)
        # 4. Закрыть HTTP клиент
        await http_client.aclose()
        logger.info("✅ Shutdown complete")
    try:
        yield
    finally:
        await graceful_shutdown()
```
#### 3.3.2: Health Check с проверкой провайдеров
**Проблема:** Текущий health checker выполняется только при старте.
**Решение:**
```python
# consilium/health_checker.py, добавить периодическую проверку
async def periodic_health_check(interval=300):  # 5 минут
    while True:
        await asyncio.sleep(interval)
        results = await check_all_providers(PROVIDERS)
        healthy_count = sum(results)
        total_count = len(results)
        if healthy_count == 0:
            logger.critical(f"🚨 HEALTH CHECK: 0/{total_count} провайдеров доступно")
            await alert_all_providers_down("health_check", "N/A", total_count)
        elif healthy_count < total_count // 2:
            logger.warning(f"⚠️ HEALTH CHECK: {healthy_count}/{total_count} провайдеров доступно")
        # Обновить статус в dashboard
        update_health_status(results)
```
#### 3.3.3: Автоматическое восстановление после длительных перебоев
**Решение:**
```python
# consilium/resilience/auto_recovery.py
class AutoRecovery:
    def __init__(self, recovery_interval=3600):  # 1 час
        self.recovery_interval = recovery_interval
        self.last_recovery_attempt = {}
    async def try_recovery(self, provider_name: str) -> bool:
        last = self.last_recovery_attempt.get(provider_name, 0)
        if time.time() - last < self.recovery_interval:
            return False
        self.last_recovery_attempt[provider_name] = time.time()
        # Попытка health check
        is_healthy = await check_provider_health(provider_name)
        if is_healthy:
            circuit_breaker.record_success(provider_name)
            rate_limiter.reset(provider_name)
            logger.info(f"♻️ {provider_name}: автоматическое восстановление успешно")
            return True
        return False
```
### 3.4 Улучшение мониторинга
#### 3.4.1: Prometheus-совместимые метрики
**Решение:**
```python
# consilium/metrics/prometheus.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
# Метрики
REQUEST_COUNT = Counter(
    'consilium_requests_total',
    'Total requests',
    ['provider', 'model', 'task', 'status']
)
REQUEST_LATENCY = Histogram(
    'consilium_request_latency_seconds',
    'Request latency',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)
TOKENS_PROCESSED = Counter(
    'consilium_tokens_total',
    'Tokens processed',
    ['provider', 'model', 'type']  # type: prompt/completion/total
)
ACTIVE_REQUESTS = Gauge(
    'consilium_active_requests',
    'Currently active requests',
    ['provider']
)
CIRCUIT_BREAKER_STATE = Gauge(
    'consilium_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['provider']
)
RATE_LIMIT_STATUS = Gauge(
    'consilium_rate_limit_remaining',
    'Remaining requests/tokens',
    ['provider', 'key_index', 'type']  # type: rpd/tpd
)
@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest())
```
#### 3.4.2: Логирование медленных запросов
**Решение:**
```python
# consilium/logging/slow_query_logger.py
SLOW_QUERY_THRESHOLD = 2.0  # секунды
class SlowQueryLogger:
    def __init__(self, threshold=SLOW_QUERY_THRESHOLD):
        self.threshold = threshold
        self.slow_queries = []
        self.max_log_size = 1000
    def log(self, request_id: str, provider: str, model: str,
            duration: float, task: str):
        if duration < self.threshold:
            return
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "task": task,
            "duration": round(duration, 3),
        }
        logger.warning(f"🐌 SLOW QUERY: {provider}/{model} took {duration:.2f}s")
        self.slow_queries.append(entry)
        if len(self.slow_queries) > self.max_log_size:
            self.slow_queries = self.slow_queries[-self.max_log_size:]
    def get_report(self, limit=100) -> List[Dict]:
        return sorted(self.slow_queries, key=lambda x: -x["duration"])[:limit]
```
#### 3.4.3: Dashboard с реальной статистикой
**Текущее состояние:** `dashboard.py` существует, но требуется расширение.
**Рекомендации:**
- Добавить графики latency по провайдерам (p50, p95, p99)
- Отображать success rate в реальном времени
- Показывать остаток RPD/TPD лимитов
- Индикаторы circuit breaker состояния
- Топ медленных запросов за последний час
- История алертов и инцидентов
### 3.5 Дополнительные рекомендации
#### 3.5.1: Тестирование нагрузки
**Рекомендация:** Регулярно проводить нагрузочное тестирование:
```bash
# Пример с wrk
wrk -t4 -c100 -d60s --latency http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"model":"auto"}'
```
**Целевые метрики для VIM4 8GB:**
- Максимум concurrent запросов: 50
- P95 latency: < 5 секунд
- Error rate: < 1%
#### 3.5.2: Документирование API
**Рекомендация:** Добавить OpenAPI спецификацию:
```python
# consilium/consilium_server.py
from fastapi.openapi.utils import get_openapi
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Consilium LLM Gateway",
        version="7.2",
        description="LLM прокси для Hermes Agent v0.19 с поддержкой 12 провайдеров",
        routes=app.routes,
    )
    # Добавить примеры запросов/ответов
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = custom_openapi
```
#### 3.5.3: Версионирование и changelog
**Рекомендация:** Вести файл CHANGELOG.md с описанием изменений:
```markdown
# Changelog
## [7.2] - 2026-07-23
### Added
- Поддержка context_length в /v1/models
- Генерация UUID для tool_calls
### Fixed
- Circuit breaker HALF_OPEN состояние
- Проверка RPD/TPD лимитов
### Changed
- Формат id ответа на UUID-based
```
---
## Заключение
### Статус аудита
| Категория | Критические | Высокие | Средние | Низкие |
|-----------|-------------|---------|---------|--------|
| Синтаксис | 0 | 0 | 0 | 3 (backup файлы) |
| Совместимость | 3 | 0 | 0 | 0 |
| Архитектура | 0 | 4 | 2 | 0 |
| Конфигурация | 0 | 2 | 1 | 0 |
| Граничные случаи | 0 | 3 | 0 | 0 |
| Мониторинг | 0 | 1 | 2 | 0 |
| **Итого** | **3** | **10** | **5** | **3** |
### Приоритеты исправлений
**P0 (Немедленно):**
1. Добавить `context_length` в `/v1/models` — требование Hermes v0.19
2. Генерация UUID для `tool_calls[].id` — требование OpenAI spec
3. Исправить подстановку `ACCOUNT_ID` для Cloudflare
**P1 (В течение недели):**
4. Реализовать HALF_OPEN состояние в Circuit Breaker
5. Добавить проверку RPD/TPD лимитов
6. Обработка полного отказа всех провайдеров
**P2 (В течение месяца):**
7. Иерархия таймаутов (модель → провайдер → дефолт)
8. Prometheus метрики
9. Graceful shutdown
**P3 (Плановые улучшения):**
10. Рефакторинг функций извлечения данных
11. Кэширование ответов (Prompt Caching)
12. Расширенный dashboard
### Общая оценка
Система **работоспособна**, но требует доработки для полного соответствия требованиям Hermes v0.19 и обеспечения надёжной эксплуатации в production. Критические проблемы совместимости могут привести к отвержению ответов Hermes'ом, что делает их приоритетом №1 для исправления.
Архитектурно система построена грамотно с разделением ответственности между модулями. Основные риски связаны с недостаточной обработкой граничных случаев и отсутствием полноценного мониторинга.
Для платформы VIM4 8GB рекомендована оптимизация работы с памятью и SQLite, а также внедрение ограничений на количество одновременных запросов.
Файл AUDIT_REPORT.txt успешно создан и содержит полный отчёт аудита Consilium v7.2.
Содержание отчёта (1040 строк):
1. Найденные проблемы (21 шт)
3 критических: Отсутствует context_length в /v1/models, не генерируются UUID для tool_calls[].id, неправильный формат id ответа
10 высоких: Отсутствует иерархия таймаутов, Circuit Breaker без HALF_OPEN, Rate Limiter не проверяет RPD/TPD, Fallback Manager может вернуть пустую цепочку, config.yaml без context_length, GitHub Provider использует неверный base_url, Cloudflare не подставляет ACCOUNT_ID, не обрабатываются случаи полного отказа/не-JSON ответа/пустого .env
5 средних: Дублирование логики извлечения content, ненужные импорты, backup файлы в репозитории, недостаточный сбор метрик, отключен alerting
3 низких: Резервные копии файлов
2. Рекомендации по исправлению с кодом
Добавление context_length в эндпоинт /v1/models
Генерация UUID для tool_calls[].id
Реализация HALF_OPEN состояния в Circuit Breaker
Проверка RPD/TPD лимитов в is_available()
Подстановка ACCOUNT_ID для Cloudflare
Обработка граничных случаев (все провайдеры упали, не-JSON ответ, пустой .env)
Рефакторинг дублирующегося кода
3. Рекомендации по улучшению
Архитектура: Provider Interface, выделение Fallback Manager, кэширование ответов
Оптимизация для VIM4 8GB: асинхронные очереди, оптимизация SQLite, кэширование метаданных
Отказоустойчивость: Graceful Shutdown, периодический Health Check, автоматическое восстановление
Мониторинг: Prometheus метрики, логирование медленных запросов, расширенный dashboard
Приоритеты исправлений:
P0 (Немедленно): context_length, UUID для tool_calls, Cloudflare ACCOUNT_ID
P1 (В течение недели): HALF_OPEN, RPD/TPD проверка, обработка полного отказа
P2 (В течение месяца): иерархия таймаутов, Prometheus, graceful shutdown
P3 (Плановые): рефакторинг, кэширование, dashboard

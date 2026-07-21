# DEVIN AUDIT — Consilium v7.1 (Hermes Agent LLM Proxy)  
  
> Аудит выполнен Devin. Репозиторий: `samsonoff80/hermes` (ref `main`).  
> Платформа: VIM4 ARM64, 8GB RAM, Ubuntu 24.04, Python 3.11 + FastAPI + httpx.  
> Документ носит рекомендательный характер: приведённые фрагменты кода — **предложения**, рабочие файлы не изменялись.  
  
## Оглавление  
1. Критический баг «200 OK → Provider failed after retries»  
2. Rate Limiter  
3. Circuit Breaker  
4. Мёртвый код и рассинхроны  
5. Балльная система провайдеров  
6. Состояние агентов  
7. Рекомендации по модернизации  
8. Совместимость с Hermes Agent v0.19  
  
---  
  
## 1. КРИТИЧЕСКИЙ БАГ — «провайдер вернул 200, но Hermes получает Provider failed after retries»  
  
**Файл:** `consilium/consilium_server.py`, функция `chat_completions`, строки ~644–790.  
  
### Симптом  
Hermes → Consilium → провайдер возвращает 200 OK → Hermes получает «Provider failed after retries».  
  
### Первопричины  
  
**1.1. Двойной вызов `call_provider`, результат первого отбрасывается.**  
```python  
# строка 725 — ПЕРВЫЙ вызов (target_provider может быть None!)  
provider_resp = await call_provider(target_provider, messages, target_model, stream, temperature, max_tokens)  
...  
# строка 756 — ВТОРОЙ вызов, перезаписывает provider_resp  
provider_resp = await call_provider(target_provider, messages, target_model, stream, temperature, max_tokens)  
```  
Результат первого (возможно успешного) вызова теряется.  
  
**1.2. Блок 726–742 перезатирает выбор роутера.**  
Даже когда Task Router корректно выбрал провайдера (строки 701–714), `else`-ветка (736–740) берёт **первый попавшийся** провайдер с ключами и меняет `target_model` на `p["models"][0]`. Логика роутинга обесценивается.  
  
**1.3. `UnboundLocalError` в fallback-блоке (763–776).**  
```python  
if provider_resp is None:  
    for p in PROVIDERS:  
        if pname == target_provider["name"] and pmodel == target_model:  # pname/pmodel!  
```  
`pname` и `pmodel` — переменные цикла роутера (строки 704–705). При `model != "auto"` цикл не выполнялся → `NameError/UnboundLocalError` → HTTP 500. Плюс вложенный `for p in PROVIDERS` затеняет внешний `p`.  
  
**1.4. Таймаут-математика превышает дедлайн Hermes.**  
`PROVIDER_TIMEOUT = 30.0` (строка 67), два последовательных вызова = до 60с. Hermes ждёт `request_timeout: 45` (`config.yaml`, строка 70). Hermes рвёт соединение по таймауту → «Provider failed after retries», хотя первый провайдер уже вернул 200.  
  
**1.5. `OVERALL_DEADLINE = 45.0` (строка 69) объявлен, но нигде не используется.** Общего дедлайна на весь запрос нет.  
  
### Решение — единый линейный поток  
```python  
@app.post("/v1/chat/completions")  
async def chat_completions(request: Request, authorization: Optional[str] = Header(None)):  
    start_time = time.time()  
    request_id = f"req-{uuid.uuid4().hex[:12]}"   # UUID вместо int(time*1000)  
    try:  
        body = await request.json()  
    except Exception:  
        raise HTTPException(400, "Invalid JSON")  
  
    messages = filter_system_prompt(body.get("messages", []))  
    if not messages:  
        raise HTTPException(400, "Messages required")  
  
    model = body.get("model") or "auto"  
    stream = False  
    temperature = body.get("temperature", 0.7)  
    max_tokens = body.get("max_tokens", 4096)  
    session_key = request.headers.get("X-Session-Key")  
  
    # 1. Собираем упорядоченный список кандидатов (provider, model)  
    candidates = build_candidates(model, messages, session_key, request_id)  
    if not candidates:  
        raise HTTPException(503, "No providers available")  
  
    # 2. Единый перебор с ОБЩИМ дедлайном  
    provider_resp, used = None, None  
    async def _try_all():  
        nonlocal provider_resp, used  
        for prov, mdl in candidates:  
            ok, reason = rate_limiter.is_available(prov["name"])  
            if not ok:  
                logger.info(f"[{request_id}] ⏭️ {prov['name']} skipped: {reason}")  
                continue  
            if not circuit_breaker.is_available(prov["name"]):  
                continue  
            resp = await call_provider(prov, messages, mdl, stream, temperature, max_tokens)  
            if isinstance(resp, dict) and "error" in resp:  
                resp = None  
            if resp is not None:  
                provider_resp, used = resp, (prov, mdl)  
                return  
    try:  
        await asyncio.wait_for(_try_all(), timeout=OVERALL_DEADLINE)  
    except asyncio.TimeoutError:  
        logger.error(f"[{request_id}] ⏱️ overall deadline {OVERALL_DEADLINE}s exceeded")  
  
    if provider_resp is None:  
        await alert_all_providers_down()  
        raise HTTPException(503, "All providers failed")  
  
    prov, mdl = used  
    if session_key:  
        sticky_sessions[session_key] = (prov["name"], mdl, time.time() + STICKY_TTL)  
    circuit_breaker.record_success(prov["name"])  
    provider_stats.record_success(prov["name"], time.time()-start_time,  
                                  (provider_resp.get("usage") or {}).get("total_tokens", 0))  
    provider_scoring.record_success(prov["name"], time.time()-start_time)  # см. §5  
  
    resp = JSONResponse(provider_resp)  
    resp.headers["X-Request-ID"] = request_id  
    resp.headers["X-Trace-ID"] = request_id  
    return resp  
```  
И уменьшить таймаут на попытку, чтобы уложиться в дедлайн Hermes:  
```python  
PROVIDER_TIMEOUT = 20.0   # было 30.0 — 2 попытки по 20с < 45с  
OVERALL_DEADLINE = 40.0   # с запасом до 45с request_timeout  
```  
  
---  
  
## 2. RATE LIMITER  
  
**Файл:** `consilium/rate_limiter.py`.  
  
| Проблема | Строки | Описание |  
|---|---|---|  
| `is_available` не вызывается | 39–48 | Возвращает кортеж `(bool, reason)`, но в `call_provider` проверяется только circuit breaker. Лимиты RPM/TPM/RPD/TPD/cooldown не применяются. |  
| `_load_state` ничего не грузит | 26–30 | Тело цикла — только комментарий. Persistence из SQLite не восстанавливается. |  
| Хардкод `key_index=0` | server 452–455 | `mark_429`/`mark_402` всегда помечают ключ 0, а `get_next_key` ротирует ключи → блокируется не тот ключ. |  
| Нет эскалации cooldown | 53–56 | Всегда `COOLDOWN_STEPS[0]` (90с), лестница шагов не используется. |  
| `record_request` — заглушка | 50–51 | `pass`, счётчики токенов не ведутся. |  
  
### Решение  
```python  
def _load_state(self):  
    with sqlite3.connect(str(DB_PATH)) as conn:  
        for row in conn.execute("SELECT * FROM rate_limits"):  
            provider, ki, rpm, tpm, rpd, tpd, ws, ds, co, c429, dis = row  
            self.state[(provider, ki)] = {  
                "cooldown_until": co, "consecutive_429": c429,  
                "disabled": bool(dis), "rpd": rpd, "tpd": tpd,  
            }  
  
def mark_429(self, provider, key_index):  
    st = self.state.setdefault((provider, key_index), {})  
    st["consecutive_429"] = st.get("consecutive_429", 0) + 1  
    step = COOLDOWN_STEPS[min(st["consecutive_429"]-1, len(COOLDOWN_STEPS)-1)]  
    st["cooldown_until"] = time.time() + step  
    self._save_state(provider, key_index, 0,0,0,0,0,0, st["cooldown_until"], st["consecutive_429"], 0)  
```  
В `call_provider` перед вызовом провайдера:  
```python  
ok, reason = rate_limiter.is_available(provider["name"], key_index)  
if not ok:  
    return None  
```  
И передавать реальный `key_index` в `mark_429/mark_402`.  
  
---  
  
## 3. CIRCUIT BREAKER  
  
**Файл:** `consilium/circuit_breaker.py`, строка 8.  
  
- **Порог 10 вместо 5.** README обещает срабатывание после 5 сетевых ошибок.  
- **Таймауты не считаются.** В `call_provider` (server 448–450) `httpx.TimeoutException` возвращает `None` **без** `record_failure` — таймауты не учитываются брейкером.  
  
### Решение  
```python  
# circuit_breaker.py  
def __init__(self, threshold=5, cooldown=60):   # было 10  
```  
```python  
# consilium_server.py, call_provider  
except httpx.TimeoutException:  
    circuit_breaker.record_failure(provider["name"])  
    provider_stats.record_failure(provider["name"])  
    provider_scoring.record_timeout(provider["name"])   # см. §5  
    logger.warning(f"⏱️ {provider['name']}: timeout after {PROVIDER_TIMEOUT}s")  
    return None  
```  
  
---  
  
## 4. МЁРТВЫЙ КОД И РАССИНХРОНЫ  
  
| # | Файл / строки | Проблема | Решение |  
|---|---|---|---|  
| 4.1 | `health_checker.py` 18–26 / server `lifespan` 109–115 | `check_all_providers` не вызывается; startup только пишет лог. | Вызвать в `lifespan` до `yield`. |  
| 4.2 | `model_catalog.py` | Не импортируется; эндпоинтов `/models`, `/stats/providers` из README нет (есть только `/v1/models`, server 636–642). | Добавить эндпоинты. |  
| 4.3 | `key_encryption.py` 6–11 | `load_key` не вызывается → префикс `enc:` не расшифровывается. `Fernet` — это AES-128-CBC+HMAC, **не AES-256-GCM** (README неверен). `get_cipher` при отсутствии ключа молча генерирует случайный → расшифровка между перезапусками невозможна. | Вызывать `load_key`; либо реализовать реальный AES-256-GCM (`cryptography.hazmat.AESGCM`), либо исправить README; требовать `CONSILIUM_ENCRYPTION_KEY`. |  
| 4.4 | `provider_stats.py` 32–38 | `record_failure` не вызывается нигде. | Вызывать при таймаутах/ошибках. |  
| 4.5 | `alerting.py` 24–28 / server 28 | `alert_circuit_breaker`, `alert_provider_disabled` объявлены, но не вызываются. | Вызывать при OPEN брейкера и отключении ключа. |  
| 4.6 | server 34, 80–87 vs `providers/base.py` 23–42 | Двойной источник ключей: сервер грузит `.env` из `/home/khadas/.hermes/skills/consilium/.env`, `BaseProvider.load_keys` — из `consilium/.env`. | Единый путь/механизм. |  
| 4.7 | server 73–78 | `load_keys` читает только `range(1,4)` → максимум 3 ключа, вопреки «любое количество». | `while`-цикл как в `base.py`. |  
| 4.8 | server 81–88 | `fallback.build_chains(PROVIDERS)` вызывается внутри цикла по провайдерам (N раз). | Вынести из цикла. |  
| 4.9 | `fallback_manager.py` 27–28 | `PRIORITY` начинается с `mistral`, README — с `groq`. | Синхронизировать. |  
| 4.10 | server 106 | `sticky_sessions` без очистки протухших записей → утечка памяти. | Периодически чистить по `expiry`. |  
| 4.11 | `providers/cloudflare.py` 7 | В `models` — embedding/image/tts (`bge-m3`, `flux`, `melotts`, `distilbert`, `qwen3-embedding`). Их выберут как chat-модель → мусор/ошибка. | Оставить только чат-модели. |  
| 4.12 | server 654–655 | `request_id` = `int(time*1000)`, не UUID; `X-Request-ID`/`X-Trace-ID` не проставляются. | UUID + заголовки (см. §1). |  
| 4.13 | server 665–669 | System prompt filter не совпадает с README; `# Finishing the job.*` c `DOTALL` вырежет всё до конца, включая AGENTS.md, если он идёт следом. | Ограничить регэкспы, не использовать жадный `DOTALL`. |  
  
---  
  
## 5. БАЛЛЬНАЯ СИСТЕМА ПРОВАЙДЕРОВ (замена статичного PRIORITY)  
  
### Формула  
```  
score(p) =  w1 * success_rate  
          + w2 * (1 / (1 + avg_latency_sec))  
          + w3 * normalized_rpd            # нормированный дневной лимит [0..1]  
          - k1 * recent_429  
          - k2 * recent_5xx  
          - k3 * recent_timeouts  
          - k4 * (1 if context_window < MIN_CONTEXT else 0)  
```  
Веса по умолчанию (в конфиг): `w1=1.0, w2=0.5, w3=0.3, k1=0.4, k2=0.4, k3=0.3, k4=0.2`.  
`recent_*` — счётчики за скользящее окно (например, последние 5 минут), затухают со временем.  
  
### Реализация — новый модуль `consilium/provider_scoring.py`  
```python  
import sqlite3, time, math  
from pathlib import Path  
  
DB_PATH = Path(__file__).parent / "provider_scores.db"  
WEIGHTS = dict(w1=1.0, w2=0.5, w3=0.3, k1=0.4, k2=0.4, k3=0.3, k4=0.2)  
MIN_CONTEXT = 8000  
WINDOW = 300  # сек  
  
class ProviderScoring:  
    def __init__(self):  
        with sqlite3.connect(str(DB_PATH)) as c:  
            c.execute("""CREATE TABLE IF NOT EXISTS scores(  
                provider TEXT PRIMARY KEY, success INT DEFAULT 0, total INT DEFAULT 0,  
                sum_latency REAL DEFAULT 0, r429 INT DEFAULT 0, r5xx INT DEFAULT 0,  
                rtimeout INT DEFAULT 0, context INT DEFAULT 0, ts REAL DEFAULT 0)""")  
  
    def _bump(self, provider, **inc):  
        with sqlite3.connect(str(DB_PATH)) as c:  
            c.execute("INSERT OR IGNORE INTO scores(provider) VALUES(?)", (provider,))  
            sets = ", ".join(f"{k}={k}+?" for k in inc)  
            c.execute(f"UPDATE scores SET {sets}, ts=? WHERE provider=?",  
                      (*inc.values(), time.time(), provider))  
            c.commit()  
  
    def record_success(self, provider, latency):  
        self._bump(provider, success=1, total=1, sum_latency=latency)  
    def record_429(self, provider):     self._bump(provider, total=1, r429=1)  
    def record_5xx(self, provider):     self._bump(provider, total=1, r5xx=1)  
    def record_timeout(self, provider): self._bump(provider, total=1, rtimeout=1)  
  
    def score(self, provider, context_window=MIN_CONTEXT, max_rpd=1):  
        with sqlite3.connect(str(DB_PATH)) as c:  
            row = c.execute("SELECT success,total,sum_latency,r429,r5xx,rtimeout FROM scores WHERE provider=?",  
                            (provider,)).fetchone()  
        if not row or row[1] == 0:  
            return 0.5  # нейтральный старт для новых провайдеров  
        success, total, sum_lat, r429, r5xx, rto = row  
        sr = success / total  
        avg_lat = sum_lat / max(success, 1)  
        w = WEIGHTS  
        return (w["w1"]*sr + w["w2"]*(1/(1+avg_lat)) + w["w3"]*(context_window/128000)  
                - w["k1"]*r429 - w["k2"]*r5xx - w["k3"]*rto  
                - w["k4"]*(1 if context_window < MIN_CONTEXT else 0))  
  
provider_scoring = ProviderScoring()  
```  
  
### Интеграция в `chat_completions` (при `model == "auto"`)  
```python  
task_chain = fallback.get_chain(task)  
task_chain.sort(key=lambda e: provider_scoring.score(e["provider"]), reverse=True)  
```  
Баллы обновляются в реальном времени (success/429/5xx/timeout) и хранятся в SQLite → **восстанавливаются после перезапуска**.  
  
---  
  
## 6. СОСТОЯНИЕ АГЕНТОВ  
  
Все 6 агентов присутствуют, у каждого есть `SOUL.md`, `SKILL.md`, `PROGRESS.md`:  
`orchestrator`, `optimizer`, `product-analyst`, `source-scout`, `parsing-engineer`, `parser` (плюс `default`).  
  
| Агент | SOUL/SKILL/PROGRESS | Замечания |  
|---|---|---|  
| `orchestrator` | ✅ / ✅ / ✅ | Протокол `read_file → delegate_task` описан согласованно; цепочка `product-analyst → source-scout → parsing-engineer → parser` совпадает в `SOUL.md`, `SKILL.md` и README (стр. 320). |  
| `product-analyst` | ✅ / ✅ / ✅ (+ archive) | Начальное звено цепочки, корректно. |  
| `source-scout` | ✅ / ✅ / ✅ (+ MEMORY.md, data/) | Много reference-файлов; согласован. |  
| `parsing-engineer` | ✅ / ✅ / ✅ (+ archive, references/) | Согласован. |  
| `parser` | ✅ / ✅ / ✅ (+ archive, references/) | Финальное звено, согласован. |  
| `optimizer` | ✅ / ✅ / ✅ | Вне основной цепочки. |  
  
**Что улучшить:**  
- Проверить, что пути в `SKILL.md` (`read_file("agents/<слой>/…")`) совпадают с рабочими путями `config.yaml` (`/home/khadas/.hermes/agents/...`) — относительный vs абсолютный путь может ломать `read_file`.  
- Task Router на сервере (`task = chat/search/code/analysis`) не связан напрямую с агентной цепочкой — стоит задокументировать это разграничение (роутинг LLM-провайдеров ≠ делегирование агентам).  
  
---  
  
## 7. РЕКОМЕНДАЦИИ ПО МОДЕРНИЗАЦИИ  
  
**Архитектура.** Вынести всю провайдер-специфику из `consilium_server.py` в модули `providers/*` (сервер не должен знать про ключи/модели конкретных провайдеров). Единый интерфейс `BaseProvider.chat()`.  
  
**Надёжность / граничные случаи:**  
- Все провайдеры упали → сейчас 503 «All providers failed» (корректно после фикса §1).  
- `.env` не найден/пустой → `load_keys` вернёт `[]`; keyless-провайдеры (`cloudflare`) должны остаться рабочими — добавить явную проверку и лог.  
- 100 одновременных запросов → ограничить конкурентность `asyncio.Semaphore` и переиспользовать единый `httpx.AsyncClient` (уже есть `http_client`, закрывается в `lifespan` 114).  
- Не-JSON ответ провайдера → оборачивать `resp.json()` в `try/except` и трактовать как ошибку (fallback).  
- System prompt > 100K токенов → предварительная обрезка по `context_length: 128000`.  
- Спецсимволы в ключе → не логировать ключи, не подставлять в f-строки без экранирования.  
  
**Оптимизация под VIM4 8GB:** единый httpx-клиент; SQLite в WAL-режиме; ограничение `max_tokens`; периодическая очистка `sticky_sessions`; `Semaphore` для контроля памяти.  
  
**Мониторинг:** сквозной `X-Request-ID`, эндпоинт `/stats/providers`, dashboard со `score` из §5, алерты через `alerting.py` (сейчас не вызываются).  
  
**Расширяемость:** автообнаружение провайдеров в `providers/__init__.py`; новый провайдер = новый файл-наследник `BaseProvider`; новый тип задачи = ключевые слова в Task Router + запись в `fallback.get_chain`; приоритет — через балльную систему §5 вместо статичного `PRIORITY`.  
  
---  
  
## 8. СОВМЕСТИМОСТЬ С HERMES AGENT v0.19  
  
⚠️ Внешнюю документацию (`hermes-agent.nousresearch.com/docs`, GitHub NousResearch) в окружении аудита загрузить нельзя — раздел основан на коде.  
  
- `config.yaml`: `_config_version: 33`, `model.provider: custom`, `base_url: http://127.0.0.1:8765/v1`, `api_mode: openai`, `request_timeout: 45`. Формат OpenAI-совместимый — обычно кросс-версионно стабилен.  
- README упоминает Hermes v0.18.2 (стр. 61) — рассинхрон с целевой v0.19.  
- **Требуется проверка на живой v0.19:** изменения формата system prompt, формата ответа API, новых фич. Рекомендуется отдельная Devin-сессия с сетевым доступом.  
  
---  
  
*Конец аудита.*

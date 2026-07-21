#!/usr/bin/env python3
"""CONSILIUM SERVER v6.16 — Preserves tool_calls for gateway execution.
Returns content + tool_calls (if present). No XML/CDATA rendering.
Guarantees tool_calls field is always present in message (empty list if none).
Rescues inline tool calls from content (Hermes/Qwen/XML formats)."""
import os, sys, json, time, asyncio, logging, hashlib, re, uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, AsyncGenerator
from collections import defaultdict
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

import sqlite3
import httpx
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Импортируем провайдеры из централизованного модуля
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from providers import PROVIDERS
from rate_limiter import RateLimiter
from circuit_breaker import circuit_breaker
from provider_stats import provider_stats
from provider_scoring import provider_scoring, WEIGHTS, MIN_CONTEXT, WINDOW_SECONDS
from alerting import alert_all_providers_down, alert_circuit_breaker
from dashboard import dashboard_html
rate_limiter = RateLimiter()
from fallback_manager import fallback

# Загружаем ключи для Consilium
load_dotenv("/home/khadas/.hermes/skills/consilium/.env")

# === Usage Logger ===
USAGE_DB = Path(__file__).parent / "usage.db"
def _init_usage():
    conn = sqlite3.connect(str(USAGE_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS usage (ts TEXT, provider TEXT, model TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER)")
    conn.commit(); conn.close()
def _log_usage(provider, model, usage_dict):
    try:
        p = (usage_dict or {}).get("prompt_tokens", 0)
        c = (usage_dict or {}).get("completion_tokens", 0)
        conn = sqlite3.connect(str(USAGE_DB))
        conn.execute("INSERT INTO usage VALUES (?,?,?,?,?,?)", (datetime.now().isoformat(), provider, model, p, c, p+c))
        conn.commit(); conn.close()
    except: pass
_init_usage()


LOG_DIR = Path.home() / ".hermes" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler(LOG_DIR / "consilium.log", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("consilium")

# ТАЙМАУТЫ: уменьшен до 20с на провайдера, общий дедлайн 40с (Hermes ждет 45с)
PROVIDER_TIMEOUT = 20.0
CONNECT_TIMEOUT = 5.0
OVERALL_DEADLINE = 40.0  # Hermes ждет 45с (request_timeout в config.yaml)
STICKY_TTL = 300.0  # 5 минут TTL для sticky sessions

# ЗАГРУЗКА КЛЮЧЕЙ из импортированных провайдеров
def load_keys(prefix: str) -> list:
    """Загружает все ключи с префиксом PREFIX_1, PREFIX_2, ... PREFIX_N"""
    keys = []
    i = 1
    while True:
        k = os.getenv(f"{prefix}_{i}", "")
        if not k:
            break
        keys.append(k)
        i += 1
    return keys

PROVIDER_KEYS = {}
for p in PROVIDERS:
    if p.get("keyless", False):
        PROVIDER_KEYS[p["name"]] = []
        logger.info(f"{p['name']}: keyless provider (no keys needed)")
    else:
        PROVIDER_KEYS[p["name"]] = load_keys(p["key_prefix"])
        logger.info(f"{p['name']}: {len(PROVIDER_KEYS[p['name']])} keys")

# Строим цепочки провайдеров ОДИН РАЗ после загрузки всех ключей
fallback.build_chains(PROVIDERS)

key_indexes = defaultdict(int)
key_indexes_lock = asyncio.Lock()

def get_next_key(name: str) -> str:
    keys = PROVIDER_KEYS.get(name, [])
    if not keys: return ""
    idx = key_indexes[name] % len(keys)
    key_indexes[name] = idx + 1
    return keys[idx]

# HTTP КЛИЕНТ с таймаутом 30с на провайдера
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(PROVIDER_TIMEOUT, connect=CONNECT_TIMEOUT),
    limits=httpx.Limits(max_connections=150, max_keepalive_connections=30)
)

# STICKY SESSIONS
sticky_sessions: Dict[str, Tuple[str, str, float]] = {}

async def cleanup_sticky_sessions():
    """Периодическая очистка протухших sticky сессий."""
    while True:
        await asyncio.sleep(60)  # Проверяем каждую минуту
        now = time.time()
        expired = [key for key, (_, _, expiry) in sticky_sessions.items() if expiry <= now]
        for key in expired:
            del sticky_sessions[key]
        if expired:
            logger.info(f"🧹 Cleaned up {len(expired)} expired sticky sessions")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — проверяем провайдеров
    logger.info("🏥 Health check starting...")
    # Запускаем задачу очистки sticky сессий
    asyncio.create_task(cleanup_sticky_sessions())
    yield
    # Shutdown
    await http_client.aclose()

app = FastAPI(title="Consilium LLM Gateway", version="6.17", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- INLINE TOOL CALL RESCUE (like FreeLLMAPI rescueFailedGeneration) ----------

# Regex patterns for inline tool call formats
INLINE_TOOL_CALL_PATTERNS = [
    # <function=name>{...}</function>  (Hermes style)
    re.compile(r'<function=([a-zA-Z_][a-zA-Z0-9_]*)>\s*(\{.*?\})\s*</function>', re.DOTALL),
    # 那些\n{"name": "...", "arguments": ...}\n那些  (Qwen style)
    re.compile(r'那些\s*(\{.*?\})\s*那些', re.DOTALL),
    # <|tool_call_begin|>...<|tool_call_end|>  (some models)
    re.compile(r'<\|tool_call_begin\|>(.*?)<\|tool_call_end\|>', re.DOTALL),
    # 那些...[/TOOL_CALLS] with JSON array inside
    re.compile(r'\[TOOL_CALLS\]\s*(\[.*?\])\s*\[/TOOL_CALLS\]', re.DOTALL),
]

def rescue_inline_tool_calls(content: str, available_tool_names: set[str] | None = None) -> List[Dict]:
    """Extract structured tool_calls from inline XML/JSON in content text.
    
    Mirrors FreeLLMAPI's rescueInlineToolCalls. Returns list of tool_calls in OpenAI format.
    """
    if not content or not isinstance(content, str):
        return []
    
    calls = []
    call_index = 0
    
    for pattern in INLINE_TOOL_CALL_PATTERNS:
        for match in pattern.finditer(content):
            call_index += 1
            try:
                if pattern.pattern.startswith(r'<function='):
                    # Hermes: <function=name>{args}</function>
                    name = match.group(1)
                    args_str = match.group(2).strip()
                elif pattern.pattern.startswith(r'那些'):
                    # Qwen: 那些{json}那些
                    json_str = match.group(1).strip()
                    parsed = json.loads(json_str)
                    name = parsed.get("name", "")
                    args_str = json.dumps(parsed.get("arguments", {}), ensure_ascii=False)
                elif pattern.pattern.startswith(r'<\|tool_call_begin\|>'):
                    # Generic: <|tool_call_begin|>json<|tool_call_end|>
                    json_str = match.group(1).strip()
                    parsed = json.loads(json_str)
                    name = parsed.get("name", "")
                    args_str = json.dumps(parsed.get("arguments", {}), ensure_ascii=False)
                elif pattern.pattern.startswith(r'\[TOOL_CALLS\]'):
                    # CDATA wrapper: 那些[...][/TOOL_CALLS]
                    json_str = match.group(1).strip()
                    parsed = json.loads(json_str)
                    if isinstance(parsed, list):
                        for item in parsed:
                            call_index += 1
                            name = item.get("name", "") or item.get("function", {}).get("name", "")
                            args = item.get("arguments", {}) or item.get("function", {}).get("arguments", {})
                            args_str = json.dumps(args, ensure_ascii=False)
                            if name and (not available_tool_names or name in available_tool_names):
                                calls.append({
                                    "id": f"call_rescued_{call_index}",
                                    "type": "function",
                                    "function": {"name": name, "arguments": args_str}
                                })
                        continue
                    else:
                        name = parsed.get("name", "") or parsed.get("function", {}).get("name", "")
                        args_str = json.dumps(parsed.get("arguments", {}) or parsed.get("function", {}).get("arguments", {}), ensure_ascii=False)
                else:
                    continue
                
                if name and (not available_tool_names or name in available_tool_names):
                    calls.append({
                        "id": f"call_rescued_{call_index}",
                        "type": "function",
                        "function": {"name": name, "arguments": args_str}
                    })
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                logger.debug(f"Failed to parse inline tool call: {e}")
                continue
    
    return calls

def strip_inline_tool_calls(content: str) -> str:
    """Remove inline tool call XML/JSON from content for clean text."""
    if not content:
        return ""
    cleaned = content
    for pattern in INLINE_TOOL_CALL_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    # Also remove CDATA-style wrappers
    cleaned = re.sub(r'\[TOOL_CALLS\].*?\[/TOOL_CALLS\]', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<!\[CDATA\[.*?\]\]>', '', cleaned, flags=re.DOTALL)
    return cleaned.strip()

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ОБРАБОТКИ ОТВЕТОВ ПРОВАЙДЕРОВ ----------

def extract_openai_content(data: dict) -> Optional[str]:
    """Извлекает content из OpenAI-совместимого ответа (non-streaming)."""
    try:
        return data.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception:
        return None

def extract_finish_reason(data: dict) -> str:
    try:
        return data.get("choices", [{}])[0].get("finish_reason", "stop")
    except Exception:
        return "stop"

def extract_tool_calls(data: dict) -> Optional[list]:
    try:
        return data.get("choices", [{}])[0].get("message", {}).get("tool_calls")
    except Exception:
        return None

def extract_usage(data: dict) -> Optional[dict]:
    return data.get("usage")

def extract_reasoning_content(data: dict) -> Optional[str]:
    try:
        return data.get("choices", [{}])[0].get("message", {}).get("reasoning_content")
    except Exception:
        return None

# AI Horde specific extractors
def extract_aihorde_content(data: dict) -> Optional[str]:
    """Extract content from AI Horde response format."""
    try:
        # AI Horde returns: {"generations": [{"text": "..."}]}
        generations = data.get("generations", [])
        if generations:
            return generations[0].get("text", "")
    except Exception:
        pass
    return None

def extract_aihorde_finish_reason(data: dict) -> str:
    try:
        generations = data.get("generations", [])
        if generations:
            return generations[0].get("finish_reason", "stop")
    except Exception:
        pass
    return "stop"

def extract_aihorde_tool_calls(data: dict) -> Optional[list]:
    # AI Horde doesn't support tool calls natively
    return None

def extract_aihorde_usage(data: dict) -> Optional[dict]:
    # AI Horde doesn't return usage in standard format
    return None

def extract_aihorde_reasoning_content(data: dict) -> Optional[str]:
    return None

# HuggingFace specific extractors
def extract_huggingface_content(data: dict) -> Optional[str]:
    """Extract content from HuggingFace Inference API response."""
    try:
        # HuggingFace returns: [{"generated_text": "..."}] or {"generated_text": "..."}
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "")
        elif isinstance(data, dict):
            return data.get("generated_text", "")
    except Exception:
        pass
    return None

def extract_huggingface_finish_reason(data: dict) -> str:
    return "stop"

def extract_huggingface_tool_calls(data: dict) -> Optional[list]:
    return None

def extract_huggingface_usage(data: dict) -> Optional[dict]:
    return None

def extract_huggingface_reasoning_content(data: dict) -> Optional[str]:
    return None

def normalize_message_content(data: dict, tool_calls: Optional[list] = None, provider_format: str = "openai") -> Optional[str]:
    """FreeLLMAPI-style normalize: content -> reasoning_content -> null (if tool_calls).
    
    Per FreeLLMAPI normalizeChoices: fold reasoning into content ONLY when no tool_calls.
    When tool_calls present, content should be null (not empty string).
    """
    if provider_format == "aihorde":
        content = extract_aihorde_content(data)
    elif provider_format == "huggingface":
        content = extract_huggingface_content(data)
    else:
        content = extract_openai_content(data)
    
    has_tool_calls = tool_calls is not None and len(tool_calls) > 0
    
    if content is not None and content != "":
        return content
    
    # Fallback на reasoning_content (как в FreeLLMAPI normalizeChoices)
    # Но ТОЛЬКО если нет tool_calls!
    if not has_tool_calls:
        if provider_format == "aihorde":
            reasoning = extract_aihorde_reasoning_content(data)
        elif provider_format == "huggingface":
            reasoning = extract_huggingface_reasoning_content(data)
        else:
            reasoning = extract_reasoning_content(data)
        if reasoning is not None and reasoning != "":
            return str(reasoning)
    
    # Если есть tool_calls — content должен быть null (OpenAI spec)
    if has_tool_calls:
        return None
    
    return ""

def ensure_tool_calls_field(message: dict) -> dict:
    """Гарантирует наличие поля tool_calls в message (пустой список если отсутствует)."""
    if "tool_calls" not in message:
        message["tool_calls"] = []
    elif message["tool_calls"] is None:
        message["tool_calls"] = []
    return message

# ---------- ВЫЗОВ ПРОВАЙДЕРОВ ----------

async def call_provider(provider: dict, messages: list, model: str, stream: bool, temperature: float, max_tokens: int) -> Optional[Any]:
    """Вызывает провайдера. Возвращает httpx.Response (stream) или dict (non-stream/cloudflare/aihorde/huggingface)."""
    # Circuit breaker check
    if not circuit_breaker.is_available(provider["name"]):
        logger.warning(f"🔴 {provider['name']}: circuit breaker blocked")
        return None
    key = get_next_key(provider["name"])
    keys_exist = bool(PROVIDER_KEYS.get(provider["name"]))
    is_keyless = provider.get("keyless", False)
    
    headers = {"Content-Type": "application/json"}
    # Добавляем Authorization только если есть ключи (не анонимный провайдер)
    if keys_exist and key:
        headers["Authorization"] = f"Bearer {key}"
    elif not keys_exist and not is_keyless:
        logger.warning(f"⚠️ {provider['name']}: no keys available")
        return None
    else:
        logger.info(f"🔓 {provider['name']}: {'keyless' if is_keyless else 'anonymous'} provider, no Authorization header")

    provider_format = provider.get("format", "openai")
    
    # Формируем payload в зависимости от формата
    if provider_format == "aihorde":
        # AI Horde format: https://aihorde.net/api/v1/generate/text
        # Requires: prompt, params, models, etc.
        # Convert messages to prompt
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        payload = {
            "prompt": prompt,
            "params": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.9,
            },
            "models": [model],
            "nsfw": False,
            "censor": False,
        }
        url = provider["base_url"]
    elif provider["name"] == "cloudflare":
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if not account_id:
            logger.warning(f"⚠️ {provider['name']}: CLOUDFLARE_ACCOUNT_ID not set")
            return None
        url = provider["base_url"].format(ACCOUNT_ID=account_id) + f"/{model}"
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
    elif provider_format == "huggingface":
        # HuggingFace Inference API format
        # Convert messages to a single prompt
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        url = provider["base_url"] + f"/{model}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "top_p": 0.9,
                "return_full_text": False,
            },
        }
    else:
        # Standard OpenAI-compatible format
        url = provider["base_url"] + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    try:
        if stream:
            resp = await http_client.post(url, headers=headers, json=payload, timeout=PROVIDER_TIMEOUT)
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: проверяем статус для streaming ответов
            resp.raise_for_status()
            return resp
        else:
            resp = await http_client.post(url, headers=headers, json=payload, timeout=PROVIDER_TIMEOUT)
            resp.raise_for_status()
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: безопасный парсинг JSON
            try:
                data = resp.json()
                usage_info = data.get("usage", {})
                if usage_info:
                    logger.info(f"📊 usage: {usage_info}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"❌ {provider['name']}: Invalid JSON response: {e}, text: {resp.text[:3000]}")
                return None
    except httpx.TimeoutException:
        circuit_breaker.record_failure(provider["name"])
        provider_stats.record_failure(provider["name"], "timeout")
        provider_scoring.record_failure(provider["name"], "timeout")
        logger.warning(f"⏱️ {provider['name']}: timeout after {PROVIDER_TIMEOUT}s")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            rate_limiter.mark_429(provider["name"], 0)
            provider_stats.record_failure(provider["name"], "429")
            provider_scoring.record_failure(provider["name"], "429")
        elif e.response.status_code in (401, 402, 403):
            rate_limiter.mark_402(provider["name"], 0)
            provider_stats.record_failure(provider["name"], "402")
            provider_scoring.record_failure(provider["name"], "402")
        elif e.response.status_code >= 500:
            provider_stats.record_failure(provider["name"], "5xx")
            provider_scoring.record_failure(provider["name"], "5xx")
        logger.warning(f"❌ {provider['name']}: HTTP {e.response.status_code} - {e.response.text[:200]}")
        return None
    except Exception as e:
        circuit_breaker.record_failure(provider["name"])
        provider_stats.record_failure(provider["name"], "other")
        provider_scoring.record_failure(provider["name"], "other")
        logger.warning(f"💥 {provider['name']}: {type(e).__name__}: {e}")
        return None

# ---------- СТРИМИНГ ----------

async def stream_provider_response(response: httpx.Response, model: str, available_tool_names: set[str] | None = None) -> AsyncGenerator[str, None]:
    """Проксирует SSE поток от провайдера, ПРОБРАСЫВАЯ tool_calls дельту.
    Gateway runner соберёт полные tool_calls из чанков.
    Also rescues inline tool calls from content deltas if provider doesn't send structured tool_calls.
    """
    accumulated_content = ""
    accumulated_tool_calls: List[Dict] = []
    seen_tool_calls_in_stream = False
    
    async for line in response.aiter_lines():
        if not line.startswith("data: "):
            continue
        data = line[6:].strip()
        if data == "[DONE]":
            # If we accumulated content with inline tool calls but no structured tool_calls,
            # rescue them in the final chunk
            if accumulated_content and not seen_tool_calls_in_stream and available_tool_names:
                rescued = rescue_inline_tool_calls(accumulated_content, available_tool_names)
                if rescued:
                    logger.info(f"[Consilium] Rescued {len(rescued)} inline tool call(s) from stream content")
                    # Send rescued tool_calls in final chunk
                    chunk_id = f"chatcmpl-{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
                    created = int(time.time())
                    final_chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"tool_calls": rescued},
                            "finish_reason": "tool_calls"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            break
        try:
            chunk = json.loads(data)
            # Track if structured tool_calls appear in stream
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                if "tool_calls" in delta and delta["tool_calls"]:
                    seen_tool_calls_in_stream = True
                    # Accumulate tool_calls deltas for potential rescue
                    for tc_delta in delta["tool_calls"]:
                        idx = tc_delta.get("index", 0)
                        while len(accumulated_tool_calls) <= idx:
                            accumulated_tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                        tc = accumulated_tool_calls[idx]
                        if "id" in tc_delta:
                            tc["id"] = tc_delta["id"]
                        if "function" in tc_delta:
                            func = tc_delta["function"]
                            if "name" in func:
                                tc["function"]["name"] = func["name"]
                            if "arguments" in func:
                                tc["function"]["arguments"] += func["arguments"]
                # Accumulate content for inline rescue fallback
                if "content" in delta and delta["content"]:
                    accumulated_content += delta["content"]
            
            # Пробрасываем чанк как есть (включая tool_calls в delta)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except json.JSONDecodeError:
            continue
        except Exception:
            continue

async def generate_fake_stream(response_data: dict, model: str, available_tool_names: set[str] | None = None, provider_format: str = "openai") -> AsyncGenerator[str, None]:
    """Создаёт SSE поток для нестриминговых провайдеров (Cloudflare, AI Horde, HuggingFace).
    Включает tool_calls в финальном чанке, если они есть.
    Rescues inline tool calls from content if structured tool_calls missing.
    """
    provider_format = provider_format or "openai"
    
    # Extract structured tool_calls first
    if provider_format == "aihorde":
        tool_calls = extract_aihorde_tool_calls(response_data)
        content = extract_aihorde_content(response_data) or ""
        reasoning = extract_aihorde_reasoning_content(response_data)
        finish_reason = extract_aihorde_finish_reason(response_data)
    elif provider_format == "huggingface":
        tool_calls = extract_huggingface_tool_calls(response_data)
        content = extract_huggingface_content(response_data) or ""
        reasoning = extract_huggingface_reasoning_content(response_data)
        finish_reason = extract_huggingface_finish_reason(response_data)
    else:
        tool_calls = extract_tool_calls(response_data)
        content = extract_openai_content(response_data) or ""
        reasoning = extract_reasoning_content(response_data)
        finish_reason = extract_finish_reason(response_data)
    
    # If no structured tool_calls, try to rescue from content
    if not tool_calls and content and available_tool_names:
        rescued = rescue_inline_tool_calls(content, available_tool_names)
        if rescued:
            logger.info(f"[Consilium] Rescued {len(rescued)} inline tool call(s) from non-stream content")
            tool_calls = rescued
            # When tool_calls rescued, content should be null per OpenAI spec
            content = None
    
    has_tool_calls = tool_calls is not None and len(tool_calls) > 0
    
    # Normalize content per FreeLLMAPI: fold reasoning only if no tool_calls
    if content is None or content == "":
        if not has_tool_calls and reasoning:
            content = str(reasoning)
        elif has_tool_calls:
            content = None
    
    chunk_id = f"chatcmpl-{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
    created = int(time.time())
    
    # Stream content only if no tool_calls (OpenAI spec: content=null when tool_calls present)
    if content and not has_tool_calls:
        words = content.split(" ")
        for i, word in enumerate(words):
            delta = word + (" " if i < len(words) - 1 else "")
            chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)
    
    # Final chunk with tool_calls (if any) and finish_reason
    final_delta = {}
    if has_tool_calls:
        final_delta["tool_calls"] = tool_calls
        finish_reason = "tool_calls"
    # Only include content in final delta if no tool_calls
    elif content:
        final_delta["content"] = content
    
    final_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": final_delta, "finish_reason": finish_reason}]
    }
    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"

# ---------- ENDPOINTS ----------


@app.get("/usage/today")
async def usage_today():
    try:
        conn = sqlite3.connect(str(USAGE_DB))
        today = datetime.now().strftime("%Y-%m-%d")
        rows = conn.execute("SELECT provider, model, SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens), COUNT(*) FROM usage WHERE ts LIKE ? GROUP BY provider, model", (today+"%",)).fetchall()
        conn.close()
        total = sum(r[4] for r in rows)
        return {"date": today, "total_tokens": total, "breakdown": [{"provider": r[0], "model": r[1], "prompt_tokens": r[2], "completion_tokens": r[3], "total_tokens": r[4], "requests": r[5]} for r in rows]}
    except: return {"date": datetime.now().strftime("%Y-%m-%d"), "total_tokens": 0}

@app.get("/")
async def root():
    return await dashboard_html(PROVIDERS, rate_limiter)

@app.get("/health")
async def health():
    return {"status": "ok", "providers": {p["name"]: len(PROVIDER_KEYS.get(p["name"], [])) for p in PROVIDERS}}

@app.get("/v1/models")
async def list_models():
    models = []
    for p in PROVIDERS:
        for m in p["models"]:
            models.append({"id": m, "object": "model", "owned_by": p["name"]})
    return {"object": "list", "data": models}

@app.get("/stats/providers")
async def get_provider_stats():
    """Возвращает статистику и баллы для всех провайдеров."""
    stats = []
    for p in PROVIDERS:
        provider_name = p["name"]
        score = provider_scoring.get_score(provider_name)
        pstats = provider_stats.get_stats(provider_name)
        pscoring = provider_scoring.get_stats(provider_name)
        
        stats.append({
            "name": provider_name,
            "score": round(score, 4),
            "success_rate": pstats.get("success", 0) / max(pstats.get("success", 0) + pstats.get("fail", 0), 1),
            "avg_latency": pstats.get("avg_latency", 0),
            "total_tokens": pstats.get("total_tokens", 0),
            "keys": len(PROVIDER_KEYS.get(provider_name, [])),
            "priority": score,
            "last_used": pstats.get("last_used", 0) if pstats else 0,
        })
    
    # Сортируем по баллам
    stats.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "providers": stats,
        "updated": time.time()
    }

@app.get("/stats/scoring")
async def get_scoring_details():
    """Возвращает детальную информацию о балльной системе."""
    return {
        "weights": WEIGHTS,
        "min_context": MIN_CONTEXT,
        "window_seconds": WINDOW_SECONDS,
        "all_scores": provider_scoring.get_all_scores()
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: Optional[str] = Header(None)):
    """OpenAI-совместимый эндпоинт. Возвращает content + tool_calls (всегда поле, пустой список если нет).
    
    Per FreeLLMAPI: 
    - content is null when tool_calls present
    - reasoning_content folded into content only when no tool_calls
    - inline tool calls rescued from content
    - tool_calls field always present (empty list if none)
    """
    start_time = time.time()
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    try:
        body = await request.json()
        logger.info(f'[{request_id}] 📥 Body: {json.dumps(body, ensure_ascii=False)[:3000]}')
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    messages = body.get("messages", [])

    # Фильтр: вырезаем блоки Hermes
    for m in messages:
        if m.get("role") == "system" and isinstance(m.get("content"), str):
            m["content"] = re.sub(r"You run on Hermes Agent.*?source of truth when the two differ\.\s*", "", m["content"], flags=re.DOTALL).strip()
            m["content"] = re.sub(r"# Finishing the job.*?(?=\n#|\Z)", "", m["content"], flags=re.DOTALL).strip()
            m["content"] = re.sub(r"# Parallel tool calls.*?(?=\n#|\Z)", "", m["content"], flags=re.DOTALL).strip()
            logger.info(f"[{request_id}] ✂️ Filtered: {len(m['content'])} chars")
    
    model = body.get("model", "auto")
    # Fix: treat empty string as auto
    if not model or model == "":
        model = "auto"
    stream = False  # Принудительно non-streaming для учёта токенов
    temperature = body.get("temperature", 0.7)
    max_tokens = body.get("max_tokens", 4096)
    tools = body.get("tools", [])
    
    # Build set of available tool names for inline rescue
    available_tool_names = {t.get("function", {}).get("name", "") for t in tools} if tools else None

    if not messages:
        raise HTTPException(400, "Messages required")

    # === Task Router v2 (Provider-aware) ===
    task = "chat"
    user_text = ([m.get("content", "") for m in messages if m.get("role") == "user"] or [""])[-1].lower() if [m for m in messages if m.get("role") == "user"] else ""
    if any(kw in user_text for kw in ["найди", "поиск", "источник", "сайт", "спарси", "scout", "url", "http", "парсинг сайт", "парс сайт"]):
        task = "search"
    elif any(kw in user_text for kw in ["код", "code", "функци", "function", "скрипт", "script", "python", "ошибк", "error", "bug", "парс", "parse"]):
        task = "code"
    elif any(kw in user_text for kw in ["анализ", "analysis", "сравни", "compare", "статус", "status", "почем", "why", "как работает"]):
        task = "analysis"
    logger.info(f"[{request_id}] 🎯 User text: {user_text[:100]}")
    logger.info(f"[{request_id}] 🎯 Task: {task}")

    # === ЕДИНЫЙ ПОТОК ВЫБОРА ПРОВАЙДЕРА ===
    target_provider = None
    target_model = None
    
    # 1. Sticky session support (проверяем сначала)
    session_key = request.headers.get("X-Session-Key")
    if session_key and session_key in sticky_sessions:
        prov_name, mod, expiry = sticky_sessions[session_key]
        if time.time() < expiry:
            for p in PROVIDERS:
                if p["name"] == prov_name and mod in p["models"]:
                    target_provider = p
                    target_model = mod
                    logger.info(f"[{request_id}] 🔒 Sticky session: {prov_name}/{mod}")
                    break
    
    # 2. Task Router + Fallback Manager
    if target_provider is None:
        if model == "auto":
            task_chain = fallback.get_chain(task)
            for entry in task_chain:
                for p in PROVIDERS:
                    if p["name"] == entry["provider"] and entry["model"] in p["models"]:
                        # Проверяем rate limiter и circuit breaker
                        key_index = 0
                        if PROVIDER_KEYS.get(p["name"]):
                            ok, reason = rate_limiter.is_available(p["name"], key_index)
                            if not ok:
                                logger.info(f"[{request_id}] ⏭️ {p['name']}:{key_index} skipped: {reason}")
                                continue
                        if not circuit_breaker.is_available(p["name"]):
                            logger.info(f"[{request_id}] 🔴 {p['name']}: circuit breaker blocked")
                            continue
                        target_provider = p
                        target_model = entry["model"]
                        model = entry["model"]
                        logger.info(f"[{request_id}] 🎯 Router: {task} → {entry['model']} @ {p['name']} (keys={entry['keys']})")
                        break
                if target_provider is not None:
                    break
        
        # 3. Явная модель
        if target_provider is None and model != "auto":
            for p in PROVIDERS:
                if model in p["models"]:
                    # Проверяем доступность
                    key_index = 0
                    if PROVIDER_KEYS.get(p["name"]):
                        ok, reason = rate_limiter.is_available(p["name"], key_index)
                        if not ok:
                            continue
                    if not circuit_breaker.is_available(p["name"]):
                        continue
                    target_provider = p
                    target_model = model
                    logger.info(f"[{request_id}] 🎯 Explicit model: {model} @ {p['name']}")
                    break
        
        # 4. Fallback: первый доступный провайдер
        if target_provider is None:
            for p in PROVIDERS:
                if PROVIDER_KEYS.get(p["name"]) or p.get("keyless", False):
                    key_index = 0
                    if PROVIDER_KEYS.get(p["name"]):
                        ok, reason = rate_limiter.is_available(p["name"], key_index)
                        if not ok:
                            continue
                    if not circuit_breaker.is_available(p["name"]):
                        continue
                    target_provider = p
                    target_model = p["models"][0]
                    model = p["models"][0]
                    logger.info(f"[{request_id}] 🎯 Fallback: {p['models'][0]} @ {p['name']}")
                    break
    
    if target_provider is None:
        await alert_all_providers_down()
        raise HTTPException(503, "No providers available")

    # === ВЫЗОВ ПРОВАЙДЕРА С FALLBACK ===
    provider_resp = None
    used_provider = None
    used_model = None
    
    # Собираем список кандидатов для fallback
    candidates = []
    if model == "auto":
        task_chain = fallback.get_chain(task)
        for entry in task_chain:
            for p in PROVIDERS:
                if p["name"] == entry["provider"]:
                    candidates.append((p, entry["model"]))
                    break
    else:
        # Для явной модели - все провайдеры с этой моделью
        for p in PROVIDERS:
            if model in p["models"]:
                candidates.append((p, model))
    
    # Если candidates пуст - добавляем все доступные провайдеры
    if not candidates:
        for p in PROVIDERS:
            if PROVIDER_KEYS.get(p["name"]) or p.get("keyless", False):
                candidates.append((p, p["models"][0]))
    
    # Перебираем кандидатов
    async def try_all_candidates():
        nonlocal provider_resp, used_provider, used_model
        for prov, mdl in candidates:
            # Проверяем rate limiter
            key_index = 0
            if PROVIDER_KEYS.get(prov["name"]):
                ok, reason = rate_limiter.is_available(prov["name"], key_index)
                if not ok:
                    logger.info(f"[{request_id}] ⏭️ {prov['name']}:{key_index} skipped: {reason}")
                    continue
            
            # Проверяем circuit breaker
            if not circuit_breaker.is_available(prov["name"]):
                logger.info(f"[{request_id}] 🔴 {prov['name']}: circuit breaker blocked")
                continue
            
            # Вызываем провайдер
            resp = await call_provider(prov, messages, mdl, stream, temperature, max_tokens)
            
            # Проверяем на error внутри ответа (OpenRouter 200 + error)
            if isinstance(resp, dict) and "error" in resp:
                logger.warning(f"[{request_id}] ⚠️ {prov['name']}: error in response: {str(resp['error'])[:100]}")
                # Обновляем статистику
                provider_stats.record_failure(prov["name"])
                continue
            
            if resp is not None:
                provider_resp = resp
                used_provider = prov
                used_model = mdl
                return
        
        # Если все кандидаты не сработали - пробуем все провайдеры
        for p in PROVIDERS:
            if p["name"] == target_provider["name"] and used_model == target_model:
                continue
            key_index = 0
            if PROVIDER_KEYS.get(p["name"]):
                ok, reason = rate_limiter.is_available(p["name"], key_index)
                if not ok:
                    continue
            if not circuit_breaker.is_available(p["name"]):
                continue
            resp = await call_provider(p, messages, p["models"][0], stream, temperature, max_tokens)
            if isinstance(resp, dict) and "error" in resp:
                logger.warning(f"[{request_id}] ⚠️ {p['name']}: error in response: {str(resp['error'])[:100]}")
                continue
            if resp is not None:
                provider_resp = resp
                used_provider = p
                used_model = p["models"][0]
                return
    
    try:
        await asyncio.wait_for(try_all_candidates(), timeout=OVERALL_DEADLINE)
    except asyncio.TimeoutError:
        logger.error(f"[{request_id}] ⏱️ Overall deadline {OVERALL_DEADLINE}s exceeded")
        await alert_all_providers_down()
        raise HTTPException(504, "Request timeout")
    
    if provider_resp is None:
        await alert_all_providers_down()
        raise HTTPException(503, "All providers failed")
    
    # Обновляем sticky session
    if session_key:
        sticky_sessions[session_key] = (used_provider["name"], used_model, time.time() + STICKY_TTL)
    
    target_provider = used_provider
    target_model = used_model
    
    # Обновляем статистику
    circuit_breaker.record_success(target_provider["name"])
    
    provider_format = target_provider.get("format", "openai")
    
    # Обработка ответа
    if stream:
        if isinstance(provider_resp, httpx.Response):
            # Логируем usage для стриминга (приблизительно)
            try:
                _log_usage(target_provider["name"], target_model, None)
            except: pass
            return StreamingResponse(
                stream_provider_response(provider_resp, target_model, available_tool_names),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # Логируем usage для стриминга (приблизительно)
            try:
                _log_usage(target_provider["name"], target_model, None)
            except: pass
            return StreamingResponse(
                generate_fake_stream(provider_resp, target_model, available_tool_names, provider_format),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
    else:
        # Non-streaming: возвращаем content + tool_calls (всегда поле)
        if provider_format == "aihorde":
            tool_calls = extract_aihorde_tool_calls(provider_resp)
            content = extract_aihorde_content(provider_resp)
            reasoning = extract_aihorde_reasoning_content(provider_resp)
            usage = extract_aihorde_usage(provider_resp)
            finish_reason = extract_aihorde_finish_reason(provider_resp)
        elif provider_format == "huggingface":
            tool_calls = extract_huggingface_tool_calls(provider_resp)
            content = extract_huggingface_content(provider_resp)
            reasoning = extract_huggingface_reasoning_content(provider_resp)
            usage = extract_huggingface_usage(provider_resp)
            finish_reason = extract_huggingface_finish_reason(provider_resp)
        else:
            tool_calls = extract_tool_calls(provider_resp)
            content = extract_openai_content(provider_resp)
            reasoning = extract_reasoning_content(provider_resp)
            usage = extract_usage(provider_resp)
            finish_reason = extract_finish_reason(provider_resp)
        
        # Rescue inline tool calls from content if structured tool_calls missing
        if not tool_calls and content and available_tool_names:
            rescued = rescue_inline_tool_calls(content, available_tool_names)
            if rescued:
                logger.info(f"[Consilium] Rescued {len(rescued)} inline tool call(s) from provider response")
                tool_calls = rescued
        
        has_tool_calls = tool_calls is not None and len(tool_calls) > 0
        
        # Normalize content per FreeLLMAPI: fold reasoning only if no tool_calls
        normalized_content = normalize_message_content(provider_resp, tool_calls, provider_format)
        
        # Strip inline tool calls from content for clean text (if any remain)
        if normalized_content and isinstance(normalized_content, str):
            normalized_content = strip_inline_tool_calls(normalized_content)
            if not normalized_content:
                normalized_content = None if has_tool_calls else ""
        
        message = {
            "role": "assistant",
            "content": normalized_content,
        }
        if reasoning and not has_tool_calls:
            message["reasoning_content"] = reasoning
        # Гарантируем наличие tool_calls поля (пустой список если нет)
        message["tool_calls"] = tool_calls if tool_calls else []
        
        response = {
            "id": f"chatcmpl-{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": target_model,
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": finish_reason if not has_tool_calls else "tool_calls"
            }]
        }
        if usage:
            response["usage"] = usage
        
        logger.info(f'📊 usage data: {usage}')
        try:
            _log_usage(target_provider["name"], target_model, usage)
        except Exception as e:
            logger.warning(f"📊 usage log failed: {e}")
        
        # Обновляем статистику и баллы
        latency = time.time() - start_time
        prompt_tokens = (usage or {}).get("prompt_tokens", 0)
        completion_tokens = (usage or {}).get("completion_tokens", 0)
        total_tokens = (usage or {}).get("total_tokens", 0)
        
        circuit_breaker.record_success(target_provider["name"])
        provider_stats.record_success(target_provider["name"], latency, total_tokens)
        provider_scoring.record_success(
            target_provider["name"], 
            latency, 
            prompt_tokens, 
            completion_tokens
        )
        
        logger.info(f"✅ [{request_id}] {target_provider['name']}/{target_model} -> content: {len(normalized_content) if normalized_content else 0} chars, tool_calls: {len(message['tool_calls'])} in {latency:.2f}s")
        return JSONResponse(response)
    
# ---------- MAIN ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")

#!/usr/bin/env python3
"""Тесты исправлений Consilium v7.2.

Запуск:  python consilium/tests/test_consilium.py
Или:     pytest consilium/tests/test_consilium.py

Каждый тест закрывает конкретный баг, найденный при аудите 22.07.2026.
"""
import os
import sys
import time
import asyncio
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router import classify_task, filter_system_prompt
from fallback_manager import FallbackManager
from provider_stats import ProviderStats
from rate_limiter import RateLimiter
from circuit_breaker import CircuitBreaker

# Реальный системный промпт Hermes v0.19 (сокращённый, из logs/consilium_responses.log)
REAL_HERMES_PROMPT = (
    "You are Hermes Agent, an intelligent AI assistant created by Nous Research. "
    "You are helpful, knowledgeable, and direct.\n\n"
    "You run on Hermes Agent (by Nous Research). When the user needs help with Hermes "
    "itself — configuring, setting up, using, extending, or troubleshooting it — "
    "treat the docs as the source of truth when the two differ.\n\n"
    "# Finishing the job\n"
    "When the user asks you to build, run, or verify something, the deliverable is a "
    "working artifact backed by real tool output.\n\n"
    "# Parallel tool calls\n"
    "When you need several pieces of information that don't depend on each other...\n\n"
    "You have persistent memory across sessions. Save durable facts using the memory tool.\n\n"
    "ТЫ — ОРКЕСТРАТОР B2B-ПАЙПЛАЙНА.\n\n"
    "## СЛОИ\n"
    "| product-analyst | /home/khadas/.hermes/agents/product-analyst/ |\n\n"
    "## ПРОТОКОЛ ВЫЗОВА\n"
    "1. read_file(<путь>/SOUL.md)\n"
    "2. delegate_task(goal=..., context=..., toolsets=[\"file\",\"terminal\"])\n"
)


def _fake_providers():
    """Два провайдера с ключами + один keyless, без обращения к сети."""
    return [
        {"name": "groq", "base_url": "https://api.groq.com/openai/v1",
         "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
         "keys": ["k1", "k2", "k3"], "keyless": False, "format": "openai", "rpd": 1000},
        {"name": "mistral", "base_url": "https://api.mistral.ai/v1",
         "models": ["mistral-large-latest", "codestral-2508"],
         "keys": ["m1"], "keyless": False, "format": "openai", "rpd": 10000},
        {"name": "aihorde", "base_url": "https://aihorde.net/api/v1",
         "models": ["stable-tsoul-4.2b"],
         "keys": [], "keyless": True, "format": "aihorde", "rpd": 0},
    ]


# --------------------------------------------------------------------------
# БАГ 1: фильтр system prompt вырезал роль агента целиком
# --------------------------------------------------------------------------

def test_filter_preserves_agent_role():
    out = filter_system_prompt(REAL_HERMES_PROMPT, "test")

    # Служебные блоки Hermes удалены
    assert "You run on Hermes Agent" not in out, "блок 'You run on' не вырезан"
    assert "# Finishing the job" not in out, "блок 'Finishing the job' не вырезан"
    assert "# Parallel tool calls" not in out, "блок 'Parallel tool calls' не вырезан"
    assert "persistent memory" not in out, "блок про память не вырезан"

    # А роль агента и протокол — на месте (раньше исчезали полностью)
    assert "ОРКЕСТРАТОР" in out, "РЕГРЕСС: роль оркестратора вырезана"
    assert "delegate_task" in out, "РЕГРЕСС: протокол вызова вырезан"
    assert "product-analyst" in out, "РЕГРЕСС: таблица слоёв вырезана"
    assert "You are Hermes Agent" in out, "базовое описание роли вырезано"
    print(f"  ✅ фильтр: {len(REAL_HERMES_PROMPT)} → {len(out)} символов, роль сохранена")


def test_filter_never_empties_prompt():
    """Защита: если паттерны съели почти всё — возвращаем оригинал."""
    only_service = ("You run on Hermes Agent (by Nous Research). Docs are the truth.\n\n"
                    "# Finishing the job\nDo the work.\n")
    out = filter_system_prompt(only_service, "test")
    assert len(out) >= 40, "фильтр вернул пустой промпт вместо защитного отката"
    print("  ✅ защита от полного опустошения промпта работает")


# --------------------------------------------------------------------------
# БАГ 2: model != "auto" не резолвился -> HTTP 503
# --------------------------------------------------------------------------

def test_explicit_model_resolves():
    fb = FallbackManager()
    fb.build_chains(_fake_providers())

    chain = fb.resolve_model("llama-3.3-70b-versatile")
    assert chain, "РЕГРЕСС: явная модель не резолвится -> будет 503"
    assert chain[0]["provider"] == "groq"

    # Формат 'провайдер/модель' тоже должен работать
    chain2 = fb.resolve_model("mistral/codestral-2508")
    assert chain2 and chain2[0]["provider"] == "mistral", "префикс провайдера не разобран"

    # Неизвестная модель -> пустой список (вызывающий откатится на роутинг)
    assert fb.resolve_model("no-such-model-xyz") == []
    print("  ✅ явная модель резолвится, неизвестная даёт откат на роутинг")


# --------------------------------------------------------------------------
# БАГ 3: get_chain возвращал пустой список для задач без моделей
# --------------------------------------------------------------------------

def test_chain_never_empty():
    fb = FallbackManager()
    # Только chat-модели: цепочки code/search/analysis окажутся пустыми
    fb.build_chains([{
        "name": "groq", "base_url": "x", "models": ["llama-3.1-8b-instant"],
        "keys": ["k"], "keyless": False, "format": "openai", "rpd": 1000,
    }])
    for task in ("chat", "code", "search", "analysis"):
        chain = fb.get_chain(task)
        assert chain, f"РЕГРЕСС: цепочка '{task}' пуста -> HTTP 503 на ровном месте"
    print("  ✅ ни одна цепочка не пуста")


def test_gate_filters_blocked_providers():
    fb = FallbackManager()
    fb.build_chains(_fake_providers())
    # groq заблокирован -> он должен уехать в хвост, а не остаться первым
    chain = fb.get_chain("chat", gate=lambda name: name != "groq")
    assert chain[0]["provider"] != "groq", "заблокированный провайдер выбран первым"
    assert any(e["provider"] == "groq" for e in chain), "заблокированный потерян совсем"
    print("  ✅ гейт уводит заблокированного в хвост, не теряя его")


# --------------------------------------------------------------------------
# Балльная система (DPS)
# --------------------------------------------------------------------------

def _fresh_stats():
    import provider_stats as ps_mod
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp()) / "stats.db"
    ps_mod.DB_PATH = tmp
    return ProviderStats(), tmp


def test_dps_rewards_success_punishes_failure():
    st, _ = _fresh_stats()
    for _ in range(20):
        st.record_success("good", latency=0.4, tokens=100, model="m")
    for _ in range(20):
        st.record_failure("bad", kind="5xx", model="m")

    good = st.get_dynamic_score("good", "m", rpd=1000)
    bad = st.get_dynamic_score("bad", "m", rpd=1000)
    assert good > bad, f"DPS не различает успешного и падающего: {good} vs {bad}"
    assert good > 60, f"успешный провайдер получил слишком мало: {good}"
    print(f"  ✅ DPS: успешный={good:.1f}, падающий={bad:.1f}")


def test_dps_prefers_faster_provider():
    st, _ = _fresh_stats()
    for _ in range(10):
        st.record_success("fast", latency=0.3, model="m")
        st.record_success("slow", latency=8.0, model="m")
    fast = st.get_dynamic_score("fast", "m", rpd=1000)
    slow = st.get_dynamic_score("slow", "m", rpd=1000)
    assert fast > slow, f"DPS игнорирует задержку: {fast} vs {slow}"
    print(f"  ✅ DPS учитывает задержку: 0.3с={fast:.1f}, 8с={slow:.1f}")


def test_dps_smoothing_protects_from_single_failure():
    """Один сбой у проверенного провайдера не должен его обнулять."""
    st, _ = _fresh_stats()
    for _ in range(100):
        st.record_success("veteran", latency=0.5, model="m")
    before = st.get_dynamic_score("veteran", "m", rpd=1000)
    st.record_failure("veteran", "429", "m")
    after = st.get_dynamic_score("veteran", "m", rpd=1000)
    assert after > before * 0.5, f"один сбой обрушил рейтинг: {before:.1f} -> {after:.1f}"
    print(f"  ✅ сглаживание: 100 успехов + 1 сбой = {before:.1f} → {after:.1f}")


def test_dps_survives_restart():
    st, tmp = _fresh_stats()
    for _ in range(15):
        st.record_success("groq", latency=0.5, tokens=50, model="m")
    st.flush(force=True)
    score_before = st.get_dynamic_score("groq", "m", rpd=1000)

    import provider_stats as ps_mod
    ps_mod.DB_PATH = tmp
    revived = ProviderStats()          # эмулируем перезапуск процесса
    score_after = revived.get_dynamic_score("groq", "m", rpd=1000)

    assert abs(score_before - score_after) < 0.01, \
        f"баллы не пережили перезапуск: {score_before} -> {score_after}"
    print(f"  ✅ баллы восстановлены после перезапуска: {score_after:.1f}")


# --------------------------------------------------------------------------
# Rate limiter
# --------------------------------------------------------------------------

def _fresh_limiter():
    import rate_limiter as rl_mod
    from pathlib import Path
    rl_mod.DB_PATH = Path(tempfile.mkdtemp()) / "rl.db"
    return RateLimiter(), rl_mod.DB_PATH


def test_is_available_returns_usable_tuple():
    rl, _ = _fresh_limiter()
    ok, reason = rl.is_available("groq", 0)
    assert ok is True and reason is None
    rl.mark_402("groq", 0)
    ok, reason = rl.is_available("groq", 0)
    assert ok is False and reason == "disabled", "402 не отключил ключ"
    print("  ✅ is_available отдаёт распаковываемый (bool, reason)")


def test_cooldown_escalates():
    rl, _ = _fresh_limiter()
    seen = []
    for _ in range(4):
        rl.mark_429("groq", 0)
        ok, reason = rl.is_available("groq", 0)
        assert not ok
        seen.append(int(reason.split(":")[1].rstrip("s")))
    assert seen[0] < seen[1] < seen[2] < seen[3], \
        f"РЕГРЕСС: cooldown не эскалирует, шаги={seen}"
    print(f"  ✅ эскалация cooldown: {seen} секунд")


def test_limiter_state_survives_restart():
    rl, db = _fresh_limiter()
    rl.mark_402("mistral", 0)
    rl.flush(force=True)

    import rate_limiter as rl_mod
    rl_mod.DB_PATH = db
    revived = RateLimiter()
    ok, reason = revived.is_available("mistral", 0)
    assert ok is False and reason == "disabled", "РЕГРЕСС: состояние лимитов не восстановлено"
    print("  ✅ отключённый ключ остаётся отключённым после перезапуска")


# --------------------------------------------------------------------------
# Circuit breaker
# --------------------------------------------------------------------------

def test_circuit_breaker_opens_at_threshold():
    cb = CircuitBreaker(threshold=5, cooldown=60)
    opened = []
    cb.on_open = opened.append
    for _ in range(4):
        cb.record_failure("groq")
    assert cb.is_available("groq"), "цепь разомкнулась раньше порога"
    cb.record_failure("groq")
    assert not cb.is_available("groq"), "цепь не разомкнулась на 5-й ошибке"
    assert opened == ["groq"], "алерт о размыкании не сработал ровно один раз"
    print("  ✅ circuit breaker: порог 5, алерт отправлен один раз")


# --------------------------------------------------------------------------
# Классификация задач
# --------------------------------------------------------------------------

def test_classify_task():
    assert classify_task([{"role": "user", "content": "Привет"}]) == "chat"
    assert classify_task([{"role": "user", "content": "Напиши код на python"}]) == "code"
    assert classify_task([{"role": "user", "content": "найди источники"}]) == "search"
    assert classify_task([{"role": "user", "content": "сделай анализ"}]) == "analysis"
    # content списком (v0.19 умеет слать части)
    assert classify_task([{"role": "user",
                           "content": [{"type": "text", "text": "напиши скрипт"}]}]) == "code"
    assert classify_task([]) == "chat"
    print("  ✅ классификация задач, включая content-списком")


# --------------------------------------------------------------------------
# Спасение вызовов инструментов, написанных текстом
# --------------------------------------------------------------------------

def test_rescue_inline_tool_calls():
    """Паттерн 'Qwen style' раньше состоял из иероглифов 那些 и не мог сработать."""
    import consilium_server as cs
    names = {"read_file", "delegate_task"}

    cases = {
        "Qwen/Hermes-2": '<tool_call>{"name": "read_file", "arguments": {"path": "SOUL.md"}}</tool_call>',
        "Hermes inline": '<function=read_file>{"path": "SOUL.md"}</function>',
        "GLM/Kimi": '<|tool_call_begin|>{"name": "read_file", "arguments": {}}<|tool_call_end|>',
        "Mistral": '[TOOL_CALLS][{"name": "read_file", "arguments": {"path": "x"}}][/TOOL_CALLS]',
    }
    for label, text in cases.items():
        calls = cs.rescue_inline_tool_calls(text, names)
        assert calls, f"формат {label} не распознан"
        assert calls[0]["function"]["name"] == "read_file", f"{label}: имя разобрано неверно"

    # Инструмент не из списка доступных — игнорируется
    assert cs.rescue_inline_tool_calls(
        '<tool_call>{"name": "rm_rf", "arguments": {}}</tool_call>', names) == []
    print(f"  ✅ распознаны все {len(cases)} текстовых формата tool_calls")


def test_empty_response_detected():
    """Пустой ответ должен считаться провалом провайдера."""
    import consilium_server as cs
    empty = {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": []}}]}
    assert not cs.response_has_payload(empty), "пустой ответ принят за валидный"

    with_text = {"choices": [{"message": {"role": "assistant", "content": "привет"}}]}
    assert cs.response_has_payload(with_text)

    with_tools = {"choices": [{"message": {"role": "assistant", "content": None,
                                           "tool_calls": [{"id": "1"}]}}]}
    assert cs.response_has_payload(with_tools), "ответ с tool_calls отброшен"
    assert not cs.response_has_payload({"choices": []}), "ответ без choices принят"
    print("  ✅ пустой ответ распознаётся как провал провайдера")


def test_max_tokens_clamped():
    """Hermes при provider=custom шлёт 65536 — модели отвечают 400."""
    import consilium_server as cs
    assert cs.clamp_max_tokens("llama-3.1-8b-instant", 65536) == 8192
    assert cs.clamp_max_tokens("llama-3.3-70b-versatile", 65536) == 32768
    assert cs.clamp_max_tokens("unknown-model", 65536) == cs.MAX_TOKENS_CAP
    assert cs.clamp_max_tokens("unknown-model", 512) == 512, "малое значение не должно расти"
    assert cs.clamp_max_tokens("unknown-model", None) == cs.MAX_TOKENS_CAP
    print("  ✅ max_tokens клампится по модели")


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    failed = 0
    for fn in TESTS:
        try:
            fn()
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  💥 {fn.__name__}: {type(e).__name__}: {e}")
    print()
    if failed:
        print(f"❌ Провалено: {failed} из {len(TESTS)}")
        sys.exit(1)
    print(f"🎉 Все тесты пройдены ({len(TESTS)})")

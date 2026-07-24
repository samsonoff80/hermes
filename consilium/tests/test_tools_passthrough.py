#!/usr/bin/env python3
"""Интеграционный тест ГЛАВНОГО бага: tools не доходили до провайдера.

Hermes Agent — агент, работающий через инструменты. Он присылает tools в
/v1/chat/completions, Consilium их читал, но в payload провайдеру НЕ клал.
Модель физически не могла вернуть tool_calls, агент вставал, а Telegram
показывал «The model provider failed after retries».

Тест поднимает фейкового провайдера на localhost и проверяет, что именно
уходит на его адрес.

Запуск: python consilium/tests/test_tools_passthrough.py
"""
import os
import sys
import json
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CAPTURED = {}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
    },
}, {
    "type": "function",
    "function": {
        "name": "delegate_task",
        "description": "Delegate to a sub-agent",
        "parameters": {"type": "object", "properties": {"goal": {"type": "string"}}},
    },
}]


class FakeProvider(BaseHTTPRequestHandler):
    """Отвечает валидным OpenAI-ответом и запоминает полученный payload."""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        CAPTURED["payload"] = json.loads(self.rfile.read(length))
        CAPTURED["auth"] = self.headers.get("Authorization")
        body = json.dumps({
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "created": 1,
            "model": "fake-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read_file",
                                     "arguments": '{"path":"SOUL.md"}'},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    srv = HTTPServer(("127.0.0.1", 0), FakeProvider)
    port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    import consilium_server as cs

    provider = {
        "name": "fake",
        "base_url": f"http://127.0.0.1:{port}/v1",
        "models": ["fake-model"],
        "keys": ["test-key"],
        "keyless": False,
        "format": "openai",
        "rpd": 100,
    }
    cs.PROVIDER_KEYS["fake"] = ["test-key"]

    messages = [
        {"role": "system", "content": "ТЫ — ОРКЕСТРАТОР."},
        {"role": "user", "content": "прочитай SOUL.md"},
    ]
    passthrough = {"tools": TOOLS, "tool_choice": "auto", "top_p": 0.9}

    resp = asyncio.run(cs.call_provider(
        provider, messages, "fake-model", False, 0.7, 4096, passthrough))

    failures = []

    payload = CAPTURED.get("payload") or {}
    if "tools" not in payload:
        failures.append("РЕГРЕСС: tools не переданы провайдеру — агент не сможет "
                        "вызывать инструменты")
    else:
        names = [t["function"]["name"] for t in payload["tools"]]
        if names != ["read_file", "delegate_task"]:
            failures.append(f"tools искажены: {names}")
        else:
            print(f"  ✅ tools доставлены провайдеру: {names}")

    if payload.get("tool_choice") != "auto":
        failures.append("tool_choice потерян")
    else:
        print("  ✅ tool_choice доставлен")

    if payload.get("top_p") != 0.9:
        failures.append("top_p потерян")
    else:
        print("  ✅ прочие поля OpenAI-спеки доставлены (top_p)")

    if CAPTURED.get("auth") != "Bearer test-key":
        failures.append(f"Authorization неверный: {CAPTURED.get('auth')}")
    else:
        print("  ✅ Authorization проставлен")

    tc = (resp or {}).get("choices", [{}])[0].get("message", {}).get("tool_calls")
    if not tc:
        failures.append("tool_calls из ответа провайдера потеряны")
    else:
        print(f"  ✅ tool_calls вернулись обратно: {tc[0]['function']['name']}")

    srv.shutdown()

    print()
    if failures:
        for f in failures:
            print(f"  ❌ {f}")
        sys.exit(1)
    print("🎉 Сквозная передача инструментов работает")


if __name__ == "__main__":
    main()

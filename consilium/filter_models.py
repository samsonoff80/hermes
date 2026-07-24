#!/usr/bin/env python3
"""Фильтрует кэш Hermes: только >=128K, исключает embedding/audio/safety."""
import json, sqlite3, time
from pathlib import Path

HERMES_CACHE = Path.home() / ".hermes/cache/model_catalog.json"
REGISTRY_DB = Path(__file__).parent / "model_registry.db"

EXCLUDE = ["embed", "audio", "speech", "vision", "guard", "safety", "bge", "pipecat", "tts", "asr", "whisper", "stable-diffusion"]

def classify(name):
    n = name.lower()
    if any(kw in n for kw in EXCLUDE):
        return []
    tags = []
    if any(kw in n for kw in ["llama", "mistral", "gpt", "gemma", "qwen"]): tags.append("chat")
    if any(kw in n for kw in ["coder", "deepseek", "code"]): tags.append("code")
    if any(kw in n for kw in ["gemini", "scout", "sonnet"]): tags.append("search")
    if any(kw in n for kw in ["large", "ultra", "r1"]): tags.append("analysis")
    return tags if tags else ["chat"]

def main():
    if not HERMES_CACHE.exists():
        print("❌ Кэш Hermes не найден")
        return
    
    with open(HERMES_CACHE) as f:
        catalog = json.load(f)
    
    conn = sqlite3.connect(str(REGISTRY_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS models (
        provider TEXT, model TEXT, context_length INTEGER,
        tags TEXT, priority REAL, enabled INTEGER,
        added_at REAL, last_checked REAL,
        PRIMARY KEY (provider, model))""")
    
    count = 0
    for p_id, p_data in catalog.get("providers", {}).items():
        for m in p_data.get("models", []):
            name = m.get("id", "")
            ctx = m.get("context_length", 0)
            tags = classify(name)
            if ctx >= 128000 and tags:
                conn.execute("INSERT OR REPLACE INTO models VALUES (?,?,?,?,?,?,?,?)",
                    (p_id, name, ctx, ",".join(tags), 50.0, 1, time.time(), time.time()))
                count += 1
    
    conn.commit()
    conn.close()
    print(f"✅ Отфильтровано: {count} моделей")

if __name__ == "__main__":
    main()

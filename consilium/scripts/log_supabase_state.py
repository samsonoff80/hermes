#!/usr/bin/env python3
"""Логирование состояния Supabase: схема таблиц и количество записей."""
import os
import json
import urllib.request
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_schema(table):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def get_count(table):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=count"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())[0]["count"]
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    tables = ["clients", "clean_clients"]
    state = {
        "timestamp": datetime.now().isoformat(),
        "tables": {}
    }
    for table in tables:
        state["tables"][table] = {
            "schema": get_schema(table),
            "count": get_count(table)
        }

    os.makedirs("references", exist_ok=True)
    output_path = f"references/supabase_state_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"Состояние сохранено в {output_path}")
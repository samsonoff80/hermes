#!/usr/bin/env python3
"""Provider Statistics — адаптивный приоритет на основе успешности."""
import sqlite3, time
from pathlib import Path

DB_PATH = Path(__file__).parent / "provider_stats.db"

class ProviderStats:
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS stats (
                provider TEXT PRIMARY KEY,
                success INTEGER DEFAULT 0,
                fail INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                avg_latency REAL DEFAULT 0,
                last_used REAL DEFAULT 0)""")
            conn.commit()
    
    def record_success(self, provider, latency, tokens):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""INSERT INTO stats (provider, success, total_tokens, avg_latency, last_used)
                VALUES (?,1,?,?,?) ON CONFLICT(provider) DO UPDATE SET
                success=success+1, total_tokens=total_tokens+?,
                avg_latency=(avg_latency*success+?)/(success+1), last_used=?""",
                (provider, tokens, latency, tokens, latency, time.time()))
            conn.commit()
    
    def record_failure(self, provider):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""INSERT INTO stats (provider, fail, last_used)
                VALUES (?,1,?) ON CONFLICT(provider) DO UPDATE SET
                fail=fail+1, last_used=?""",
                (provider, time.time(), time.time()))
            conn.commit()
    
    def get_priority(self):
        """Возвращает провайдеров отсортированных по успешности."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute("""SELECT provider, 
                CAST(success AS REAL)/(success+fail+1) as rate,
                avg_latency FROM stats ORDER BY rate DESC, avg_latency ASC""").fetchall()
            return [(r[0], r[1], r[2]) for r in rows]

provider_stats = ProviderStats()

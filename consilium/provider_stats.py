#!/usr/bin/env python3
"""Provider Statistics — адаптивный приоритет на основе успешности."""
import sqlite3, time, threading
from pathlib import Path

DB_PATH = Path(__file__).parent / "provider_stats.db"

class ProviderStats:
    def __init__(self):
        self.lock = threading.Lock()
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
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute("""INSERT INTO stats (provider, success, total_tokens, avg_latency, last_used)
                VALUES (?,1,?,?,?) ON CONFLICT(provider) DO UPDATE SET
                success=success+1, total_tokens=total_tokens+?,
                avg_latency=(avg_latency*success+?)/(success+1), last_used=?""",
                (provider, tokens, latency, tokens, latency, time.time()))
            conn.commit()
    
    def record_failure(self, provider):
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute("""INSERT INTO stats (provider, fail, last_used)
                VALUES (?,1,?) ON CONFLICT(provider) DO UPDATE SET
                fail=fail+1, last_used=?""",
                (provider, time.time(), time.time()))
            conn.commit()
    
    
    def get_dynamic_score(self, provider_name: str) -> float:
        """DPS = success_rate*40 + latency*30 + availability*20 + cost*10"""
        import math
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                row = conn.execute("SELECT success, fail, avg_latency FROM stats WHERE provider=?", (provider_name,)).fetchone()
                if not row:
                    return 50.0
                success, fail, avg_latency = row
                rate = success / (success + fail + 1)
                score_success = rate * 40
                latency_ms = (avg_latency or 1.0) * 1000
                score_latency = 30 * math.exp(-latency_ms / 500)
                score_availability = max(0, 20 - fail * 2)
                return score_success + score_latency + score_availability + 5.0

    def get_priority(self):
        """Возвращает провайдеров отсортированных по успешности."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute("""SELECT provider, 
                CAST(success AS REAL)/(success+fail+1) as rate,
                avg_latency FROM stats ORDER BY rate DESC, avg_latency ASC""").fetchall()
            return [(r[0], r[1], r[2]) for r in rows]

provider_stats = ProviderStats()

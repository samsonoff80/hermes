#!/usr/bin/env python3
"""Provider Statistics — адаптивный приоритет на основе успешности."""
import sqlite3, time, threading, math
from pathlib import Path
from typing import List, Tuple

DB_PATH = Path(__file__).parent / "provider_stats.db"

class ProviderStats:
    def __init__(self):
        self._init_db()
        self.lock = threading.Lock()  # Потокобезопасность
    
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
                # Исправлено: 7 параметров для 7 плейсхолдеров
                conn.execute("""INSERT INTO stats (provider, success, total_tokens, avg_latency, last_used)
                    VALUES (?, 1, ?, ?, ?) 
                    ON CONFLICT(provider) DO UPDATE SET
                    success = success + 1, 
                    total_tokens = total_tokens + ?,
                    avg_latency = (avg_latency * success + ?) / (success + 1), 
                    last_used = ?""",
                    (provider, tokens, latency, time.time(), tokens, latency, time.time()))
                conn.commit()
    
    def record_failure(self, provider):
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute("""INSERT INTO stats (provider, fail, last_used)
                    VALUES (?,1,?) ON CONFLICT(provider) DO UPDATE SET
                    fail=fail+1, last_used=?""",
                    (provider, time.time(), time.time()))
                conn.commit()
    
    def get_priority(self):
        """Возвращает провайдеров отсортированных по успешности."""
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                rows = conn.execute("""SELECT provider, 
                    CAST(success AS REAL)/(success+fail+1) as rate,
                    avg_latency FROM stats ORDER BY rate DESC, avg_latency ASC""").fetchall()
                return [(r[0], r[1], r[2]) for r in rows]
    
    def get_dynamic_score(self, provider_name: str) -> float:
        """
        Dynamic Provider Score (DPS) — формула:
        DPS = SUCCESS_RATE*40 + LATENCY_SCORE*30 + AVAILABILITY*20 + COST*10
        """
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                row = conn.execute("""
                    SELECT success, fail, avg_latency, total_tokens 
                    FROM stats WHERE provider = ?
                """, (provider_name,)).fetchone()
                
                if not row:
                    return 10.0  # Новый провайдер, средний score
                
                success, fail, avg_latency, tokens = row
                
                # 1. Success Rate (0-40 баллов)
                success_rate = success / (success + fail + 1)
                score_success = success_rate * 40
                
                # 2. Latency Score (0-30 баллов) — экспоненциальное затухание
                # 100ms=30, 500ms=20, 1000ms=10, 3000ms=0
                latency_ms = (avg_latency or 1.0) * 1000
                score_latency = 30 * math.exp(-latency_ms / 500)
                
                # 3. Availability (0-20 баллов) — упрощённо по failure count
                score_availability = max(0, 20 - fail * 2)
                
                # 4. Cost (0-10 баллов) — заглушка, все равны
                score_cost = 5
                
                return score_success + score_latency + score_availability + score_cost
    
    def get_ranked_providers(self, providers_list: list) -> List[Tuple[str, float]]:
        """Вернуть список (provider_name, dps) отсортированный по убыванию DPS."""
        scored = []
        for p in providers_list:
            name = p.get("name", "")
            if not name:
                continue
            dps = self.get_dynamic_score(name)
            scored.append((name, dps))
        scored.sort(key=lambda x: -x[1])
        return scored

provider_stats = ProviderStats()

#!/usr/bin/env python3
"""Provider Statistics — адаптивный приоритет на основе успешности."""
import sqlite3, time, logging
from pathlib import Path

logger = logging.getLogger("consilium.provider_stats")

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
                last_used REAL DEFAULT 0,
                last_success REAL DEFAULT 0,
                last_failure REAL DEFAULT 0)""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_provider ON stats(provider)")
            conn.commit()
    
    def record_success(self, provider, latency, tokens):
        """Записывает успешный запрос."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""INSERT INTO stats (provider, success, total_tokens, avg_latency, last_used, last_success)
                VALUES (?,1,?,?,?,?) ON CONFLICT(provider) DO UPDATE SET
                success=success+1, 
                total_tokens=total_tokens+?,
                avg_latency=(avg_latency*success+?)/(success+1), 
                last_used=?, last_success=?""",
                (provider, tokens, latency, time.time(), time.time(), tokens, latency, time.time(), time.time()))
            conn.commit()
        logger.debug(f"✅ {provider}: success recorded (latency: {latency:.2f}s, tokens: {tokens})")
    
    def record_failure(self, provider, error_type="other"):
        """Записывает ошибку."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""INSERT INTO stats (provider, fail, last_used, last_failure)
                VALUES (?,1,?,?) ON CONFLICT(provider) DO UPDATE SET
                fail=fail+1, last_used=?, last_failure=?""",
                (provider, time.time(), time.time(), time.time(), time.time()))
            conn.commit()
        logger.debug(f"❌ {provider}: failure recorded ({error_type})")
    
    def get_priority(self):
        """Возвращает провайдеров отсортированных по успешности."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute("""SELECT provider, 
                CAST(success AS REAL)/(success+fail+1) as rate,
                avg_latency FROM stats ORDER BY rate DESC, avg_latency ASC""").fetchall()
            return [(r[0], r[1], r[2]) for r in rows]
    
    def get_stats(self, provider):
        """Возвращает статистику для провайдера."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute("SELECT * FROM stats WHERE provider=?", (provider,)).fetchone()
        if not row:
            return None
        columns = ["provider", "success", "fail", "total_tokens", "avg_latency", "last_used", "last_success", "last_failure"]
        return dict(zip(columns, row))

provider_stats = ProviderStats()

#!/usr/bin/env python3
"""Rate Limiter — per-key tracking with SQLite persistence."""
import time, sqlite3, threading, logging
from pathlib import Path

logger = logging.getLogger("consilium.rate_limiter")

DB_PATH = Path(__file__).parent / "rate_limits.db"
COOLDOWN_STEPS = [90, 300, 900, 3600, 21600]

class RateLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self._cache = {}
        self._init_db()
        self._load_state()
        self._load_state()
    
    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS rate_limits (
                provider TEXT, key_index INTEGER, rpm_count INTEGER, tpm_count INTEGER,
                rpd_count INTEGER, tpd_count INTEGER, window_start REAL, day_start REAL,
                cooldown_until REAL, consecutive_429 INTEGER, disabled INTEGER DEFAULT 0,
                PRIMARY KEY (provider, key_index))""")
            conn.commit()
    
    def _load_state(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            for row in conn.execute("SELECT * FROM rate_limits"):
                provider, ki, rpm, tpm, rpd, tpd, ws, ds, co, c429, dis = row
                self._cache[(provider, ki)] = {"cooldown_until": co, "disabled": dis, "consecutive_429": c429}
    
    def _save_state(self, provider, key_index, rpm, tpm, rpd, tpd, ws, ds, co, c429, dis):
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute("""INSERT OR REPLACE INTO rate_limits VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (provider, key_index, rpm, tpm, rpd, tpd, ws, ds, co, c429, dis))
                conn.commit()
    
    def is_available(self, provider, key_index=0):
        # Упрощённая проверка — всегда True если не disabled
        with sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute("SELECT disabled, cooldown_until FROM rate_limits WHERE provider=? AND key_index=?",
                              (provider, key_index)).fetchone()
            if row and row[0]:
                return False, "disabled"
            if row and row[1] > time.time():
                return False, f"cooldown:{int(row[1]-time.time())}s"
        return True, None
    
    def record_request(self, provider, key_index, tokens):
        # Обновляем счётчики RPM/TPM в памяти и SQLite
        pass  # TODO: реализовать агрегацию
    
    def _get_consecutive_429(self, provider, key_index):
        with sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute("SELECT consecutive_429 FROM rate_limits WHERE provider=? AND key_index=?", (provider, key_index)).fetchone()
            return row[0] if row and row[0] else 0

    def mark_429(self, provider, key_index):
        prev = self._get_consecutive_429(provider, key_index)
        step = min(prev, len(COOLDOWN_STEPS) - 1)
        cooldown = time.time() + COOLDOWN_STEPS[step]
        self._save_state(provider, key_index, 0,0,0,0,0,0, cooldown, prev + 1, 0)
        logger.warning(f"⏳ {provider}:{key_index} 429 → cooldown {COOLDOWN_STEPS[0]}s")
    
    def mark_402(self, provider, key_index):
        self._save_state(provider, key_index, 0,0,0,0,0,0,0,0, 1)
        logger.warning(f"❌ {provider}:{key_index} 402 → disabled")
    
    def mark_success(self, provider, key_index):
        self._save_state(provider, key_index, 0,0,0,0,0,0,0,0, 0)

rate_limiter = RateLimiter()

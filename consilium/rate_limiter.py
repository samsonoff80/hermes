#!/usr/bin/env python3
"""Rate Limiter — per-key tracking with SQLite persistence."""
import time, sqlite3, threading, logging
from pathlib import Path

logger = logging.getLogger("consilium.rate_limiter")

DB_PATH = Path(__file__).parent / "rate_limits.db"
COOLDOWN_STEPS = [90, 300, 900, 3600, 21600]  # 90s -> 5m -> 15m -> 1h -> 6h

class RateLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self._init_db()
        self._load_state()
    
    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS rate_limits (
                provider TEXT, 
                key_index INTEGER, 
                rpm_count INTEGER DEFAULT 0,
                tpm_count INTEGER DEFAULT 0,
                rpd_count INTEGER DEFAULT 0,
                tpd_count INTEGER DEFAULT 0,
                window_start REAL DEFAULT 0,
                day_start REAL DEFAULT 0,
                cooldown_until REAL DEFAULT 0,
                consecutive_429 INTEGER DEFAULT 0,
                disabled INTEGER DEFAULT 0,
                PRIMARY KEY (provider, key_index))""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_provider ON rate_limits(provider)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cooldown ON rate_limits(cooldown_until) WHERE cooldown_until > 0")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_disabled ON rate_limits(disabled) WHERE disabled = 1")
            conn.commit()
    
    def _load_state(self):
        """Загружаем состояние из SQLite в память для быстрого доступа."""
        self.state = {}
        with sqlite3.connect(str(DB_PATH)) as conn:
            for row in conn.execute("SELECT * FROM rate_limits"):
                provider, ki, rpm, tpm, rpd, tpd, ws, ds, co, c429, dis = row
                self.state[(provider, ki)] = {
                    "rpm_count": rpm,
                    "tpm_count": tpm,
                    "rpd_count": rpd,
                    "tpd_count": tpd,
                    "window_start": ws,
                    "day_start": ds,
                    "cooldown_until": co,
                    "consecutive_429": c429,
                    "disabled": bool(dis),
                }
    
    def _save_state(self, provider, key_index, rpm, tpm, rpd, tpd, ws, ds, co, c429, dis):
        """Сохраняем состояние в SQLite."""
        with self.lock:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute("""INSERT OR REPLACE INTO rate_limits VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (provider, key_index, rpm, tpm, rpd, tpd, ws, ds, co, c429, dis))
                conn.commit()
            # Обновляем кэш
            self.state[(provider, key_index)] = {
                "rpm_count": rpm,
                "tpm_count": tpm,
                "rpd_count": rpd,
                "tpd_count": tpd,
                "window_start": ws,
                "day_start": ds,
                "cooldown_until": co,
                "consecutive_429": c429,
                "disabled": bool(dis),
            }
    
    def is_available(self, provider: str, key_index: int = 0) -> tuple[bool, str | None]:
        """Проверяет доступность ключа провайдера.
        
        Возвращает:
            (True, None) - доступен
            (False, "disabled") - ключ отключён
            (False, "cooldown:Xs") - ключ в cooldown на X секунд
            (False, "rate_limit") - превышен лимит
        """
        # Проверяем кэш
        state = self.state.get((provider, key_index), {})
        
        # Проверяем disabled
        if state.get("disabled", False):
            return False, "disabled"
        
        # Проверяем cooldown
        cooldown_until = state.get("cooldown_until", 0)
        if cooldown_until > time.time():
            remaining = int(cooldown_until - time.time())
            return False, f"cooldown:{remaining}s"
        
        # Проверяем RPM/TPM/RPD/TPD лимиты
        # Для упрощения - пока только cooldown и disabled
        # Полная реализация требует знания лимитов провайдера
        
        return True, None
    
    def record_request(self, provider: str, key_index: int, prompt_tokens: int, completion_tokens: int):
        """Записывает запрос для трекинга лимитов."""
        now = time.time()
        state = self.state.get((provider, key_index), {})
        
        # RPM (requests per minute) - окно 60 секунд
        if state.get("window_start", 0) < now - 60:
            rpm_count = 1
            window_start = now
        else:
            rpm_count = state.get("rpm_count", 0) + 1
            window_start = state.get("window_start", now)
        
        # TPM (tokens per minute)
        tpm_count = state.get("tpm_count", 0) + prompt_tokens + completion_tokens
        
        # RPD (requests per day)
        if state.get("day_start", 0) < now - 86400:
            rpd_count = 1
            day_start = now
        else:
            rpd_count = state.get("rpd_count", 0) + 1
            day_start = state.get("day_start", now)
        
        # TPD (tokens per day)
        tpd_count = state.get("tpd_count", 0) + prompt_tokens + completion_tokens
        
        self._save_state(
            provider, key_index,
            rpm_count, tpm_count, rpd_count, tpd_count,
            window_start, day_start,
            state.get("cooldown_until", 0),
            state.get("consecutive_429", 0),
            0  # disabled
        )
    
    def mark_429(self, provider: str, key_index: int):
        """Помечает ключ как получивший 429 Too Many Requests."""
        state = self.state.get((provider, key_index), {})
        consecutive_429 = state.get("consecutive_429", 0) + 1
        
        # Эскалация cooldown
        step_index = min(consecutive_429 - 1, len(COOLDOWN_STEPS) - 1)
        cooldown = time.time() + COOLDOWN_STEPS[step_index]
        
        self._save_state(
            provider, key_index,
            state.get("rpm_count", 0),
            state.get("tpm_count", 0),
            state.get("rpd_count", 0),
            state.get("tpd_count", 0),
            state.get("window_start", 0),
            state.get("day_start", 0),
            cooldown,
            consecutive_429,
            0  # не отключаем ключ
        )
        logger.warning(f"⏳ {provider}:{key_index} 429 → cooldown {COOLDOWN_STEPS[step_index]}s (consecutive: {consecutive_429})")
    
    def mark_402(self, provider: str, key_index: int):
        """Помечает ключ как невалидный (402/403)."""
        self._save_state(
            provider, key_index,
            0, 0, 0, 0,
            0, 0, 0, 0, 1  # disabled = True
        )
        logger.warning(f"❌ {provider}:{key_index} 402/403 → disabled")
    
    def mark_success(self, provider: str, key_index: int):
        """Сбрасывает счётчики ошибок после успешного запроса."""
        state = self.state.get((provider, key_index), {})
        self._save_state(
            provider, key_index,
            state.get("rpm_count", 0),
            state.get("tpm_count", 0),
            state.get("rpd_count", 0),
            state.get("tpd_count", 0),
            state.get("window_start", 0),
            state.get("day_start", 0),
            0,  # cooldown_until
            0,  # consecutive_429
            0   # disabled
        )
    
    def reset_key(self, provider: str, key_index: int):
        """Сбрасывает все счётчики для ключа."""
        self._save_state(
            provider, key_index,
            0, 0, 0, 0,
            0, 0, 0, 0, 0
        )

rate_limiter = RateLimiter()
